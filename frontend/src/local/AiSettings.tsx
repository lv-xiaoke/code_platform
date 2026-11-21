import {useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from './api'
import type {AiConfig} from './aiTypes'
import './ai.css'

export function AiSettings(){
  const qc=useQueryClient(),[key,setKey]=useState(''),[model,setModel]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('')
  const config=useQuery({queryKey:['ai-config'],queryFn:()=>api<AiConfig>('/ai/settings'),staleTime:0})
  async function save(test=false){
    setBusy(true);setMessage('');setError('')
    try{
      const value=await api<AiConfig>('/ai/settings',{method:'PUT',body:JSON.stringify({api_key:key,model:model||config.data?.model||'deepseek-flash'})})
      qc.setQueryData(['ai-config'],value);setKey('')
      setMessage(test?(await api<{message:string}>('/ai/test',{method:'POST'})).message:'AI 设置已保存')
    }catch(cause){setError((cause as Error).message)}finally{setBusy(false)}
  }
  return <section className="ai-settings" aria-label="AI 设置"><h3>AI 助教 · DeepSeek</h3><p className="muted small">{config.data?.configured?`已配置 ${config.data.key_hint}`:'尚未配置 API Key'}。发送问题时，所选题面、代码等内容会发送给 DeepSeek。</p>
    <label>API Key<input aria-label="DeepSeek API Key" type="password" autoComplete="off" value={key} placeholder={config.data?.configured?'留空保留已有 Key':'填写 DeepSeek API Key'} onChange={e=>setKey(e.target.value)}/></label>
    <label>模型<select aria-label="AI 模型" value={model||config.data?.model||'deepseek-flash'} onChange={e=>setModel(e.target.value)}><option value="deepseek-flash">DeepSeek Flash · 日常问答</option><option value="deepseek-v4-pro">DeepSeek V4 Pro · 复杂分析</option></select></label>
    <p className="muted small">Key 只保存在本机（Windows/macOS 使用系统加密存储，其他系统为仅当前用户可读的本地文件），学习数据备份不包含 Key。测试连接会发送一次简短请求。</p>
    <div className="button-row"><button disabled={busy||config.isPending} onClick={()=>void save()}>保存 AI 设置</button><button disabled={busy||config.isPending||(!key&&!config.data?.configured)} onClick={()=>void save(true)}>{busy?'处理中…':'保存并测试连接'}</button></div>
    {(error||config.error||config.data?.error)&&<p className="local-error" role="alert">{error||config.error?.message||config.data?.error}</p>}{message&&<p className="local-success" role="status">{message}</p>}
  </section>
}
