import {test} from 'node:test'
import assert from 'node:assert/strict'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/code-history-render-'),'render.cjs')
const hookOutput=path.join(path.dirname(output),'hook.cjs')
buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {useNote} from './src/local/useNote'; export function session(initial){let note;function Capture(){note=useNote('p',initial);return null}renderToStaticMarkup(<Capture/>);return note}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:hookOutput,jsx:'automatic',logLevel:'silent'})
const {session}=createRequire(import.meta.url)(hookOutput)
const initial={body_md:'notes',code_text:'old code',language:'python',revision:1,updated_at:'now'}

// Use the real hook closures. SSR omits timers so each async interleaving is explicit.
function network(t){
  const requests=[]
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    if(url==='/api/v1/session')return Response.json({token:'test-token'})
    return new Promise(resolve=>requests.push({url,body:JSON.parse(options.body),reply:(body,status=200)=>resolve(Response.json(body,{status}))}))
  })
  return requests
}
async function until(condition){
  for(let i=0;i<30&&!condition();i++)await new Promise(resolve=>setImmediate(resolve))
  assert.ok(condition(),'expected request or state did not arrive')
}

test('rewrite saves the latest draft first; close waits and note edits during archive survive',async t=>{
  const requests=network(t),note=session(initial)
  note.setDraft({code_text:'latest draft'})
  const rewrite=note.rewriteCode()
  const duplicate=note.rewriteCode()
  assert.equal(duplicate,rewrite)
  let closed=false
  const close=note.flush().then(ok=>{closed=ok;return ok})
  await until(()=>requests.length===1)
  assert.deepEqual(requests[0].body,{revision:1,body_md:'notes',code_text:'latest draft',language:'python'})
  assert.equal(closed,false)
  requests[0].reply({...initial,code_text:'latest draft',revision:2})
  await until(()=>requests.length===2)
  assert.equal(requests[1].url,'/api/v1/problems/p/code/rewrite')
  assert.deepEqual(requests[1].body,{revision:2,history_id:null})
  note.setDraft({body_md:'notes written during archive'})
  assert.equal(closed,false)
  requests[1].reply({...initial,code_text:'',revision:3})
  assert.equal(await rewrite,true)
  await until(()=>requests.length===3)
  assert.deepEqual(requests[2].body,{revision:3,body_md:'notes written during archive',code_text:'',language:'python'})
  requests[2].reply({...requests[2].body,revision:4})
  assert.equal(await close,true)
})

test('failed draft save prevents archiving and keeps the unsaved code available for retry',async t=>{
  const requests=network(t),note=session(initial)
  note.setDraft({code_text:'do not lose this'})
  const rewrite=note.rewriteCode(7)
  await until(()=>requests.length===1)
  requests[0].reply({detail:'storage failure'},503)
  assert.equal(await rewrite,false)
  assert.equal(requests.length,1)
  const retry=note.flush()
  await until(()=>requests.length===2)
  assert.equal(requests[1].url,'/api/v1/problems/p/note')
  assert.equal(requests[1].body.code_text,'do not lose this')
  requests[1].reply({...requests[1].body,revision:2})
  assert.equal(await retry,true)
})

test('archive conflict keeps the current code and prevents a pending close',async t=>{
  const requests=network(t),note=session(initial)
  const rewrite=note.rewriteCode(7),close=note.flush()
  await until(()=>requests.length===1)
  assert.deepEqual(requests[0].body,{revision:1,history_id:7})
  requests[0].reply({detail:'revision conflict'},409)
  assert.equal(await rewrite,false)
  assert.equal(await close,false)
  note.setDraft({body_md:'updated notes'})
  const retry=note.flush()
  await until(()=>requests.length===2)
  assert.equal(requests[1].body.code_text,'old code')
  assert.equal(requests[1].body.revision,1)
  requests[1].reply({detail:'revision conflict'},409)
  assert.equal(await retry,false)
})

test('history displays an immutable version with copy and restore, without editing the current draft',()=>{
  buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {QueryClient,QueryClientProvider} from '@tanstack/react-query'; import CodePractice from './src/local/CodePractice'; export function render(view,busy=false){const client=new QueryClient();client.setQueryData(['code-history','p'],[{id:7,problem_id:'p',code_text:'console.log("old")',language:'javascript',created_at:'2026-11-04T09:00:00Z'}]);return renderToStaticMarkup(<QueryClientProvider client={client}><CodePractice problemId="p" code="unsaved current draft" language="javascript" view={view} onViewChange={()=>{}} onCodeChange={()=>{}} onLanguageChange={()=>{}} onRewrite={async()=>true} changing={busy}/></QueryClientProvider>)}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent',loader:{'.css':'empty'}})
  const {render}=createRequire(import.meta.url)(output)
  const history=render('history')
  assert.match(history,/console\.log/)
  assert.doesNotMatch(history,/unsaved current draft/)
  assert.match(history,/只读/)
  assert.match(history,/复制代码/)
  assert.match(history,/载入到当前练习/)
  assert.doesNotMatch(history,/<textarea[^>]*aria-label="我的代码"/)
  const current=render('current')
  assert.match(current,/unsaved current draft/)
  assert.match(current,/重新编写/)
  assert.doesNotMatch(current,/console\.log/)
  const busy=render('current',true)
  assert.match(busy,/<textarea[^>]*readonly=""/i)
  assert.match(busy,/<select[^>]*disabled=""/)
})
