import {test} from 'node:test'
import assert from 'node:assert/strict'
import {prepareRun} from '../src/local/runRequest.ts'

const draft={name:'one',stdin:'a',expected_stdout:'a',comparison:'tokens'}
const suite={revision:1,cases:[draft],draft}
test('retry identity stays the same for the same saved suite',()=>{
  assert.equal(prepareRun('print(1)','suite',suite).signature,prepareRun('print(1)','suite',structuredClone(suite)).signature)
})
test('changing saved tests starts a fresh retry identity without sending client suite cases',()=>{
  const first=prepareRun('print(1)','suite',suite)
  const next=prepareRun('print(1)','suite',{...suite,revision:2,cases:[{...draft,stdin:'b'}]})
  assert.notEqual(first.signature,next.signature)
  assert.deepEqual(next.submission,{source_code:'print(1)',mode:'suite'})
})
test('custom runs use the current scratch input',()=>{
  const first=prepareRun('print(1)','custom',suite)
  const next=prepareRun('print(1)','custom',{...suite,draft:{...draft,stdin:'b'}})
  assert.notEqual(first.signature,next.signature)
  assert.deepEqual(next.submission.cases,[{...draft,stdin:'b'}])
})
