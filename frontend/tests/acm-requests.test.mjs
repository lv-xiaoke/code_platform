import {test} from 'node:test'
import assert from 'node:assert/strict'
import {prepareRun,prepareQuickRun} from '../src/local/runRequest.ts'

const draft={name:'one',stdin:'a',expected_stdout:'a',comparison:'tokens'}
const suite={revision:1,cases:[draft],draft}
test('retry identity stays the same for the same saved suite',()=>{
  assert.equal(prepareRun('print(1)','suite',suite).signature,prepareRun('print(1)','suite',structuredClone(suite)).signature)
})
test('changing saved tests starts a fresh retry identity without sending client suite cases',()=>{
  const first=prepareRun('print(1)','suite',suite)
  const next=prepareRun('print(1)','suite',{...suite,revision:2,cases:[{...draft,stdin:'b'}]})
  assert.notEqual(first.signature,next.signature)
  assert.deepEqual(next.submission,{source_code:'print(1)',language:'python',mode:'suite'})
})
test('custom runs use the current scratch input',()=>{
  const first=prepareRun('print(1)','custom',suite)
  const next=prepareRun('print(1)','custom',{...suite,draft:{...draft,stdin:'b'}})
  assert.notEqual(first.signature,next.signature)
  assert.deepEqual(next.submission.cases,[{...draft,stdin:'b'}])
})

test('quick run executes code with empty stdin and no expected output by default',()=>{
  const {submission}=prepareQuickRun('print(3)')
  assert.equal(submission.mode,'custom')
  assert.equal(submission.cases.length,1)
  assert.equal(submission.cases[0].stdin,'')
  assert.equal(submission.cases[0].expected_stdout,null)
})

test('explicit stdin changes quick run identity without enabling output comparison',()=>{
  const first=prepareQuickRun('print(input())','abc\n')
  assert.equal(first.submission.cases[0].stdin,'abc\n')
  assert.equal(first.submission.cases[0].expected_stdout,null)
  assert.notEqual(first.signature,prepareQuickRun('print(input())').signature)
})
