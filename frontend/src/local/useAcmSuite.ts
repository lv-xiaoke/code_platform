import {useCallback,useEffect,useRef,useState} from 'react'
import {useQueryClient} from '@tanstack/react-query'
import {api} from './api'
import type {AcmCase,AcmSuite} from './acmTypes'

export const EMPTY_CASE:AcmCase={name:'自定义测试',stdin:'',expected_stdout:null,comparison:'tokens'}
const content=(suite:AcmSuite)=>JSON.stringify({cases:suite.cases,draft:suite.draft})

export function useAcmSuite(id:string,initial:AcmSuite){
  const qc=useQueryClient()
  const initialValue:AcmSuite={revision:initial.revision,cases:initial.cases,draft:initial.draft??{...EMPTY_CASE}}
  const [value,setValue]=useState<AcmSuite>(initialValue),current=useRef(initialValue),saved=useRef(content(initialValue)),revision=useRef(initial.revision)
  const running=useRef<Promise<boolean>|null>(null)
  const [status,setStatus]=useState('已保存'),[error,setError]=useState('')
  const dirty=()=>content(current.current)!==saved.current
  const flush=useCallback(async():Promise<boolean>=>{
    if(running.current){const ok=await running.current;return ok&&dirty()?flush():ok}
    if(!dirty()){setStatus('已保存');return true}
    const sent={revision:revision.current,cases:current.current.cases,draft:current.current.draft}
    const sentContent=JSON.stringify({cases:sent.cases,draft:sent.draft})
    setStatus('保存中');setError('')
    running.current=api<AcmSuite>(`/problems/${id}/test-cases`,{method:'PUT',body:JSON.stringify(sent)}).then(async result=>{
      // Discard GETs started before this save; they may carry an older revision.
      await qc.cancelQueries({queryKey:['acm',id],exact:true})
      revision.current=result.revision;saved.current=sentContent
      current.current={...current.current,revision:result.revision};setValue(current.current)
      qc.setQueryData<AcmSuite>(['acm',id],previous=>previous?{...previous,...result}:previous)
      setStatus(dirty()?'等待保存':'已保存');return true
    }).catch(e=>{setStatus('保存失败');setError(e.message);return false}).finally(()=>{running.current=null})
    const ok=await running.current
    return ok&&dirty()?flush():ok
  },[id,qc])
  const update=useCallback((patch:Partial<AcmSuite>)=>{const next={...current.current,...patch};current.current=next;setValue(next);setStatus('等待保存')},[])
  const reloadServer=useCallback(async()=>{
    if(running.current)await running.current
    const before=current.current
    try{
      const latest=await api<AcmSuite>(`/problems/${id}/acm`)
      if(current.current!==before){setError('读取期间有新的编辑，已保留草稿，请重试。');return false}
      const value={revision:latest.revision,cases:latest.cases,draft:latest.draft??{...EMPTY_CASE}}
      qc.setQueryData(['acm',id],latest)
      current.current=value;setValue(value);revision.current=latest.revision;saved.current=content(value);setStatus('已保存');setError('');return true
    }catch(e){setError((e as Error).message);return false}
  },[id,qc])
  useEffect(()=>{
    // A background refresh may follow a cached first render. Adopt it only
    // while clean, so refreshed data never replaces a live local edit.
    if(initial.revision>revision.current&&!running.current&&!dirty()){
      const next={revision:initial.revision,cases:initial.cases,draft:initial.draft??{...EMPTY_CASE}}
      current.current=next;revision.current=next.revision;saved.current=content(next);setValue(next)
    }
  },[initial])
  useEffect(()=>{if(status==='等待保存'){const timer=setTimeout(()=>void flush(),700);return()=>clearTimeout(timer)}},[value,status,flush])
  useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty()){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[])
  return {value,update,flush,reloadServer,snapshot:()=>current.current,status,error}
}
