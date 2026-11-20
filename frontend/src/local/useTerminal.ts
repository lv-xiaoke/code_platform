import {useCallback,useEffect,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from './api'
import {prepareTerminalInput,prepareTerminalStart,terminalActive,type TerminalStartBody,type TerminalInputRequest,type TerminalState} from './terminalTypes'

export function useTerminal(problemId:string){
  const qc=useQueryClient()
  const [id,setId]=useState<string|null>(null),[starting,setStarting]=useState(false),[sending,setSending]=useState(false),[error,setError]=useState('')
  const requestKey=useRef<string|null>(null)
  const ownedRequests=useRef(new Set<string>())
  const startBody=useRef<TerminalStartBody|null>(null)
  const startPromise=useRef<Promise<void>|null>(null)
  const pendingInput=useRef<TerminalInputRequest|null>(null),inputLock=useRef(false)
  const state=useQuery({queryKey:['terminal',id],queryFn:()=>api<TerminalState>('/terminals/'+id),enabled:!!id,
    refetchInterval:q=>terminalActive(q.state.data)?250:false,staleTime:0})
  const adopt=useCallback(async(value:TerminalState)=>{
    // A slow poll must never replace the response to a newer input/stop.
    await qc.cancelQueries({queryKey:['terminal',value.id],exact:true})
    qc.setQueryData(['terminal',value.id],value)
  },[qc])
  const start=useCallback((source:string,language='python')=>{
    if(startPromise.current)return startPromise.current
    const previous=startBody.current
    const body=prepareTerminalStart(previous,source,language)
    startBody.current=body;requestKey.current=body.request_id
    setStarting(true);setError('');pendingInput.current=null
    const promise=(async()=>{
      try{
        for(const key of ownedRequests.current){
          if(key===body.request_id)continue
          await api(`/terminal-requests/${key}/stop`,{method:'POST'})
          ownedRequests.current.delete(key)
        }
        ownedRequests.current.add(body.request_id)
        const value=await api<TerminalState>(`/problems/${problemId}/terminals`,{method:'POST',body:JSON.stringify(body)})
        await adopt(value);setId(value.id);startBody.current=null
      }catch(cause){setError((cause as Error).message)}finally{setStarting(false);startPromise.current=null}
    })()
    startPromise.current=promise
    return promise
  },[adopt,problemId])
  const stop=useCallback(async()=>{
    if(!requestKey.current)return true
    setError('')
    try{
      // Cancel by request identity, including a start whose response was lost.
      for(const key of new Set([...ownedRequests.current,requestKey.current])){
        const value=await api<TerminalState>(`/terminal-requests/${key}/stop`,{method:'POST'})
        if(value.id)await adopt(value)
      }
      await startPromise.current
      ownedRequests.current.clear()
      startBody.current=null
      return true
    }catch(cause){setError((cause as Error).message);return false}
  },[adopt])
  const send=useCallback(async(text:string,eof=false)=>{
    if(!id||inputLock.current)return false
    inputLock.current=true;setSending(true);setError('')
    const pending=prepareTerminalInput(pendingInput.current,text,eof)
    pendingInput.current=pending
    try{
      const value=await api<TerminalState>(`/terminals/${id}/input`,{method:'POST',body:JSON.stringify(pending.body)})
      await adopt(value);pendingInput.current=null;return true
    }catch(cause){setError((cause as Error).message);return false}
    finally{inputLock.current=false;setSending(false)}
  },[adopt,id])
  useEffect(()=>{
    if(state.data&&!terminalActive(state.data))void qc.invalidateQueries({queryKey:['runs',problemId]})
  },[state.data?.status,problemId,qc])
  useEffect(()=>{
    const cleanup=()=>{for(const key of new Set([...ownedRequests.current,...(requestKey.current?[requestKey.current]:[])]))void api(`/terminal-requests/${key}/stop`,{method:'POST',keepalive:true}).catch(()=>{})}
    window.addEventListener('pagehide',cleanup)
    return()=>{window.removeEventListener('pagehide',cleanup);cleanup()}
  },[])
  return {id,state:state.data,start,send,stop,starting,sending,error:error||state.error?.message||'',busy:starting||terminalActive(state.data)}
}
