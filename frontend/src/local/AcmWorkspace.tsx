import {useEffect,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {Play,Plus,Save,RefreshCw,Terminal} from 'lucide-react'
import {api,downloadText} from './api'
import type {AcmCase,AcmData,AcmSuite,CodeRun,RunnerHealth} from './acmTypes'
import {useAcmSuite,EMPTY_CASE} from './useAcmSuite'
import {prepareRun} from './runRequest'
import PythonEditor from './PythonEditor'
import {ReferencePanel} from './ReferencePanel'
import {RunResults,runLabel} from './RunResults'
import './acm.css'

type Props={problemId:string;code:string;language:string;onCodeChange:(code:string)=>void;onLanguageChange:(language:string)=>void;registerGuard:(guard:(()=>Promise<boolean>)|null)=>void}

export default function AcmWorkspace(props:Props){
  const acm=useQuery({queryKey:['acm',props.problemId],queryFn:()=>api<AcmData>(`/problems/${props.problemId}/acm`),staleTime:0})
  if(acm.data)return <AcmContent {...props} initial={acm.data}/>
  return <section className="acm-workspace">{acm.error?<p className="local-error" role="alert">{acm.error.message}<button onClick={()=>void acm.refetch()}>重新读取</button></p>:<p>正在载入 Python ACM 工作区…</p>}</section>
}

function AcmContent({initial,...props}:Props&{initial:AcmData}){
  const suite=useAcmSuite(props.problemId,initial),qc=useQueryClient()
  const [runId,setRunId]=useState<string|null>(null),[submitting,setSubmitting]=useState(false),[error,setError]=useState('')
  const pending=useRef<{signature:string;body:unknown}|null>(null)
  const health=useQuery({queryKey:['runner-health'],queryFn:()=>api<RunnerHealth>('/runner/health'),staleTime:10000})
  const active=useQuery({queryKey:['run',runId],queryFn:()=>api<CodeRun>('/runs/'+runId),enabled:!!runId,refetchInterval:q=>['queued','running'].includes(q.state.data?.status??'queued')?500:false,staleTime:0})
  const history=useQuery({queryKey:['runs',props.problemId],queryFn:()=>api<CodeRun[]>(`/problems/${props.problemId}/runs`),staleTime:0})
  const busy=submitting||['queued','running'].includes(active.data?.status??'')
  const draft=suite.value.draft??{...EMPTY_CASE}
  useEffect(()=>{props.registerGuard(suite.flush);return()=>props.registerGuard(null)},[props.registerGuard,suite.flush])
  useEffect(()=>{if(active.data&&!['queued','running'].includes(active.data.status))void qc.invalidateQueries({queryKey:['runs',props.problemId]})},[active.data?.status,props.problemId,qc])
  const updateDraft=(patch:Partial<AcmCase>)=>suite.update({draft:{...draft,...patch}})
  async function submit(source:string,mode:'custom'|'suite'){
    setError('')
    if(!source.trim()){setError('请先编写完整 Python 程序，或使用参考实现运行。');return}
    setSubmitting(true)
    try{
      if(!await suite.flush())return
      const {submission,signature}=prepareRun(source,mode,suite.snapshot())
      if(pending.current?.signature!==signature)pending.current={signature,body:{...submission,request_id:crypto.randomUUID()}}
      const result=await api<CodeRun>(`/problems/${props.problemId}/runs`,{method:'POST',body:JSON.stringify(pending.current.body)})
      pending.current=null;setRunId(result.id);qc.setQueryData(['run',result.id],result)
      void qc.invalidateQueries({queryKey:['runs',props.problemId]})
    }catch(e){setError((e as Error).message)}finally{setSubmitting(false)}
  }
  function saveCase(){
    const id=draft.id&&!draft.id.startsWith('builtin:')?draft.id:crypto.randomUUID()
    const item={...draft,id}
    const cases=suite.value.cases.filter(c=>c.id!==id)
    if(cases.length>=16){setError('最多保存 16 组自定义测试。');return}
    suite.update({cases:[...cases,item],draft:item})
  }
  const runDisabled=busy||!health.data?.available
  return <section className="acm-workspace" aria-label="Python ACM 工作区"><header className="acm-title"><div><span className="eyebrow">WRITE · RUN · UNDERSTAND</span><h3><Terminal size={18}/>Python ACM 工作区</h3></div><span className={'runner-chip '+(health.data?.available?'ready':'')}>{health.isFetching?'检查运行环境…':health.data?.available?'Docker 已就绪':'Docker 未就绪'}</span></header>
    {(health.error||health.data?.error)&&<div className="local-error" role="alert">{health.error?.message??health.data?.error}<button onClick={()=>void health.refetch()}><RefreshCw size={13}/>重新检查</button></div>}
    <details className="acm-contract" open><summary>本题 ACM 输入输出约定</summary><p className="muted small">{initial.contract_notice}</p>{initial.reference?<div className="contract-grid"><div><h4>输入格式</h4><p>{initial.reference.input_description}</p></div><div><h4>输出格式</h4><p>{initial.reference.output_description}</p></div></div>:<p className="small">自行约定输入格式，使用 input() 或 sys.stdin 读取，并用 print() 输出。可以保存期望输出，或只运行观察结果。</p>}</details>
    <div className="acm-editor-heading"><strong>我的代码</strong><div><select aria-label="代码语言" value={props.language} onChange={e=>props.onLanguageChange(e.target.value)}>{['python','cpp','java','javascript','typescript','go','rust','sql','text'].map(v=><option key={v}>{v}</option>)}</select><button disabled={!!props.code.trim()||props.language!=='python'} title="仅在代码为空时载入，不替换已有代码" onClick={()=>props.onCodeChange(initial.template)}>载入输入模板</button></div></div>
    {props.language==='python'?<PythonEditor value={props.code} onChange={props.onCodeChange} label="Python ACM 代码"/>:<><textarea aria-label="我的代码" className="other-code" value={props.code} onChange={e=>props.onCodeChange(e.target.value)}/><p className="muted small">当前版本只执行 Python；其他语言的已有代码仍可编辑和保存。</p></>}
    <div className="acm-limits">Python 3.12 · 每组 2 秒 · 256 MiB · 输出上限 64 KiB · stdin → stdout</div>
    <div className="case-toolbar"><h4>自定义测试</h4><span role="status">测试输入：{suite.status}</span><button onClick={()=>suite.update({draft:{...EMPTY_CASE}})}><Plus size={13}/>新建输入</button></div>
    {initial.builtin_cases.length>0&&<div className="sample-buttons"><span>载入题目样例</span>{initial.builtin_cases.map((c,i)=><button key={c.id} onClick={()=>suite.update({draft:{...c,id:null}})}>样例 {i+1}</button>)}</div>}
    <div className="case-options"><label>用例名称<input aria-label="测试名称" value={draft.name} onChange={e=>updateDraft({name:e.target.value})}/></label><label>输出比较<select aria-label="输出比较" value={draft.comparison} onChange={e=>updateDraft({comparison:e.target.value as AcmCase['comparison']})}><option value="tokens">忽略空白差异</option><option value="exact">严格文本（统一换行）</option><option value="unordered_lines">忽略行顺序</option><option value="float">浮点容差 1e-6</option></select></label><label className="expected-toggle"><input type="checkbox" aria-label="校验期望输出" checked={draft.expected_stdout!==null} onChange={e=>updateDraft({expected_stdout:e.target.checked?'':null})}/>校验期望输出</label></div>
    <div className="case-input-grid"><label>标准输入 stdin<textarea aria-label="标准输入 stdin" value={draft.stdin} spellCheck={false} placeholder="在这里填写输入；不需要写 input = 或参数名。" onChange={e=>updateDraft({stdin:e.target.value})}/></label><label>期望输出 stdout<textarea aria-label="期望输出 stdout" disabled={draft.expected_stdout===null} value={draft.expected_stdout??''} spellCheck={false} placeholder={draft.expected_stdout===null?'未启用：只显示运行结果':'允许空输出；不会按空值跳过比较。'} onChange={e=>updateDraft({expected_stdout:e.target.value})}/></label></div>
    <div className="acm-run-actions"><button className="primary" disabled={runDisabled||props.language!=='python'} onClick={()=>void submit(props.code,'custom')}><Play size={15}/>{busy?'运行中…':'运行当前输入'}</button><button disabled={runDisabled||props.language!=='python'||initial.builtin_cases.length+suite.value.cases.length===0} onClick={()=>void submit(props.code,'suite')}>运行全部测试（{initial.builtin_cases.length+suite.value.cases.length}）</button><button onClick={saveCase}><Save size={14}/>保存为测试用例</button></div>
    {suite.error&&<div className="local-error" role="alert">测试保存失败，当前输入保留：{suite.error}<button onClick={()=>void suite.flush()}>重试保存</button><button onClick={()=>{downloadText(`ACM测试草稿-${props.problemId}.json`,JSON.stringify(suite.value,null,2));void suite.reloadServer()}}>导出测试草稿并载入服务器版本</button></div>}{error&&<div className="local-error" role="alert">{error}</div>}
    {suite.value.cases.length>0&&<div className="saved-tests"><h4>我的测试（自动保存）</h4>{suite.value.cases.map(c=><div key={c.id}><span>{c.name}</span><small>{c.expected_stdout===null?'仅运行':'校验输出'}</small><button onClick={()=>suite.update({draft:{...c}})}>载入</button><button onClick={()=>suite.update({cases:suite.value.cases.filter(v=>v.id!==c.id)})}>移出测试集</button></div>)}</div>}
    {runId&&<RunResults runId={runId}/>}
    <ReferencePanel reference={initial.reference} disabled={runDisabled} onRun={source=>void submit(source,'suite')}/>
    <details className="run-history"><summary>运行历史 <span>最近 20 次</span></summary>{history.error?<p role="alert">{history.error.message}</p>:history.data?.length?history.data.map(run=><button key={run.id} onClick={()=>setRunId(run.id)}><time>{new Date(run.created_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}</time><span>{runLabel(run.status)}</span><small>{run.passed}/{run.total}</small></button>):<p className="muted small">还没有运行记录。</p>}</details>
  </section>
}
