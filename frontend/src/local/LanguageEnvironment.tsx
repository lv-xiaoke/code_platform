import {useState} from 'react'
import {api} from './api'
import type {LanguageCapability} from './languageTypes'

const stateLabels:Record<string,string>={unprepared:'未准备',downloading:'下载中',verifying:'校验中',extracting:'解压中',ready:'已就绪',failed:'准备失败',needs_system_tool:'需要系统工具',unsupported:'暂不支持运行'}
export function LanguageEnvironment({capability,refresh}:{capability:LanguageCapability;refresh:()=>Promise<unknown>}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  const working=['downloading','verifying','extracting'].includes(capability.state)
  async function action(cancel=false){
    setBusy(true);setError('')
    try{await api(`/runner/languages/${capability.language}/${cancel?'cancel':'prepare'}`,{method:'POST'});await refresh()}
    catch(cause){setError((cause as Error).message)}finally{setBusy(false)}
  }
  return <details className="language-environment" open={!capability.available}><summary>语言环境 · {capability.label??capability.language} · {stateLabels[capability.state]??capability.state}</summary>
    {capability.runtime_version&&<p>版本：{capability.runtime_version}</p>}
    {capability.state==='needs_system_tool'?<p>请安装 Apple Command Line Tools，再重新检查。无需完整 Xcode 或付费开发者账号。<a href="https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/" target="_blank" rel="noreferrer">Apple 安装说明</a></p>:!capability.available&&capability.state!=='unsupported'&&<p>首次准备需要联网，准备完成后可离线运行。选择语言不会自动下载。</p>}
    {(error||capability.error)&&<p className="local-error" role="alert">{error||capability.error}</p>}
    {working?<button disabled={busy} onClick={()=>void action(true)}>取消准备</button>:capability.state==='needs_system_tool'?<button disabled={busy} onClick={()=>void action()}>重新检查</button>:!capability.available&&capability.kind==='native'&&capability.state!=='unsupported'?<button disabled={busy} onClick={()=>void action()}>{busy?'正在准备…':'准备环境'}</button>:<button disabled={busy} onClick={()=>void refresh()}>重新检查</button>}
    {capability.available&&capability.limits&&<p className="muted small">每组 {capability.limits.wall_seconds} 秒 · 总内存目标 {capability.limits.memory_mb} MiB{capability.limits.heap_mb?` · 堆上限 ${capability.limits.heap_mb} MiB`:''} · 输出 64 KiB{capability.memory_enforcement==='rss-monitor'?'；Mac 使用进程组 RSS 采样，可能短暂超出阈值。':''}</p>}
    {capability.sdk&&<p className="muted small">SDK：{capability.sdk}</p>}
  </details>
}
