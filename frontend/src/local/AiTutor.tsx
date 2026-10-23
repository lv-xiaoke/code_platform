import {useEffect,useRef,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from './api'
import {AiSettings} from './AiSettings'
import {AiMarkdown} from './AiMarkdown'
import {makeAiRequest,type AiConfig,type AiContext,type AiOptions,type AiRequest} from './aiTypes'
import type {useAiTutor} from './useAiTutor'
import type {CodeRun} from './acmTypes'
import './ai.css'

const prompts=[['给点提示','我暂时没有思路，请先给我一个提示，不要直接给完整答案。'],['解释样例','请逐步解释本题样例的输入与输出。'],['分析代码','请分析我的当前代码，指出逻辑问题和遗漏的边界情况。'],['分析报错','请分析本次运行的问题，解释原因并给出修改建议。']]
export function AiTutor({context,tutor,trigger,onAppend,onAppended}:{context:AiContext;tutor:ReturnType<typeof useAiTutor>;trigger:{id:string;runId:string}|null;onAppend:(text:string)=>void;onAppended:()=>void}){
  const [question,setQuestion]=useState(''),[options,setOptions]=useState<AiOptions>({statement:true,code:true,notes:false,history:false}),[settings,setSettings]=useState(false),[runId,setRunId]=useState<string|undefined>(),[localError,setLocalError]=useState(''),[notice,setNotice]=useState('')
  const config=useQuery({queryKey:['ai-config'],queryFn:()=>api<AiConfig>('/ai/settings'),staleTime:0})
  useEffect(()=>{if(config.data&&!config.data.configured)setSettings(true)},[config.data?.configured])
  const messages=tutor.chat?.messages??[],busy=tutor.sending||!!tutor.chat?.busy
  const bottom=useRef<HTMLDivElement>(null),scroller=useRef<HTMLDivElement>(null),follow=useRef(true),seen=useRef('')
  useEffect(()=>{if(follow.current)bottom.current?.scrollIntoView({block:'end'})},[messages[messages.length-1]?.content,messages.length])
  async function send(text=question,run=runId,override?:AiRequest){
    setLocalError('');setNotice('')
    try{
      const body=override?{...override,request_id:crypto.randomUUID()}:makeAiRequest(text,context,options,run)
      if(await tutor.send(body)){setQuestion('');setRunId(undefined);follow.current=true}
    }catch(cause){setLocalError((cause as Error).message)}
  }
  async function preset(index:number){
    setLocalError('');setQuestion(prompts[index][1])
    if(index!==3){setRunId(undefined);return}
    try{
      const runs=await api<CodeRun[]>(`/problems/${tutor.problemId}/runs`)
      const latest=runs.find(run=>!['queued','running'].includes(run.status))
      if(!latest){setLocalError('请先运行代码，再分析报错。');return}
      setRunId(latest.id)
    }catch(cause){setLocalError((cause as Error).message)}
  }
  useEffect(()=>{
    if(!trigger||seen.current===trigger.id)return
    seen.current=trigger.id;setRunId(trigger.runId);setQuestion(prompts[3][1])
    // This trigger is created only by an explicit click beside a run result.
    void send(prompts[3][1],trigger.runId)
  },[trigger?.id])
  return <section className={'ai-tutor'+(settings?' is-configuring':'')} aria-label="AI 助教"><header className="ai-heading"><div><strong>随题助教</strong><span className="muted small">从一点提示开始，也可以直接追问</span></div><button aria-expanded={settings} onClick={()=>setSettings(!settings)}>{settings?'返回问答':'AI 设置'}</button></header>
    {settings&&<AiSettings/>}
    {config.error&&<p className="local-error" role="alert">{config.error.message}<button onClick={()=>void config.refetch()}>重试</button></p>}
    <div className="ai-messages" ref={scroller} onScroll={()=>{const el=scroller.current!;follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<80}}>
      {!messages.length&&<div className="ai-empty"><h3>卡在哪一步？</h3><p>可以直接问“这道题怎么想到滑动窗口？”<br/>题面和当前代码会随问题一起发送。</p></div>}
      {messages.map((message,index)=><article className={'ai-message ai-'+message.role} key={message.id}><div className="ai-message-label">{message.role==='user'?'我':'AI 助教'}{message.status==='generating'&&<span role="status">{message.content?' · 回答中…':' · 正在思考…'}</span>}</div>{message.role==='assistant'?<AiMarkdown content={message.content}/>:<p className="ai-user-text">{message.content}</p>}
        {message.role==='user'&&<small className="muted">附带：{(message.attachments??[]).map(value=>({statement:'题面',code:'当前代码',language:'语言',notes:'笔记',run:'本次运行',recent_runs:'最近运行'}[value]??value)).join(' · ')||'仅问题'}</small>}
        {message.error&&<p className="local-error" role="alert">{message.error}</p>}
        {['stopped','interrupted'].includes(message.status)&&<p className="muted small">{message.status==='stopped'?'已停止回答':'回答已中断'}</p>}
        {message.role==='assistant'&&message.status!=='generating'&&<div className="ai-message-actions">{message.content&&<button onClick={()=>{onAppend(message.content);setNotice('已追加到笔记');onAppended()}}>追加到笔记</button>}{['failed','interrupted','stopped'].includes(message.status)&&messages[index-1]?.retry&&<button disabled={busy} onClick={()=>void send('',undefined,messages[index-1].retry)}>重试提问</button>}</div>}
      </article>)}<div ref={bottom}/>
    </div>
    <div className="ai-composer"><div className="ai-shortcuts">{prompts.map(([label],index)=><button disabled={busy} key={label} onClick={()=>void preset(index)}>{label}</button>)}</div>
      {!!messages.length&&!busy&&<div className="ai-followups"><button onClick={()=>setQuestion('请继续给我下一步提示。')}>继续提示</button><button onClick={()=>setQuestion('请展开完整解法，给出 Python ACM 代码、复杂度和边界情况。')}>展开完整解法</button></div>}
      <details className="ai-context"><summary>附带：{[options.statement&&'题面',options.code&&'当前代码',options.notes&&'笔记',options.history&&'最近运行',runId&&'指定运行'].filter(Boolean).join(' · ')||'仅问题'} · 调整</summary><div>{(['statement','code','notes','history'] as const).map(key=><label key={key}><input type="checkbox" checked={options[key]} onChange={e=>setOptions({...options,[key]:e.target.checked})}/>{{statement:'题面与样例',code:'当前代码草稿',notes:'我的笔记',history:'最近 3 次运行状态'}[key]}</label>)}</div></details>
      {runId&&<p className="small muted">已选本次运行的原始代码、输入和结果 <button onClick={()=>setRunId(undefined)}>取消附带</button></p>}
      <textarea aria-label="向 AI 提问" placeholder="直接描述你卡住的地方… Enter 发送，Shift+Enter 换行" maxLength={4000} value={question} readOnly={tutor.sending} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(!busy&&question.trim())void send()}}}/>
      <div className="ai-send-row"><span className="muted small">所选内容将发送给 DeepSeek</span>{busy?<button onClick={()=>void tutor.stop()}>停止回答</button>:<button className="primary" disabled={!question.trim()||!tutor.chat} onClick={()=>void send()}>发送</button>}</div>
      {(localError||tutor.error)&&<p className="local-error" role="alert">{localError||tutor.error}<button onClick={()=>void tutor.reload()}>重新读取对话</button></p>}{notice&&<p role="status">{notice}</p>}
    </div>
  </section>
}
