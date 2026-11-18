import type {RunnerHealth} from './acmTypes'

export function runnerLabel(health:RunnerHealth):string {
  return `${health.kind==='native'?'本机 Python':'Docker'}${health.available?' 已就绪':' 未就绪'}`
}

export async function ensureRunnerConsent(health:RunnerHealth,confirm:()=>boolean,accept:()=>Promise<unknown>):Promise<boolean>{
  if(health.kind!=='native'||!health.consent_required)return true
  if(!confirm())return false
  await accept()
  return true
}
