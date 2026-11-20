import {test} from 'node:test'
import assert from 'node:assert/strict'
import {prepareQuickRun} from '../src/local/runRequest.ts'
import {prepareTerminalStart,terminalActive} from '../src/local/terminalTypes.ts'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

test('language changes batch and terminal retry identities',()=>{
  const py=prepareQuickRun('same','','python'),java=prepareQuickRun('same','','java')
  assert.notEqual(py.signature,java.signature)
  assert.equal(java.submission.language,'java')
  const first=prepareTerminalStart(null,'same','python')
  assert.equal(prepareTerminalStart(first,'same','python').request_id,first.request_id)
  assert.notEqual(prepareTerminalStart(first,'same','java').request_id,first.request_id)
})
test('preparation and compilation remain active until a final state',()=>{
  for(const status of ['preparing','compiling'])assert.equal(terminalActive({status}),true)
  for(const status of ['compile_error','compile_time_limit','stopped'])assert.equal(terminalActive({status}),false)
})

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/language-environment-'),'render.cjs')
buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {QueryClient,QueryClientProvider} from '@tanstack/react-query';import {LanguageEnvironment} from './src/local/LanguageEnvironment';import {RunResults} from './src/local/RunResults';export const environment=(state)=>renderToStaticMarkup(<LanguageEnvironment capability={state} refresh={async()=>{}}/>);export function results(data){const client=new QueryClient();client.setQueryData(['run','r'],data);return renderToStaticMarkup(<QueryClientProvider client={client}><RunResults runId="r"/></QueryClientProvider>)}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent'})
const {environment,results}=createRequire(import.meta.url)(output)
test('environment states expose explicit prepare and Apple installation actions',()=>{
  const unprepared=environment({language:'java',label:'Java 21',kind:'native',state:'unprepared',available:false})
  assert.match(unprepared,/准备环境/)
  assert.match(unprepared,/选择语言不会自动下载/)
  const apple=environment({language:'cpp',kind:'native',state:'needs_system_tool',available:false})
  assert.match(apple,/Apple 安装说明/)
  assert.match(apple,/重新检查/)
  assert.doesNotMatch(apple,/准备环境/)
})
test('compile diagnostics render separately as escaped text with the actual language',()=>{
  const html=results({id:'r',problem_id:'p',language:'java',runtime_version:'21.0.13+9',status:'compile_error',passed:0,total:1,cases:[],results:[],compile:{stderr:'<script>missing brace</script>'},error:null})
  assert.match(html,/编译诊断/)
  assert.match(html,/java 21.0.13/)
  assert.match(html,/&lt;script&gt;/)
  assert.doesNotMatch(html,/<script>/)
})
