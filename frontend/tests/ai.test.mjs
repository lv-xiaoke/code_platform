import {test} from 'node:test'
import assert from 'node:assert/strict'
import {makeAiRequest} from '../src/local/aiTypes.ts'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

test('context opt-outs omit code and private notes; run identity remains explicit',()=>{
  const request=makeAiRequest('why?',{code:'unsaved draft',language:'python',datasetId:'dataset',notes:'private'}, {statement:true,code:false,notes:false,history:false},'old-run')
  assert.equal(request.code,'')
  assert.equal(request.include_code,false)
  assert.equal(request.notes,null)
  assert.equal(request.include_history,false)
  assert.equal(request.run_id,'old-run')
  assert.equal(request.dataset_id,'dataset')
})

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/ai-render-'),'render.cjs')
buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {AiMarkdown} from './src/local/AiMarkdown'; import PracticeDialog from './src/local/PracticeDialog'; import {QueryClient,QueryClientProvider} from '@tanstack/react-query'; export function render(content){return renderToStaticMarkup(React.createElement(AiMarkdown,{content}))}; export function practice(){return renderToStaticMarkup(React.createElement(QueryClientProvider,{client:new QueryClient()},React.createElement(PracticeDialog,{id:'test',datasetId:'d',onClose:()=>{}})))}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent',loader:{'.css':'empty'}})
const {render,practice}=createRequire(import.meta.url)(output)
test('AI markdown escapes raw HTML, blocks executable links and remote images, preserves code',()=>{
  const html=render('<script>alert(1)</script>\n[x](javascript:alert)\n![image](https://example.com/a.png)\n```python\nprint("<img src=x onerror=evil()>")\n```')
  assert.doesNotMatch(html,/<script|<img|href="javascript:/)
  assert.match(html,/&lt;script&gt;/)
  assert.match(html,/复制代码/)
  assert.match(html,/hljs-/)
})
test('every newly opened practice dialog starts maximized',()=>{
  assert.match(practice(),/class="practice-dialog is-maximized"/)
})

test('current draft and notes are captured at send time and question validation preserves draft',()=>{
  const request=makeAiRequest(' explain ',{code:'print(2)',language:'python',datasetId:'d',notes:'note'}, {statement:true,code:true,notes:true,history:true})
  assert.equal(request.code,'print(2)')
  assert.equal(request.notes,'note')
  assert.equal(request.question,'explain')
  assert.throws(()=>makeAiRequest(' ',{code:'',language:'python',datasetId:'d',notes:''},{statement:true,code:true,notes:false,history:false}),/问题/)
})
