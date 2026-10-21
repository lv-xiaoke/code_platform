import {Suspense,lazy,useCallback,useEffect,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import CodeMirror from '@uiw/react-codemirror'
import {markdown} from '@codemirror/lang-markdown'
import {EditorView} from '@codemirror/view'
import {githubDark,githubLight} from '@uiw/codemirror-theme-github'
import {Download,ExternalLink,X} from 'lucide-react'
import {api,downloadText,type Detail} from './api'
import type {AcmData} from './acmTypes'
import {problemDestination} from './links'
import {useNote} from './useNote'
import {ReferencePanel} from './ReferencePanel'
import {EditorBoundary} from './EditorBoundary'
import './acm.css'

const Preview=lazy(()=>import('../components/NoteEditorDialog').then(m=>({default:m.MarkdownPreview})))
const noteExtensions=[markdown(),EditorView.lineWrapping,EditorView.contentAttributes.of({'aria-label':'Markdown 笔记'})]

export default function NotesDrawer({id,datasetId,onClose}:{id:string;datasetId?:string;onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null),guard=useRef<(()=>Promise<boolean>)|null>(null)
  const [closing,setClosing]=useState(false)
  const qc=useQueryClient()
  // The editor always starts from a fresh read; stale cached revisions must
  // never become the initial revision when opening the drawer again.
  const detail=useQuery({queryKey:['note-detail',id,datasetId],queryFn:()=>api<Detail>(`/problems/${id}${datasetId?'?dataset_id='+datasetId:''}`),staleTime:0,gcTime:0})
  const registerGuard=useCallback((value:(()=>Promise<boolean>)|null)=>{guard.current=value},[])
  useEffect(()=>{const element=dialog.current!;element.showModal();return()=>element.close()},[])
  async function close(){
    if(closing)return
    setClosing(true)
    try{
      if(guard.current&&!await guard.current())return
      void qc.invalidateQueries({queryKey:['problems']})
      onClose()
    }finally{setClosing(false)}
  }
  return <dialog ref={dialog} className="notes-drawer" aria-label="笔记与参考代码" onCancel={event=>{event.preventDefault();void close()}}>
    <header className="notes-drawer-header"><div><span className="muted small">笔记与参考代码</span><h2>{detail.data?`${detail.data.display_id} · ${detail.data.title}`:'正在读取…'}</h2></div><button autoFocus className="icon-btn" disabled={closing} aria-label="关闭笔记" onClick={()=>void close()}><X size={20}/></button></header>
    <div className="notes-drawer-body">{detail.isFetchedAfterMount&&detail.data?<NoteContent key={id} detail={detail.data} registerGuard={registerGuard}/>:detail.error?<div className="local-error" role="alert">{detail.error.message}<button onClick={()=>void detail.refetch()}>重试读取</button></div>:<p className="muted">正在载入笔记…</p>}</div>
  </dialog>
}

function NoteContent({detail,registerGuard}:{detail:Detail;registerGuard:(guard:(()=>Promise<boolean>)|null)=>void}){
  const note=useNote(detail.id,detail.note),[preview,setPreview]=useState(false),previewRef=useRef<HTMLDivElement>(null)
  const reference=useQuery({queryKey:['reference',detail.id],queryFn:()=>api<AcmData>(`/problems/${detail.id}/acm`),select:data=>data.reference})
  const destination=problemDestination(detail.url)
  useEffect(()=>{registerGuard(note.flush);return()=>registerGuard(null)},[registerGuard,note.flush])
  const exportDraft=()=>downloadText(`笔记-${detail.display_id}.md`,note.draft.body_md+(note.draft.code_text?`\n\n\`\`\`${note.draft.language}\n${note.draft.code_text}\n\`\`\`\n`:''))
  async function recover(){exportDraft();await note.reloadServer()}
  return <>
    <div className="notes-actions">{destination&&<a className="button-link" href={destination.href} target="_blank" rel="noreferrer">去 {destination.platform} 做题<ExternalLink size={13}/></a>}<button className="note-export" onClick={exportDraft}><Download size={14}/>导出笔记</button></div>
    <div className="note-editor-toolbar"><div className="note-editor-tabs" role="group" aria-label="笔记模式"><button aria-pressed={!preview} onClick={()=>setPreview(false)}>编写</button><button aria-pressed={preview} onClick={()=>setPreview(true)}>预览</button></div><span className={note.error?'error-text':'muted'} role="status">{note.status}</span></div>
    <EditorBoundary key={preview?'preview':'write'} onClose={()=>setPreview(!preview)} fallback={<div className="local-error" role="alert">{preview?'预览':'编辑器'}暂时无法载入，草稿仍保留。可以导出笔记，或切换编辑模式继续。<button onClick={()=>setPreview(!preview)}>{preview?'切回编写':'查看预览'}</button></div>}>
      {preview?<section className="simple-note-preview" aria-label="笔记预览">{note.draft.body_md?<Suspense fallback={<p className="muted">正在载入预览…</p>}><Preview content={note.draft.body_md} previewRef={previewRef}/></Suspense>:<p className="muted">还没有笔记，切换到“编写”记录思路。</p>}</section>:<CodeMirror value={note.draft.body_md} onChange={body_md=>note.setDraft({body_md})} extensions={noteExtensions} height="360px" placeholder="记录思路、易错点，或粘贴解法。支持 Markdown。" theme={document.documentElement.dataset.theme==='dark'?githubDark:githubLight} basicSetup={{lineNumbers:false,foldGutter:false,highlightActiveLine:false}}/>}
    </EditorBoundary>
    {note.error&&<div className="local-error" role="alert">保存失败，当前草稿仍保留：{note.error}<div className="button-row"><button onClick={()=>void note.flush()}>重试保存</button><button onClick={()=>void recover()}>导出草稿并载入服务器版本</button></div></div>}
    <p className="note-autosave-hint muted">停止输入后自动保存，关闭面板前会保存当前编辑。</p>
    <section className="reference-section" aria-label="参考实现"><EditorBoundary onClose={()=>setPreview(false)} fallback={<p className="local-error" role="alert">参考代码暂时无法显示，可以继续编辑笔记。</p>}>{reference.error?<div className="local-error" role="alert">参考代码读取失败：{reference.error.message}<button onClick={()=>void reference.refetch()}>重试</button></div>:reference.isPending?<p className="muted small">正在读取参考代码…</p>:<ReferencePanel reference={reference.data??null}/>}</EditorBoundary></section>
  </>
}
