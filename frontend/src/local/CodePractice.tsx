import {useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {Copy,History,RotateCcw} from 'lucide-react'
import {api,type CodeVersion} from './api'
import CodeEditor from './CodeEditor'

type Props={problemId:string;code:string;language:string;view:'current'|'history';onViewChange:(view:'current'|'history')=>void;onCodeChange:(value:string)=>void;onLanguageChange:(value:string)=>void;onRewrite:(historyId?:number,language?:string)=>Promise<boolean>;changing:boolean;disabled?:boolean}

export default function CodePractice(props:Props){
  const qc=useQueryClient()
  const [selected,setSelected]=useState<number|null>(null),[message,setMessage]=useState('')
  const [onlyCurrent,setOnlyCurrent]=useState(false)
  const languages=useQuery({queryKey:['code-languages',props.problemId],queryFn:()=>api<string[]>(`/problems/${props.problemId}/code/languages`),staleTime:0})
  const versions=useQuery({queryKey:['code-history',props.problemId],queryFn:()=>api<CodeVersion[]>(`/problems/${props.problemId}/code/history`),enabled:props.view==='history',staleTime:0})
  const filtered=versions.data?.filter(version=>!onlyCurrent||version.language===props.language)
  const current=filtered?.find(v=>v.id===selected)??filtered?.[0]
  const disabled=props.changing||props.disabled
  async function replace(historyId?:number,language?:string){
    setMessage('')
    if(await props.onRewrite(historyId,language)){
      void qc.invalidateQueries({queryKey:['code-history',props.problemId]})
      props.onViewChange('current')
      setMessage(historyId?'历史代码已载入，原草稿已保留。':props.code.trim()?'原代码已存入历史，可以开始重新编写。':'已开始空白练习。')
    }else setMessage('操作未完成，当前草稿仍保留。请查看代码与笔记的保存提示。')
  }
  async function copy(){
    try{await navigator.clipboard.writeText(current!.code_text);setMessage('代码已复制。')}
    catch{setMessage('复制失败，可在代码区选择文本后手动复制。')}
  }
  return <div className="code-practice">
    <div className="acm-editor-heading code-practice-toolbar">
      <div className="code-view-tabs" role="group" aria-label="代码视图">
        <button aria-pressed={props.view==='current'} onClick={()=>{props.onViewChange('current');setMessage('')}}>当前练习</button>
        <button aria-pressed={props.view==='history'} onClick={()=>{props.onViewChange('history');setMessage('')}}><History size={13}/>历史代码</button>
      </div>
      <div><button disabled={disabled} title="将当前非空代码保存到历史，再开始空白练习" onClick={()=>void replace()}><RotateCcw size={13}/>{props.changing?'正在保存…':'重新编写'}</button>
        {props.view==='current'&&<select disabled={props.changing} aria-label="代码语言" value={props.language} onChange={e=>props.onLanguageChange(e.target.value)}>{Array.from(new Set(['python','c','cpp','java','javascript','typescript','go','rust','sql','text',...(languages.data??[]),props.language])).map(v=><option key={v} value={v}>{v||'（旧草稿未标注语言）'}</option>)}</select>}
      </div>
    </div>
    {message&&<p className="code-history-message muted small" role="status">{message}</p>}
    {props.view==='current'?<><CodeEditor language={props.language} value={props.code} onChange={props.onCodeChange} readOnly={props.changing} ariaLabel={`${props.language} 代码`}/>{!['python','c','cpp','java','javascript'].includes(props.language)&&<p className="muted small">可编辑，暂不支持运行。</p>}</>:<section className="code-history-panel" aria-label="历史代码"><label className="code-history-filter"><input type="checkbox" checked={onlyCurrent} onChange={event=>setOnlyCurrent(event.target.checked)}/>仅显示当前语言</label>
      {versions.error?<p className="local-error" role="alert">历史代码读取失败：{versions.error.message}<button onClick={()=>void versions.refetch()}>重试读取</button></p>:!versions.data?<p className="muted" role="status">正在读取历史代码…</p>:current?<>
        <div className="code-history-actions"><label>历史版本<select aria-label="历史代码版本" value={current.id} onChange={e=>{setSelected(Number(e.target.value));setMessage('')}}>{filtered!.map((v,i)=><option key={v.id} value={v.id}>第 {filtered!.length-i} 次 · {new Date(v.created_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})} · {v.language}</option>)}</select></label><div><button onClick={()=>void copy()}><Copy size={13}/>复制代码</button><button disabled={disabled} onClick={()=>void replace(current.id,current.language)}>载入到当前练习</button></div></div>
        <p className="muted small">只读历史 · 载入前会将当前非空草稿保存到历史。</p>
        <CodeEditor language={current.language} value={current.code_text} ariaLabel={`历史 ${current.language} 代码`} readOnly/>
      </>:<div className="code-history-empty muted"><p>还没有历史代码。</p><p>点击“重新编写”后，当前非空代码会保留在这里。</p></div>}
    </section>}
  </div>
}
