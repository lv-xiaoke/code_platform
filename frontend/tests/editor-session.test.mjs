import {test,after} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from '../node_modules/jsdom/lib/api.js'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost',pretendToBeVisual:true})
for(const name of ['window','document','Window','Document','Node','Element','HTMLElement','MutationObserver','DOMRect','Range'])globalThis[name]=name==='window'?dom.window:dom.window[name]
Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true})
globalThis.getComputedStyle=dom.window.getComputedStyle.bind(dom.window)
globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window)
globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window)
globalThis.IS_REACT_ACT_ENVIRONMENT=true
// React's browser scheduler must use timers in this DOM harness; Node's
// MessageChannel otherwise keeps a test-only port alive after unmount.
globalThis.MessageChannel=class{
  constructor(){this.port1={onmessage:null};this.port2={postMessage:data=>setImmediate(()=>this.port1.onmessage?.({data}))}}
}
globalThis.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}}
dom.window.Range.prototype.getClientRects=()=>[]
dom.window.Range.prototype.getBoundingClientRect=()=>({top:0,left:0,right:0,bottom:0,width:0,height:0})
after(()=>dom.window.close())
mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/editor-session-'),'test.cjs')
buildSync({stdin:{contents:`
import React,{act} from 'react';import {createRoot} from 'react-dom/client';
import {EditorView} from '@codemirror/view';import {undo} from '@codemirror/commands';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import CodeEditor from './src/local/CodeEditor';import {useTerminal} from './src/local/useTerminal';
import CodePractice from './src/local/CodePractice';
export {act,undo};
export function editor(node){const root=createRoot(node);return {
 async render(language,source,onChange){await act(async()=>{root.render(<CodeEditor language={language} value={source} onChange={onChange} ariaLabel="test editor"/>)});},
 view(){return EditorView.findFromDOM(node.querySelector('.cm-editor'));},
 async close(){await act(async()=>root.unmount());}};}
export async function terminal(node){const root=createRoot(node),client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});let current;
function Capture(){current=useTerminal('p');return null;}
await act(async()=>{root.render(<QueryClientProvider client={client}><Capture/></QueryClientProvider>)});
return {get:()=>current,async close(){await act(async()=>root.unmount());client.clear();}};}
export function practice(node){const root=createRoot(node),client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});client.setQueryData(['code-languages','p'],['kotlin','Go','C++']);return {
 async render(language){await act(async()=>{root.render(<QueryClientProvider client={client}><CodePractice problemId="p" code="saved draft" language={language} view="current" onViewChange={()=>{}} onCodeChange={()=>{}} onLanguageChange={()=>{}} onRewrite={async()=>true} changing={false}/></QueryClientProvider>)});},
 async close(){await act(async()=>root.unmount());client.clear();}};}
`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent'})
const {act,undo,editor,terminal,practice}=createRequire(import.meta.url)(output)

test('undo after changing language cannot save source from the previous language',async()=>{
  const node=document.createElement('div');document.body.append(node)
  const session=editor(node),drafts={python:'python original',java:'java original'}
  try{
    await session.render('python',drafts.python,text=>drafts.python=text)
    await act(async()=>{const view=session.view();view.dispatch({changes:{from:0,to:view.state.doc.length,insert:'python edited'}})})
    await session.render('java',drafts.java,text=>drafts.java=text)
    await act(async()=>{undo(session.view())})
    assert.equal(drafts.java,'java original')
    assert.equal(session.view().state.doc.toString(),'java original')
    assert.equal(drafts.python,'python edited')
  }finally{await session.close();node.remove()}
})

test('failed terminal start cannot expose the previous language terminal',async t=>{
  const old={id:'python-session',problem_id:'p',language:'python',status:'executed',stdout:'old Python output',stderr:'',stdin:'',transcript:'old Python output',input_closed:true}
  t.mock.method(globalThis,'fetch',async(url,options={})=>{
    if(url==='/api/v1/session')return Response.json({token:'test'})
    if(url.includes('/terminal-requests/'))return Response.json(old)
    if(url==='/api/v1/terminals/python-session')return Response.json(old)
    if(url==='/api/v1/problems/p/terminals'){
      return JSON.parse(options.body).language==='python'?Response.json(old):Response.json({detail:'terminal quota'},{status:429})
    }
    throw Error('unexpected request: '+url)
  })
  const node=document.createElement('div');document.body.append(node)
  const session=await terminal(node)
  try{
    await act(async()=>{await session.get().start('print(1)','python')})
    assert.equal(session.get().state?.id,'python-session')
    await act(async()=>{await session.get().start('class Main {}','java')})
    assert.equal(session.get().id,null)
    assert.equal(session.get().state,undefined)
    assert.match(session.get().error,/terminal quota/)
  }finally{await session.close();node.remove()}
})

test('saved legacy languages stay selectable after switching to Python',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json(['kotlin','Go','C++']))
  const node=document.createElement('div');document.body.append(node)
  const session=practice(node)
  try{
    await session.render('kotlin')
    assert.ok(node.querySelector('option[value="kotlin"]'))
    await session.render('python')
    for(const language of ['kotlin','Go','C++']){
      assert.ok([...node.querySelectorAll('option')].some(option=>option.value===language))
    }
  }finally{await session.close();node.remove()}
})
