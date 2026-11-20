import {test} from 'node:test'
import assert from 'node:assert/strict'
import {prepareTerminalInput} from '../src/local/terminalTypes.ts'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

test('Enter sends one line, preserving empty input, Unicode and whitespace',()=>{
  for(const [text,expected] of [['','\n'],[' 你好 ',' 你好 \n'],['a\nb\n','a\nb\n']]){
    assert.equal(prepareTerminalInput(null,text).body.text,expected)
  }
})

test('lost input responses reuse the same request while new content and EOF get new identities',()=>{
  const first=prepareTerminalInput(null,'abc')
  assert.deepEqual(prepareTerminalInput(first,'abc'),first)
  assert.notEqual(prepareTerminalInput(first,'abcd').body.request_id,first.body.request_id)
  const eof=prepareTerminalInput(first,'',true)
  assert.equal(eof.body.text,'')
  assert.equal(eof.body.eof,true)
})

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/terminal-panel-'),'render.cjs')
buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {TerminalPanel} from './src/local/TerminalPanel'; export function render(state,sending=false){return renderToStaticMarkup(React.createElement(TerminalPanel,{state,sending,error:'',onSend:async()=>true,onEof:()=>{},onStop:()=>{}}))}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent'})
const {render}=createRequire(import.meta.url)(output)
const active={id:'test',problem_id:'1',status:'running',stdin:'',stdout:'',stderr:'',transcript:'请输入：',input_closed:false}

test('a live terminal exposes keyboard input, EOF and stop controls',()=>{
  const html=render(active)
  assert.match(html,/请输入：/)
  assert.match(html,/<textarea[^>]*aria-label="终端输入"/)
  assert.match(html,/结束输入/)
  assert.match(html,/停止/)
  assert.doesNotMatch(html,/<textarea[^>]*disabled/)
})

test('completed programs disable keyboard input and render output as text',()=>{
  const html=render({...active,status:'executed',transcript:'<script>alert(1)</script>',input_closed:true})
  assert.match(html,/<textarea[^>]*disabled/)
  assert.match(html,/&lt;script&gt;/)
  assert.doesNotMatch(html,/<script>/)
})

test('sending retains keyboard focus by making input readonly instead of disabled',()=>{
  const html=render(active,true)
  assert.match(html,/<textarea[^>]*readonly/i)
  assert.doesNotMatch(html,/<textarea[^>]*disabled/)
})
test('compiling remains stoppable and does not offer stdin before ready',()=>{
  const html=render({...active,status:'compiling',language:'java',runtime_version:'21'})
  assert.match(html,/编译中/)
  assert.match(html,/停止/)
  assert.match(html,/<textarea[^>]*disabled/)
})
