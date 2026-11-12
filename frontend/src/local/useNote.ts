import {useCallback,useEffect,useRef,useState} from 'react'
import {api,ApiError,type Note,type Detail} from './api'

export function useNote(id:string,initial:Note){
  const [draft,setDraftState]=useState(initial)
  const draftRef=useRef(initial),saved=useRef(initial),revision=useRef(initial.revision)
  const running=useRef<Promise<boolean>|null>(null)
  const transition=useRef<Promise<boolean>|null>(null)
  const [changingCode,setChangingCode]=useState(false)
  const [status,setStatus]=useState('已保存'),[error,setError]=useState('')
  const [conflict,setConflict]=useState(false)
  const changed=()=>['body_md','code_text','language'].some(k=>draftRef.current[k as keyof Note]!==saved.current[k as keyof Note])
  const save=useCallback(async():Promise<boolean>=>{
    if(running.current){if(!await running.current)return false;return changed()?save():true}
    if(!changed())return true
    const sent={...draftRef.current,revision:revision.current}
    setStatus('保存中');setError('');setConflict(false)
    running.current=api<Note>(`/problems/${id}/note`,{method:'PUT',body:JSON.stringify({revision:sent.revision,body_md:sent.body_md,code_text:sent.code_text,language:sent.language})}).then(result=>{
      saved.current=sent;revision.current=result.revision;setStatus(changed()?'等待保存':'已保存');return true
    }).catch(e=>{setStatus('保存失败');setError(e.message);setConflict(e instanceof ApiError&&e.status===409);return false}).finally(()=>{running.current=null})
    const ok=await running.current
    if(ok&&changed())return save()
    return ok
  },[id])
  const flush=useCallback(async():Promise<boolean>=>{
    if(transition.current&&!await transition.current)return false
    return save()
  },[save])
  const rewriteCode=useCallback((historyId?:number):Promise<boolean>=>{
    if(transition.current)return transition.current
    setChangingCode(true)
    // Reserve the transition synchronously before any save or close can race it.
    const task=Promise.resolve().then(async()=>{
      if(!await save())return false
      setStatus('归档中');setError('');setConflict(false)
      try{
        const result=await api<Note>(`/problems/${id}/code/rewrite`,{method:'POST',body:JSON.stringify({revision:revision.current,history_id:historyId??null})})
        saved.current=result;revision.current=result.revision
        draftRef.current={...draftRef.current,code_text:result.code_text,language:result.language,revision:result.revision,updated_at:result.updated_at}
        setDraftState(draftRef.current);setStatus(changed()?'等待保存':'已保存')
        return true
      }catch(e){setStatus('归档失败');setError((e as Error).message);setConflict(e instanceof ApiError&&e.status===409);return false}
    }).finally(()=>{transition.current=null;setChangingCode(false)})
    transition.current=task
    return task
  },[id,save])
  const setDraft=useCallback((value:Partial<Note>)=>{const next={...draftRef.current,...value};draftRef.current=next;setDraftState(next);setStatus('等待保存')},[])
  const reloadServer=useCallback(async()=>{
    if(transition.current)await transition.current
    if(running.current)await running.current
    const requested=draftRef.current
    try{
      const latest=(await api<Detail>(`/problems/${id}`)).note
      if(draftRef.current!==requested){setError('读取期间有新的编辑，已保留当前草稿，请重新导出并载入。');return false}
      saved.current=latest;draftRef.current=latest;revision.current=latest.revision;setDraftState(latest);setStatus('已保存');setError('');setConflict(false);return true
    }catch(e){setError((e as Error).message);return false}
  },[id])
  useEffect(()=>{if(status==='等待保存'){const timeout=setTimeout(()=>void flush(),700);return()=>clearTimeout(timeout)}},[draft,flush,status])
  useEffect(()=>{const warn=(event:BeforeUnloadEvent)=>{if(changed()||transition.current){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[])
  return {draft,setDraft,status,error,conflict,flush,reloadServer,dirty:changed(),rewriteCode,changingCode}
}
