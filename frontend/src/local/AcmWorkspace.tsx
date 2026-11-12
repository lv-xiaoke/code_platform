import {useEffect,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {Play,Plus,Save,RefreshCw,Terminal,ChevronDown} from 'lucide-react'
import {api,downloadText} from './api'
import type {AcmCase,AcmSuite,CodeRun,RunnerHealth} from './acmTypes'
import {useAcmSuite,EMPTY_CASE} from './useAcmSuite'
import {prepareRun,prepareQuickRun} from './runRequest'
import CodePractice from './CodePractice'
import {RunResults,runLabel} from './RunResults'
import {useTerminal} from './useTerminal'
import {TerminalPanel} from './TerminalPanel'
import './acm.css'

type Props={problemId:string;code:string;language:string;onCodeChange:(code:string)=>void;onLanguageChange:(language:string)=>void;onRewrite:(historyId?:number)=>Promise<boolean>;changingCode:boolean;registerGuard:(guard:(()=>Promise<boolean>)|null)=>void;beforeRun?:()=>Promise<boolean>;onAnalyze?:(runId:string)=>void}

export default function AcmWorkspace(props:Props){
  const acm=useQuery({queryKey:['acm',props.problemId],queryFn:()=>api<AcmSuite>(`/problems/${props.problemId}/acm`),staleTime:0})
  if(acm.data)return <AcmContent {...props} initial={acm.data}/>
  return <section className="acm-workspace">{acm.error?<p className="local-error" role="alert">{acm.error.message}<button onClick={()=>void acm.refetch()}>重新读取</button></p>:<p>正在载入 Python ACM 工作区…</p>}</section>
}

function AcmContent({initial,...props}:Props&{initial:AcmSuite}){
  const suite=useAcmSuite(props.problemId,initial),qc=useQueryClient()
  const [inputOpen,setInputOpen]=useState(false),[showTerminal,setShowTerminal]=useState(false)
  const [codeView,setCodeView]=useState<'current'|'history'>('current')
  const terminal=useTerminal(props.problemId)
  const [runId,setRunId]=useState<string|null>(null),[submitting,setSubmitting]=useState(false),[error,setError]=useState('')
  const pending=useRef<{signature:string;body:unknown}|null>(null)
  const results=useRef<HTMLDivElement>(null)
  const health=useQuery({queryKey:['runner-health'],queryFn:()=>api<RunnerHealth>('/runner/health'),staleTime:10000})
  const active=useQuery({queryKey:['run',runId],queryFn:()=>api<CodeRun>('/runs/'+runId),enabled:!!runId,refetchInterval:q=>['queued','running'].includes(q.state.data?.status??'queued')?500:false,staleTime:0})
  const history=useQuery({queryKey:['runs',props.problemId],queryFn:()=>api<CodeRun[]>(`/problems/${props.problemId}/runs`),staleTime:0})
  const busy=submitting||terminal.busy||['queued','running'].includes(active.data?.status??'')
  const draft=suite.value.draft??{...EMPTY_CASE}
  useEffect(()=>{props.registerGuard(async()=>{const [stopped,saved]=await Promise.all([terminal.stop(),suite.flush()]);return stopped&&saved});return()=>props.registerGuard(null)},[props.registerGuard,suite.flush,terminal.stop])
  useEffect(()=>{if(active.data&&!['queued','running'].includes(active.data.status))void qc.invalidateQueries({queryKey:['runs',props.problemId]})},[active.data?.status,props.problemId,qc])
  const updateDraft=(patch:Partial<AcmCase>)=>suite.update({draft:{...draft,...patch}})
  async function submit(source:string,mode:'quick'|'custom'|'suite'){
    setError('')
    if(!source.trim()){setError('请先编写代码，并在代码末尾添加函数调用、print 或 assert。');return}
    setSubmitting(true)
    try{
      if(props.beforeRun&&!await props.beforeRun())return
      if(mode==='quick'&&!inputOpen){setShowTerminal(true);setRunId(null);await terminal.start(source);return}
      if(mode!=='quick'&&!await suite.flush())return
      const {submission,signature}=mode==='quick'?prepareQuickRun(source,inputOpen?suite.snapshot().draft?.stdin??'':''):prepareRun(source,mode,suite.snapshot())
      if(pending.current?.signature!==signature)pending.current={signature,body:{...submission,request_id:crypto.randomUUID()}}
      const result=await api<CodeRun>(`/problems/${props.problemId}/runs`,{method:'POST',body:JSON.stringify(pending.current.body)})
      pending.current=null;setShowTerminal(false);setRunId(result.id);qc.setQueryData(['run',result.id],result)
      if(mode!=='quick')results.current?.scrollIntoView({block:'start'})
      void qc.invalidateQueries({queryKey:['runs',props.problemId]})
    }catch(e){setError((e as Error).message)}finally{setSubmitting(false)}
  }
  function saveCase(){
    setError('')
    const cases=suite.value.cases
    const editing=cases.some(c=>c.id===draft.id)
    if(!editing&&cases.length>=16){setError('最多保存 16 组自定义测试。');return}
    const item={...draft,id:editing?draft.id:crypto.randomUUID()}
    suite.update({cases:editing?cases.map(c=>c.id===item.id?item:c):[...cases,item],draft:item})
    void suite.flush()
  }
  const savedCases=suite.value.cases
  const editingSavedCase=savedCases.some(c=>c.id===draft.id)
  const runDisabled=busy||props.changingCode||codeView==='history'||!health.data?.available
  const testDisabled=runDisabled||props.language!=='python'
  return <section className="acm-workspace" aria-label="Python ACM 工作区"><header className="acm-title"><div><span className="eyebrow">WRITE · RUN · UNDERSTAND</span><h3><Terminal size={18}/>Python 代码</h3></div><span className={'runner-chip '+(health.data?.available?'ready':'')}>{health.isFetching?'检查运行环境…':health.data?.available?'Docker 已就绪':'Docker 未就绪'}</span></header>
    {(health.error||health.data?.error)&&<div className="local-error" role="alert">{health.error?.message??health.data?.error}<button onClick={()=>void health.refetch()}><RefreshCw size={13}/>重新检查</button></div>}
    {health.data&&!health.data.available&&<p className="runner-setup-hint">本地运行需要 Docker Desktop 已启动并安装 Python 镜像。首次准备可运行 <code>.\scripts\setup-runner.ps1</code>，完成后点击“重新检查”。题目阅读、代码和测试编辑仍可使用。</p>}
    <CodePractice problemId={props.problemId} code={props.code} language={props.language} view={codeView} onViewChange={setCodeView} onCodeChange={props.onCodeChange} onLanguageChange={props.onLanguageChange} onRewrite={async historyId=>{const ok=await props.onRewrite(historyId);if(ok){setShowTerminal(false);setRunId(null);pending.current=null}return ok}} changing={props.changingCode} disabled={busy}/>
    <p className="quick-code-hint muted">点击运行后，可在下方终端输入并按 Enter。也可以在代码中直接写函数调用、print 或 assert。</p>
    <div className="quick-run-actions"><button className="primary" disabled={runDisabled||props.language!=='python'} onClick={()=>void submit(props.code,'quick')}><Play size={15}/>{busy?'运行中…':'运行'}</button><button aria-expanded={inputOpen} aria-controls={'quick-input-'+props.problemId} onClick={()=>setInputOpen(!inputOpen)}>预设输入<ChevronDown size={13}/></button></div>
    <div className="quick-input" id={'quick-input-'+props.problemId} hidden={!inputOpen}><label>标准输入（可选）<textarea aria-label="自定义输入" value={draft.stdin} spellCheck={false} placeholder="使用 input() 或 sys.stdin 时，在这里填写输入。" onChange={e=>updateDraft({stdin:e.target.value})}/></label><p className="muted small">只在展开时将这里的文本传给程序；收起后运行进入交互终端。直接在代码中写测试调用时无需填写。</p></div>
    {error&&<div className="local-error" role="alert">{error}</div>}
    {suite.error&&<div className="local-error" role="alert">测试保存失败，当前输入保留：{suite.error}<button onClick={()=>void suite.flush()}>重试保存</button><button onClick={()=>{downloadText(`ACM测试草稿-${props.problemId}.json`,JSON.stringify(suite.value,null,2));void suite.reloadServer()}}>导出测试草稿并载入服务器版本</button></div>}
    <div ref={results}>
    {showTerminal&&terminal.error&&!terminal.state&&<div className="local-error" role="alert">{terminal.error}</div>}
    {showTerminal&&terminal.starting?<section className="interactive-terminal" aria-label="交互终端"><p role="status">正在启动交互终端…</p></section>:showTerminal&&terminal.state?<TerminalPanel state={terminal.state} sending={terminal.sending} error={terminal.error} onSend={text=>terminal.send(text)} onEof={()=>void terminal.send('',true)} onStop={()=>void terminal.stop()}/>:runId?<RunResults runId={runId}/>:<section className="acm-results console-empty" aria-label="运行结果"><h3>运行结果</h3><p className="muted small">点击运行后，程序输出和终端输入区会显示在这里。</p></section>}
    {props.onAnalyze&&(showTerminal?terminal.state&&!terminal.busy:active.data&&!['queued','running'].includes(active.data.status))&&<button className="ai-analyze-run" onClick={()=>props.onAnalyze?.(showTerminal?terminal.state!.id:runId!)}>让 AI 分析本次运行</button>}
    </div>
    <details className="advanced-tests"><summary>高级测试</summary><div className="advanced-tests-body">
    <div className="case-toolbar"><label>样例名称<input value={draft.name===EMPTY_CASE.name?'':draft.name} placeholder="选填" maxLength={100} onChange={e=>updateDraft({name:e.target.value||EMPTY_CASE.name})}/></label><span role="status">{suite.status}</span><button onClick={()=>{setError('');suite.update({draft:{...EMPTY_CASE}})}}><Plus size={13}/>新建样例</button></div>
    <div className="case-input-grid"><label>标准输入<textarea value={draft.stdin} spellCheck={false} placeholder="无需输入可留空" onChange={e=>updateDraft({stdin:e.target.value})}/></label><label>期望输出<textarea value={draft.expected_stdout??''} spellCheck={false} placeholder={draft.expected_stdout===null?'留空则只查看运行结果':'留空则校验程序没有输出'} onChange={e=>updateDraft({expected_stdout:e.target.value||null})}/></label></div>
    <div className="case-options"><label className="expected-toggle"><input type="checkbox" checked={draft.expected_stdout!==null} onChange={e=>updateDraft({expected_stdout:e.target.checked?'':null})}/>校验期望输出</label>{draft.expected_stdout!==null&&<select aria-label="输出比较" value={draft.comparison} onChange={e=>updateDraft({comparison:e.target.value as AcmCase['comparison']})}><option value="tokens">忽略空白差异</option><option value="exact">严格文本（统一换行）</option><option value="unordered_lines">忽略行顺序</option><option value="float">浮点容差 1e-6</option></select>}</div>
    <div className="acm-run-actions"><button onClick={saveCase}><Save size={14}/>{editingSavedCase?'更新样例':'保存样例'}</button><button disabled={testDisabled} onClick={()=>void submit(props.code,'custom')}>运行当前样例</button></div>
    <section className="saved-tests" aria-label="已保存样例">
      <div className="saved-tests-header"><h4>已保存样例（{savedCases.length}）</h4><button className="primary" disabled={testDisabled||savedCases.length===0} onClick={()=>void submit(props.code,'suite')}>一键测试全部</button></div>
      {savedCases.length?savedCases.map(c=><div className="saved-test" key={c.id}><span>{c.name}</span><button onClick={()=>{setError('');suite.update({draft:{...c}})}}>{c.id===draft.id?'重新载入':'编辑'}</button><button onClick={()=>suite.update({cases:savedCases.filter(v=>v.id!==c.id),...(c.id===draft.id?{draft:{...draft,id:null}}:{})})}>移除</button></div>):<p className="muted small">保存样例后，即可一键测试全部。</p>}
    </section>
    </div></details>
    <details className="run-history"><summary>运行历史 <span>最近 20 次</span></summary>{history.error?<p role="alert">{history.error.message}</p>:history.data?.length?history.data.map(run=><button key={run.id} disabled={busy} onClick={()=>{setShowTerminal(false);setRunId(run.id)}}><time>{new Date(run.created_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}</time><span>{runLabel(run.status)}</span><small>{run.passed}/{run.total}</small></button>):<p className="muted small">还没有运行记录。</p>}</details>
  </section>
}
