import {lazy,Suspense,useCallback,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import DOMPurify from 'dompurify'
import {ExternalLink,Star,X,BookOpen,Download,Check,Pause,Play} from 'lucide-react'
import {api,type Detail,type StudyState,dateLabel,downloadText,safeLink} from './api'
import {useNote} from './useNote'
import {useCodeDraft} from './useCodeDraft'
import {EditorBoundary} from './EditorBoundary'

const NoteEditor = lazy(()=>import('../components/NoteEditorDialog').then(m=>({default:m.NoteEditorDialog})))
const AcmWorkspace = lazy(()=>import('./AcmWorkspace'))
const outcomes:Record<string,string>={independent:'独立完成',hint:'使用提示',solution:'查看答案',unfinished:'未完成'}
const masteryNames=['未评估','生疏','基本掌握','熟练']

export function ProblemDialog({id,datasetId,onClose}:{id:string;datasetId?:string;onClose:()=>void}){
  const detail=useQuery({queryKey:['detail',id,datasetId],queryFn:()=>api<Detail>(`/problems/${id}${datasetId?'?dataset_id='+datasetId:''}`),staleTime:0})
  return <div className="local-modal-shade"><section className="local-detail" role="dialog" aria-modal="true" aria-label="题目详情">{detail.data?<><DetailContent key={id} detail={detail.data} onClose={onClose}/>{detail.error&&<p className="local-error" role="alert">后台刷新失败：{detail.error.message}。当前编辑内容仍保留。</p>}</>:detail.isLoading?<p>正在读取题目…</p>:detail.error?<><p role="alert">{detail.error.message}</p><button onClick={onClose}>关闭</button></>:null}</section></div>
}

function DetailContent({detail,onClose}:{detail:Detail;onClose:()=>void}){
  const qc=useQueryClient(),note=useNote(detail.id,detail.note)
  const [state,setState]=useState(detail.state),[editor,setEditor]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [outcome,setOutcome]=useState('independent'),[duration,setDuration]=useState('')
  const pending=useRef<{request_id:string;outcome:string;duration_seconds:number|null}|null>(null)
  const [attempts,setAttempts]=useState(detail.attempts)
  const acmAnchor=useRef<HTMLDivElement>(null),acmGuard=useRef<(()=>Promise<boolean>)|null>(null)
  const registerAcmGuard=useCallback((guard:(()=>Promise<boolean>)|null)=>{acmGuard.current=guard},[])
  const stopCode=useCallback(async()=>acmGuard.current?await acmGuard.current():true,[])
  const code=useCodeDraft(detail.id,detail.note,stopCode)
  const link=safeLink(detail.url)
  const invalidate=()=>{for(const key of ['problems','due','activity','detail'])void qc.invalidateQueries({queryKey:[key]})}
  async function changeState(patch:Partial<StudyState>){
    setBusy(true);setError('')
    try{const result=await api<StudyState>(`/problems/${detail.id}/state`,{method:'PATCH',body:JSON.stringify({revision:state.revision,...patch})});setState(result);invalidate()}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  async function attempt(){
    const seconds=duration===''?null:Number(duration)*60
    if(seconds!==null&&(!Number.isInteger(seconds)||seconds<0||seconds>86400)){setError('用时应在 0–1440 分钟之间');return}
    pending.current??={request_id:crypto.randomUUID(),outcome,duration_seconds:seconds}
    setBusy(true);setError('')
    try{
      const result=await api<{state:StudyState;attempt:Detail['attempts'][number]}>(`/problems/${detail.id}/attempts`,{method:'POST',body:JSON.stringify(pending.current)})
      setState(result.state);setAttempts(current=>current.some(a=>a.id===result.attempt.id)?current:[result.attempt,...current]);pending.current=null;invalidate()
    }catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  async function close(){
    if(acmGuard.current&&!await acmGuard.current())return
    if(await code.flush()&&await note.flush()){invalidate();onClose()}
  }
  async function recover(){
    downloadText(`未保存草稿-${detail.display_id}.md`,note.draft.body_md+'\n\n```'+code.draft.language+'\n'+code.draft.code_text+'\n```')
    await note.reloadServer();await code.reloadServer()
  }
  const upstreamQuestion={id:0,displayId:detail.display_id,title:detail.title,level:detail.difficulty,date:'',frequency:0,rate:0 as const,done:false,slug:detail.url??'',expandedLink:true}
  return <>
    <header className="detail-head"><div><span className="eyebrow">PROBLEM / {detail.display_id}</span><h2>{detail.title}</h2><div className="detail-meta"><span className={'difficulty d'+detail.difficulty}>{['','简单','中等','困难'][detail.difficulty]}</span><span>{detail.source_name} · 数据生成 {dateLabel(detail.generated_at)} · 导入 {dateLabel(detail.imported_at)}</span></div></div><button className="icon-btn" aria-label="关闭详情" onClick={()=>void close()}><X size={20}/></button></header>
    <div className="detail-tools"><button className="primary" onClick={()=>acmAnchor.current?.scrollIntoView({behavior:'smooth',block:'start'})}>ACM 编程 / 运行</button><button disabled={busy} onClick={()=>void changeState({favorite:!state.favorite})}><Star size={16} fill={state.favorite?'currentColor':'none'}/>{state.favorite?'已收藏':'收藏题目'}</button><button onClick={()=>setEditor(true)}><BookOpen size={16}/>编辑笔记</button>{link?<a className="button-link" href={link} target="_blank" rel="noreferrer">打开原题 <ExternalLink size={14}/></a>:<span className="muted">来源未提供原题地址</span>}</div>
    <div className="detail-grid"><article className="problem-content">{detail.content_html?<div dangerouslySetInnerHTML={{__html:DOMPurify.sanitize(detail.content_html,{USE_PROFILES:{html:true},FORBID_TAGS:['style','form','input','button','iframe','video','audio'],FORBID_ATTR:['style']})}}/>:<div className="empty">来源暂缺题面。仍可保存笔记、记录练习或打开原题。</div>}</article><aside className="study-panel">
      <h3>本次练习</h3><label>练习结果<select aria-label="练习结果" value={outcome} disabled={busy||!!pending.current} onChange={e=>setOutcome(e.target.value)}>{Object.entries(outcomes).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>用时（分钟，可留空）<input type="number" min="0" max="1440" value={duration} disabled={busy||!!pending.current} onChange={e=>setDuration(e.target.value)}/></label><button className="primary wide" disabled={busy} onClick={()=>void attempt()}><Check size={16}/>{pending.current?'重试保存本次练习':'记录练习'}</button>
      <div className="review-state"><span>下次复习</span><strong>{state.next_review_date??'记录练习后安排'}</strong><small>{state.review_enabled?'复习已启用':'复习已暂停'} · {state.review_step<0?'起始阶段':`第 ${state.review_step+1} 级`}</small><button disabled={busy} onClick={()=>void changeState({review_enabled:!state.review_enabled})}>{state.review_enabled?<Pause size={14}/>:<Play size={14}/>} {state.review_enabled?'暂停复习':'启用复习'}</button></div>
      <label>掌握程度<select aria-label="掌握程度" value={state.mastery} disabled={busy} onChange={e=>void changeState({mastery:Number(e.target.value)})}>{masteryNames.map((v,k)=><option key={k} value={k}>{v}</option>)}</select></label>
      <p className="muted small">独立完成按 1、3、7、14、30 天推进；同日不重复升级。使用提示、查看答案或未完成安排次日复习。</p>
      <h3>练习历史 <small>{attempts.length}</small></h3><div className="attempt-list">{attempts.length===0?<p className="muted">还没有练习记录</p>:attempts.map(a=><div key={a.id}><span>{outcomes[a.outcome]??a.outcome}</span><small>{new Date(a.practiced_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}{a.duration_seconds!==null?` · ${a.duration_seconds/60} 分钟`:''}</small></div>)}</div>
    </aside></div>
    {error&&<div className="local-error" role="alert">{error}</div>}
    <footer className="note-save-bar"><span className={note.error?'error-text':'muted'} role="status">代码：{code.status} · 笔记：{note.status}{note.error?' · '+note.error:''}</span>{note.error&&<button onClick={()=>void note.flush()}>重新保存</button>}<button onClick={()=>downloadText(`笔记-${detail.display_id}.md`,note.draft.body_md+'\n\n```'+code.draft.language+'\n'+code.draft.code_text+'\n```')}><Download size={14}/>导出草稿</button></footer>
    {(note.error||code.error)&&<div className="button-row"><span role="alert">{code.error}</span><button onClick={()=>void recover()}>导出当前草稿并载入服务器版本</button><span className="muted small">{note.conflict?'检测到版本冲突，服务器内容不会被自动覆盖。':'连接恢复后可以重试保存，或导出草稿后重新载入。'}</span></div>}
    <div ref={acmAnchor}><EditorBoundary onClose={()=>acmAnchor.current?.scrollIntoView()}><Suspense fallback={<p>正在载入 ACM 编辑器…</p>}><AcmWorkspace problemId={detail.id} code={code.draft.code_text} language={code.draft.language} onCodeChange={code.setCode} onLanguageChange={language=>{void code.switchLanguage(language)}} onRewrite={code.rewriteCode} changingCode={code.changing} registerGuard={registerAcmGuard} beforeRun={code.flush}/></Suspense></EditorBoundary></div>
    {editor&&<div className="upstream-editor-wrap"><div className="editor-save-indicator" role="status">{note.status}{note.error?' · '+note.error:''}</div><EditorBoundary onClose={()=>setEditor(false)}><Suspense fallback={<p>载入编辑器…</p>}><NoteEditor question={upstreamQuestion} value={note.draft.body_md} note={{content:note.draft.body_md,updatedAt:note.draft.updated_at}} onChange={body_md=>note.setDraft({body_md})} onClose={()=>setEditor(false)} onExport={()=>downloadText(`笔记-${detail.display_id}.md`,note.draft.body_md)}/></Suspense></EditorBoundary></div>}
  </>
}
