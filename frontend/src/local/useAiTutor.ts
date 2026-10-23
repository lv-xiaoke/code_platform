import {useCallback,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,ApiError} from './api'
import type {AiChat,AiRequest} from './aiTypes'

export function useAiTutor(problemId:string,enabled:boolean){
  const qc=useQueryClient(),[sending,setSending]=useState(false),[error,setError]=useState('')
  const pending=useRef<AiRequest|null>(null),promise=useRef<Promise<boolean>|null>(null)
  const key=['ai-chat',problemId]
  const query=useQuery({queryKey:key,queryFn:({signal})=>api<AiChat>(`/problems/${problemId}/ai`,{signal}),enabled,
    refetchInterval:q=>q.state.data?.busy?350:false,staleTime:0})
  const adopt=useCallback(async(chat:AiChat)=>{
    await qc.cancelQueries({queryKey:['ai-chat',problemId],exact:true})
    qc.setQueryData(['ai-chat',problemId],chat)
  },[qc,problemId])
  function send(request:AiRequest){
    if(promise.current)return promise.current
    // Retry uncertain transport failures with the same identity, never an automatic paid retry.
    const old=pending.current
    const signature=(value:AiRequest)=>JSON.stringify({...value,request_id:''})
    const body=old&&signature(old)===signature(request)?old:request
    pending.current=body;setSending(true);setError('')
    const task=(async()=>{
      try{
        const result=await api<AiChat>(`/problems/${problemId}/ai`,{method:'POST',body:JSON.stringify(body),signal:AbortSignal.timeout(20000)})
        await adopt(result);pending.current=null;return true
      }catch(cause){
        if(cause instanceof ApiError&&cause.status<500)pending.current=null
        setError((cause as Error).name==='TimeoutError'?'发送超时，问题已保留。重发相同问题会复用原请求，也可重新读取对话。':(cause as Error).message);return false
      }finally{setSending(false);promise.current=null}
    })()
    promise.current=task;return task
  }
  const stop=useCallback(async()=>{
    // Resolve a submitted start before stopping, including a response which was lost.
    await promise.current
    if(!qc.getQueryData<AiChat>(['ai-chat',problemId])?.busy&&!pending.current)return true
    try{
      await adopt(await api<AiChat>(`/problems/${problemId}/ai/stop`,{method:'POST',signal:AbortSignal.timeout(20000)}))
      pending.current=null;return true
    }catch(cause){setError((cause as Error).message);return false}
  },[problemId,adopt,qc])
  return {problemId,chat:query.data,sending,error:error||query.error?.message||'',send,stop,reload:query.refetch}
}
