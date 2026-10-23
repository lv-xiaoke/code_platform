import {test} from 'node:test'
import assert from 'node:assert/strict'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/console-output-'),'render.cjs')
buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {ConsoleOutput} from './src/local/ConsoleOutput'; export function render(result){return renderToStaticMarkup(React.createElement(ConsoleOutput,{result,statusLabel:result.status}))}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent'})
const {render}=createRequire(import.meta.url)(output)
const result={name:'运行',stdin:'',expected_stdout:null,comparison:'tokens',stdout:'3\n',stderr:'',status:'executed',exit_code:0,duration_ms:20}

test('a normal program shows its output directly without test comparison controls',()=>{
  const html=render(result)
  assert.match(html,/标准输出/)
  assert.match(html,/<pre>3\n<\/pre>/)
  assert.doesNotMatch(html,/期望输出|组通过|<summary/)
})

test('Python errors remain visible without having to expand a test result',()=>{
  const html=render({...result,stdout:'',stderr:'AssertionError: expected 3',status:'runtime_error'})
  assert.match(html,/错误信息/)
  assert.match(html,/AssertionError: expected 3/)
  assert.match(html,/（无输出）/)
  assert.doesNotMatch(html,/<details/)
})

test('a previous run keeps its actual stdin available in collapsed details',()=>{
  const html=render({...result,stdin:'old input\n'})
  assert.match(html,/<summary>本次输入<\/summary>/)
  assert.match(html,/<pre>old input\n<\/pre>/)
  assert.doesNotMatch(html,/<details[^>]*open/)
})
