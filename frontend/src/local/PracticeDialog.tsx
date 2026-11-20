import {lazy,Suspense,useCallback,useEffect,useId,useMemo,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import DOMPurify from 'dompurify'
import {Download,ExternalLink,Maximize2,Minimize2,PanelLeftClose,PanelLeftOpen,X} from 'lucide-react'
import {api,downloadText,type Detail} from './api'
import {problemDestination} from './links'
import {useNote} from './useNote'
import {useCodeDraft} from './useCodeDraft'
import {flushPractice} from './practiceSession'
import {PracticeBody} from './PracticeBody'
import {EditorBoundary} from './EditorBoundary'
import {AiTutor} from './AiTutor'
import {useAiTutor} from './useAiTutor'
import './practice.css'

const AcmWorkspace=lazy(()=>import('./AcmWorkspace'))
const Preview=lazy(()=>import('../components/NoteEditorDialog').then(m=>({default:m.MarkdownPreview})))

export default function PracticeDialog({id,datasetId,onClose}:{id:string;datasetId:string;onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null),guard=useRef<(()=>Promise<boolean>)|null>(null),closingRef=useRef(false)
  const [closing,setClosing]=useState(false),[maximized,setMaximized]=useState(true)
  const [closeError,setCloseError]=useState('')
  const qc=useQueryClient()
  const detail=useQuery({queryKey:['practice-detail',id,datasetId],queryFn:()=>api<Detail>(`/problems/${id}?dataset_id=${encodeURIComponent(datasetId)}`),staleTime:0,gcTime:0})
  const registerGuard=useCallback((value:(()=>Promise<boolean>)|null)=>{guard.current=value},[])
  useEffect(()=>{
    const element=dialog.current!,overflow=document.body.style.overflow
    element.showModal();document.body.style.overflow='hidden'
    return()=>{element.close();document.body.style.overflow=overflow}
  },[])
  async function close(){
    if(closingRef.current)return
    closingRef.current=true;setClosing(true);setCloseError('')
    try{
      if(guard.current&&!await guard.current()){
        setCloseError('尚有草稿保存失败，练习面板已保留。请查看代码区的测试保存提示或底部的代码与笔记提示，再重试关闭。')
        return
      }
      void qc.invalidateQueries({queryKey:['problems']})
      // The notes drawer also writes code and language; discard its old detail.
      void qc.invalidateQueries({queryKey:['note-detail',id]})
      onClose()
    }finally{closingRef.current=false;setClosing(false)}
  }
  return <dialog ref={dialog} className={`practice-dialog${maximized?' is-maximized':''}`} aria-label="本地题目练习" onCancel={event=>{event.preventDefault();void close()}}>
    <header className="practice-header"><div><span className="muted small">本地练习 · 多语言 ACM</span><h2>{detail.data?`${detail.data.display_id} · ${detail.data.title}`:'正在读取题目…'}</h2></div><div className="practice-window-actions"><button className="icon-btn" aria-label={maximized?'还原练习面板':'最大化练习面板'} title={maximized?'还原':'最大化'} onClick={()=>setMaximized(!maximized)}>{maximized?<Minimize2 size={17}/>:<Maximize2 size={17}/>}</button><button autoFocus className="icon-btn" disabled={closing} aria-label="关闭本地练习" onClick={()=>void close()}><X size={20}/></button></div></header>
    {closeError&&<div className="practice-close-error local-error" role="alert">{closeError}<button disabled={closing} onClick={()=>void close()}>重试保存并关闭</button></div>}
    <PracticeBody saving={closing}>{detail.isFetchedAfterMount&&detail.data?<PracticeContent key={id} detail={detail.data} registerGuard={registerGuard}/>:detail.error?<div className="practice-loading local-error" role="alert">题目读取失败：{detail.error.message}<button onClick={()=>void detail.refetch()}>重试读取</button></div>:<p className="practice-loading muted" role="status">正在读取本地题目…</p>}</PracticeBody>
  </dialog>
}

function PracticeContent({detail,registerGuard}:{detail:Detail;registerGuard:(guard:(()=>Promise<boolean>)|null)=>void}){
  const note=useNote(detail.id,detail.note)
  const suiteGuard=useRef<(()=>Promise<boolean>)|null>(null),previewRef=useRef<HTMLDivElement>(null)
  const stopCode=useCallback(async()=>suiteGuard.current?await suiteGuard.current():true,[])
  const code=useCodeDraft(detail.id,detail.note,stopCode)
  const [view,setView]=useState<'statement'|'code'|'notes'|'ai'>('statement'),[preview,setPreview]=useState(false)
  const [readingCollapsed,setReadingCollapsed]=useState(false)
  const readingId=useId()
  const [aiOpened,setAiOpened]=useState(false),[aiTrigger,setAiTrigger]=useState<{id:string;runId:string}|null>(null)
  const tutor=useAiTutor(detail.id,aiOpened)
  const destination=problemDestination(detail.url)
  const statement=useMemo(()=>DOMPurify.sanitize(detail.content_html??'',{USE_PROFILES:{html:true},FORBID_TAGS:['style','form','input','button','iframe','video','audio'],FORBID_ATTR:['style']}),[detail.content_html])
  const registerSuite=useCallback((guard:(()=>Promise<boolean>)|null)=>{suiteGuard.current=guard},[])
  const flush=useCallback(async()=>{if(!await tutor.stop())return false;return flushPractice(async()=>{if(!await code.flush())return false;return note.flush()},suiteGuard.current)},[note.flush,code.flush,tutor.stop])
  useEffect(()=>{registerGuard(flush);return()=>registerGuard(null)},[flush,registerGuard])
  function changeView(next:typeof view){setView(next);setReadingCollapsed(false)}
  function exportDraft(){downloadText(`练习草稿-${detail.display_id}.md`,note.draft.body_md+`\n\n\`\`\`${code.draft.language}\n${code.draft.code_text}\n\`\`\`\n`)}
  return <>
    <nav className="practice-toolbar" aria-label="练习视图"><div className="practice-tabs" role="group" aria-label="练习内容"><button aria-pressed={view==='statement'} onClick={()=>changeView('statement')}>题目</button><button className="practice-code-tab" aria-pressed={view==='code'} onClick={()=>changeView('code')}>代码与测试</button><button aria-pressed={view==='notes'} onClick={()=>changeView('notes')}>笔记</button><button aria-pressed={view==='ai'} onClick={()=>{setAiOpened(true);changeView('ai')}}>AI 助教</button></div><div className="practice-toolbar-actions"><button className="practice-collapse-toggle" aria-expanded={!readingCollapsed} aria-controls={readingId} onClick={()=>setReadingCollapsed(value=>!value)}>{readingCollapsed?<PanelLeftOpen size={15}/>:<PanelLeftClose size={15}/>} {readingCollapsed?'展开左栏':'收起左栏'}</button>{destination&&<a className="button-link" href={destination.href} target="_blank" rel="noreferrer">打开原题<ExternalLink size={13}/></a>}</div></nav>
    <div className="practice-columns" data-view={view} data-reading-collapsed={readingCollapsed}>
      <section id={readingId} className="practice-reading" aria-label="题目与笔记">
        <div hidden={view==='notes'||view==='ai'}><div className="practice-statement-meta"><span className={'difficulty d'+detail.difficulty}>{['','简单','中等','困难'][detail.difficulty]}</span><span className="muted">原题题面与示例</span></div>{statement?<article className="problem-content" aria-label="本地题面" dangerouslySetInnerHTML={{__html:statement}}/>:<div className="empty"><h3>本题暂缺本地题面</h3><p>可以打开原题查看，或在右侧编写代码继续练习。</p>{destination&&<a className="button-link" href={destination.href} target="_blank" rel="noreferrer">查看原题<ExternalLink size={13}/></a>}</div>}<p className="practice-statement-hint muted">请使用当前语言的完整程序入口读取输入并输出答案。点击运行后可在终端输入；也可展开“预设输入”；要保存和批量运行自定义样例，请展开“高级测试”。</p></div>
        <section hidden={view!=='notes'} aria-label="练习笔记"><div className="note-editor-toolbar"><strong>我的笔记</strong><div className="note-editor-tabs"><button aria-pressed={!preview} onClick={()=>setPreview(false)}>编写</button><button aria-pressed={preview} onClick={()=>setPreview(true)}>预览</button></div></div><EditorBoundary key={preview?'preview':'write'} onClose={()=>setPreview(false)} fallback={<div className="local-error" role="alert">笔记预览暂时无法载入，草稿仍保留。<button onClick={()=>setPreview(false)}>返回编写</button></div>}>{preview?<div className="simple-note-preview"><Suspense fallback={<p>正在载入预览…</p>}><Preview content={note.draft.body_md} previewRef={previewRef}/></Suspense></div>:<textarea className="practice-note-input" aria-label="练习 Markdown 笔记" placeholder="记录思路、易错点，支持 Markdown。" value={note.draft.body_md} onChange={event=>note.setDraft({body_md:event.target.value})}/>}</EditorBoundary></section>
        {aiOpened&&<div className="ai-slot" hidden={view!=='ai'}><AiTutor context={{code:code.draft.code_text,language:code.draft.language,notes:note.draft.body_md,datasetId:detail.dataset_id}} tutor={tutor} trigger={aiTrigger} onAppend={text=>note.setDraft({body_md:note.draft.body_md+'\n\n### AI 助教记录\n\n'+text})} onAppended={()=>{}}/></div>}
      </section>
      <section className="practice-coding" aria-label="代码与测试"><EditorBoundary onClose={()=>changeView('statement')} fallback={<div className="local-error" role="alert">代码编辑器暂时无法载入，当前代码和笔记草稿仍保留。可先导出草稿，恢复连接后重新打开练习。</div>}><Suspense fallback={<p className="muted" role="status">正在载入代码编辑器…</p>}><AcmWorkspace problemId={detail.id} code={code.draft.code_text} language={code.draft.language} onCodeChange={code.setCode} onLanguageChange={language=>{void code.switchLanguage(language)}} onRewrite={code.rewriteCode} changingCode={code.changing} registerGuard={registerSuite} beforeRun={async()=>{const saved=await Promise.all([note.flush(),code.flush()]);return saved.every(Boolean)}} onAnalyze={runId=>{setAiOpened(true);changeView('ai');setAiTrigger({id:crypto.randomUUID(),runId})}}/></Suspense></EditorBoundary></section>
    </div>
    <footer className="practice-footer"><span className={note.error||code.error?'error-text':'muted'} role="status">代码：{code.status} · 笔记：{note.status}</span><button onClick={exportDraft}><Download size={13}/>导出草稿</button>{(note.error||code.error)&&<div className="practice-save-error local-error" role="alert">操作未完成，草稿仍保留：{code.error||note.error}<div className="button-row"><button onClick={()=>{void note.flush();void code.flush()}}>重试保存</button><button onClick={()=>{exportDraft();void note.reloadServer();void code.reloadServer()}}>导出并载入服务器版本</button></div></div>}</footer>
  </>
}
