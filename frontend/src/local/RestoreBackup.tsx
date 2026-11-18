import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from './api'

type Preview={ticket:string;counts:Record<string,number>;state:string;error?:string}
export function RestoreBackup(){
  const enabled=useQuery({queryKey:['desktop-capabilities'],queryFn:()=>api<{restore:boolean}>('/desktop/capabilities')})
  const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState<Preview|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
  if(!enabled.data?.restore)return null
  async function inspect(){
    if(!file)return
    setBusy(true);setError('')
    try{const form=new FormData();form.set('file',file);setPreview(await api<Preview>('/desktop/restore/preview',{method:'POST',body:form}))}catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  async function restore(){
    if(!preview||!window.confirm('恢复会替换当前学习记录。程序会先备份当前数据，然后重启。是否继续？'))return
    setBusy(true);setError('')
    try{
      await api(`/desktop/restore/${preview.ticket}/confirm`,{method:'POST'})
      setMessage('正在恢复并重启，请保持本页打开…')
      let failures=0
      for(let i=0;i<120;i++){
        await new Promise(resolve=>setTimeout(resolve,1000))
        try{
          const response=await api<Preview>(`/desktop/restore/${preview.ticket}`)
          if(response.state==='completed'){window.location.reload();return}
          if(response.state==='failed'){setError(response.error??'恢复失败，原数据已保留');setMessage('');return}
        }catch{failures++}
      }
      throw new Error(`暂未确认恢复结果，请重新打开 CodeTop 后检查记录（连接重试 ${failures} 次）。`)
    }catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  return <section><h3>恢复完整备份</h3><p className="muted">选择旧版本导出的完整备份 ZIP，先校验并预览。确认后会先备份当前数据，再恢复并重启。</p><input type="file" accept=".zip" aria-label="完整备份文件" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]??null);setPreview(null);setError('')}}/><button disabled={busy||!file} onClick={()=>void inspect()}>检查备份</button>{preview&&<div><p>备份包含 {preview.counts.problems??0} 道题、{preview.counts.notes??0} 份笔记、{preview.counts.code_runs??0} 条运行记录。</p><button disabled={busy} onClick={()=>void restore()}>确认恢复并重启</button></div>}{message&&<p role="status">{message}</p>}{error&&<p role="alert" className="local-error">{error}</p>}</section>
}
