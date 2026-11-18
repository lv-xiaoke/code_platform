import {test} from 'node:test'
import assert from 'node:assert/strict'
import {runnerLabel,ensureRunnerConsent} from '../src/local/runnerEnvironment.ts'

test('native and Docker have accurate readiness labels',()=>{
  assert.equal(runnerLabel({kind:'native',available:true}),'本机 Python 已就绪')
  assert.equal(runnerLabel({kind:'docker',available:false}),'Docker 未就绪')
})
test('cancel never accepts; acceptance persists only after confirmation',async()=>{
  let count=0
  const health={kind:'native',consent_required:true}
  assert.equal(await ensureRunnerConsent(health,()=>false,async()=>{count++}),false)
  assert.equal(count,0)
  assert.equal(await ensureRunnerConsent(health,()=>true,async()=>{count++}),true)
  assert.equal(count,1)
  await ensureRunnerConsent({...health,consent_required:false},()=>{throw Error('repeat prompt')},async()=>{count++})
  assert.equal(count,1)
})
