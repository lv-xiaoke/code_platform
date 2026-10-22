import {test} from 'node:test'
import assert from 'node:assert/strict'
import {flushPractice} from '../src/local/practiceSession.ts'

test('closing waits for code and test draft saves, even when one save fails',async()=>{
  let release
  let codeSaved=false
  const code=new Promise(resolve=>{release=()=>{codeSaved=true;resolve(true)}})
  let finished=false
  const closing=flushPractice(()=>code,async()=>false).then(ok=>{finished=true;return ok})
  await Promise.resolve()
  assert.equal(finished,false)
  release()
  assert.equal(await closing,false)
  assert.equal(codeSaved,true)
})

test('closing without a mounted test editor still saves code',async()=>{
  let saved=0
  assert.equal(await flushPractice(async()=>{saved++;return true},null),true)
  assert.equal(saved,1)
})

test('a rejected save keeps the practice session open while the other draft is saved',async()=>{
  let saved=false
  assert.equal(await flushPractice(async()=>{throw new Error('offline')},async()=>{saved=true;return true}),false)
  assert.equal(saved,true)
})
