import {useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {api,type Note} from './api'
import {DraftController} from './codeDraftState'
import type {CodeDraft,LanguageCapability,RewriteResult} from './languageTypes'

export function useCodeDraft(id:string,initial:Note,stopActive:()=>Promise<boolean>){
  const stop=useRef(stopActive);stop.current=stopActive
  const [controller]=useState(()=>new DraftController({problem_id:id,language:initial.language,
    code_text:initial.code_text,revision:initial.draft_revision??0,exists:initial.draft_exists??false,
    created_at:initial.updated_at,updated_at:initial.updated_at},{
    stopActive:()=>stop.current(),
    read:language=>api<CodeDraft>(`/problems/${id}/code/drafts/${encodeURIComponent(language)}`),
    write:(language,code_text,revision)=>api<CodeDraft>(`/problems/${id}/code/drafts/${encodeURIComponent(language)}`,{method:'PUT',body:JSON.stringify({revision,code_text})}),
    select:async language=>{
      const pref=await api<{revision:number}>(`/problems/${id}/code/preference`)
      return api(`/problems/${id}/code/preference`,{method:'PUT',body:JSON.stringify({language,revision:pref.revision})})
    },
    template:async language=>{
      const data=await api<{languages:LanguageCapability[]}>('/runner/languages')
      return data.languages.find(item=>item.language===language)?.template??''
    },
    rewrite:(language,revision,historyId)=>api<RewriteResult>(`/problems/${id}/code/rewrite`,{method:'POST',body:JSON.stringify({language,revision,history_id:historyId??null})}),
  }))
  const state=useSyncExternalStore(controller.subscribe,controller.getSnapshot,controller.getSnapshot)
  useEffect(()=>{void controller.loadInitialTemplate()},[controller])
  useEffect(()=>{
    if(state.status==='等待保存'&&!state.changing){const timer=setTimeout(()=>void controller.flush(),700);return()=>clearTimeout(timer)}
  },[controller,state])
  useEffect(()=>{
    const warn=(event:BeforeUnloadEvent)=>{const current=controller.getSnapshot();if(current.dirty||current.changing){event.preventDefault();event.returnValue=''}}
    window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)
  },[controller])
  return {...state,setCode:controller.setCode,flush:controller.flush,switchLanguage:controller.switchLanguage,
    rewriteCode:controller.rewriteCode,reloadServer:controller.reloadServer}
}
