import {test} from 'node:test'
import assert from 'node:assert/strict'
import {DraftController,initialCode} from '../src/local/codeDraftState.ts'

const py={problem_id:'p',language:'python',code_text:'python draft',revision:1,exists:true,created_at:'a',updated_at:'a'}
function fixture(overrides={}){
  const store={python:{...py},java:{...py,language:'java',code_text:'java draft',revision:2}}
  const events=[]
  const deps={
    stopActive:async()=>{events.push('stop');return true},
    read:async lang=>({...store[lang]}),
    write:async(lang,code,revision)=>{events.push('save:'+lang);assert.equal(revision,store[lang].revision);return store[lang]={...store[lang],code_text:code,revision:revision+1,exists:true}},
    select:async lang=>events.push('select:'+lang),
    template:async lang=>'template:'+lang,
    rewrite:async()=>{throw Error('not expected')},
    ...overrides,
  }
  return {controller:new DraftController(py,deps),store,events}
}

test('switch saves source language then loads target; switching back preserves edits',async()=>{
  const {controller:c,events}=fixture()
  c.setCode('new python')
  assert.equal(await c.switchLanguage('java'),true)
  assert.equal(c.getSnapshot().draft.code_text,'java draft')
  assert.deepEqual(events,['stop','save:python','select:java'])
  c.setCode('new java')
  assert.equal(await c.switchLanguage('python'),true)
  assert.equal(c.getSnapshot().draft.code_text,'new python')
})
test('save conflict retains source language and input without selecting target',async()=>{
  const {controller:c,events}=fixture({write:async()=>{throw Error('conflict')}})
  c.setCode('unsaved python')
  assert.equal(await c.switchLanguage('java'),false)
  assert.equal(c.getSnapshot().draft.language,'python')
  assert.equal(c.getSnapshot().draft.code_text,'unsaved python')
  assert.match(c.getSnapshot().error,/conflict/)
  assert.deepEqual(events,['stop'])
})
test('failed stop prevents saving and switching',async()=>{
  const {controller:c,events}=fixture({stopActive:async()=>false})
  c.setCode('keep')
  assert.equal(await c.switchLanguage('java'),false)
  assert.equal(c.getSnapshot().draft.code_text,'keep')
  assert.deepEqual(events,[])
})
test('pending switch locks edits and duplicate switches share a promise',async()=>{
  let finish
  const {controller:c}=fixture({read:()=>new Promise(resolve=>{finish=resolve})})
  const pending=c.switchLanguage('java')
  assert.equal(c.switchLanguage('python'),pending)
  c.setCode('late edit')
  for(let i=0;i<10&&!finish;i++)await new Promise(resolve=>setImmediate(resolve))
  finish({...py,language:'java',code_text:'target'})
  assert.equal(await pending,true)
  assert.equal(c.getSnapshot().draft.code_text,'target')
})
test('edits arriving during save are saved after its response without losing new text',async()=>{
  let finish
  const {controller:c}=fixture({write:(lang,code,revision)=>new Promise(resolve=>{finish=()=>resolve({...py,code_text:code,revision:revision+1})})})
  c.setCode('first')
  const pending=c.save()
  for(let i=0;i<10&&!finish;i++)await new Promise(resolve=>setImmediate(resolve))
  c.setCode('second');finish();finish=null
  for(let i=0;i<10&&!finish;i++)await new Promise(resolve=>setImmediate(resolve))
  assert.equal(c.getSnapshot().draft.code_text,'second')
  finish()
  assert.equal(await pending,true)
  assert.equal(c.getSnapshot().dirty,false)
})
test('saved empty draft stays empty; only missing drafts use templates',()=>{
  assert.equal(initialCode({...py,code_text:''},'template'),'')
  assert.equal(initialCode({...py,code_text:'',exists:false},'template'),'template')
})
test('failed preference write leaves current language and both server drafts intact',async()=>{
  const {controller:c,store}=fixture({select:async()=>{throw Error('preference conflict')}})
  c.setCode('saved python')
  assert.equal(await c.switchLanguage('java'),false)
  assert.equal(c.getSnapshot().draft.language,'python')
  assert.equal(store.python.code_text,'saved python')
  assert.equal(store.java.code_text,'java draft')
})
test('late initial template cannot replace newly typed source',async()=>{
  let finish
  const empty={...py,code_text:'',exists:false,revision:0}
  const {controller:unused}=fixture()
  const c=new DraftController(empty,{...unused.deps,template:()=>new Promise(resolve=>{finish=resolve})})
  const loading=c.loadInitialTemplate()
  c.setCode('typed while loading')
  finish('template')
  await loading
  assert.equal(c.getSnapshot().draft.code_text,'typed while loading')
})
test('failed cross-language history restore retains current draft and revision',async()=>{
  const {controller:c}=fixture({rewrite:async()=>{throw Error('target revision conflict')}})
  c.setCode('saved before restore')
  assert.equal(await c.rewriteCode(7,'java'),false)
  assert.equal(c.getSnapshot().draft.language,'python')
  assert.equal(c.getSnapshot().draft.code_text,'saved before restore')
  assert.equal(c.getSnapshot().draft.revision,2)
})
