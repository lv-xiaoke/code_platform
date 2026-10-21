import {useCallback,useEffect,useRef,useState} from 'react'
import {api,ApiError,type Note,type Detail} from './api'

export function useNote(id:string,initial:Note){
  const [draft,setDraftState]=useState(initial)
  const draftRef=useRef(initial),saved=useRef(initial),revision=useRef(initial.revision)
  const running=useRef<Promise<boolean>|null>(null)
  const [status,setStatus]=useState('已保存'),[error,setError]=useState('')
  const [conflict,setConflict]=useState(false)
  const changed=()=>['body_md','code_text','language'].some(k=>draftRef.current[k as keyof Note]!==saved.current[k as keyof Note])
  const flush=useCallback(async():Promise<boolean>=>{
    if(running.current){await running.current;return changed()?flush():true}
    if(!changed())return true
    const sent={...draftRef.current,revision:revision.current}
    setStatus('保存中');setError('');setConflict(false)
    running.current=api<Note>(`/problems/${id}/note`,{method:'PUT',body:JSON.stringify({revision:sent.revision,body_md:sent.body_md,code_text:sent.code_text,language:sent.language})}).then(result=>{
      saved.current=sent;revision.current=result.revision;setStatus(changed()?'等待保存':'已保存');return true
    }).catch(e=>{setStatus('保存失败');setError(e.message);setConflict(e instanceof ApiError&&e.status===409);return false}).finally(()=>{running.current=null})
    const ok=await running.current
    if(ok&&changed())return flush()
    return ok
  },[id])
  const setDraft=useCallback((value:Partial<Note>)=>{const next={...draftRef.current,...value};draftRef.current=next;setDraftState(next);setStatus('等待保存')},[])
  const reloadServer=useCallback(async()=>{
    if(running.current)await running.current
    const requested=draftRef.current
    try{
      const latest=(await api<Detail>(`/problems/${id}`)).note
      if(draftRef.current!==requested){setError('读取期间有新的编辑，已保留当前草稿，请重新导出并载入。');return false}
      saved.current=latest;draftRef.current=latest;revision.current=latest.revision;setDraftState(latest);setStatus('已保存');setError('');setConflict(false);return true
    }catch(e){setError((e as Error).message);return false}
  },[id])
  useEffect(()=>{if(status==='等待保存'){const timeout=setTimeout(()=>void flush(),700);return()=>clearTimeout(timeout)}},[draft,flush,status])
  useEffect(()=>{const warn=(event:BeforeUnloadEvent)=>{if(changed()){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[])
  return {draft,setDraft,status,error,conflict,flush,reloadServer,dirty:changed()}
}
