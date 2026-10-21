import {useQuery} from '@tanstack/react-query'
import {api} from './api'
import type {CodeRun} from './acmTypes'

const labels:Record<string,string>={queued:'排队中',running:'运行中',completed:'已完成',failed:'执行器错误',interrupted:'服务中断',passed:'通过',wrong_answer:'输出不符',executed:'运行完成（未设置期望）',syntax_error:'语法错误',runtime_error:'运行异常',memory_limit:'内存超限',time_limit:'超时',output_limit:'输出超限'}
export const runLabel=(status:string)=>labels[status]??status

export function RunResults({runId}:{runId:string}){
  const run=useQuery({queryKey:['run',runId],queryFn:()=>api<CodeRun>('/runs/'+runId),refetchInterval:q=>['queued','running'].includes(q.state.data?.status??'queued')?500:false,staleTime:0})
  if(run.error)return <div className="local-error" role="alert">读取运行结果失败，已提交的任务会继续执行：{run.error.message}<button onClick={()=>void run.refetch()}>重试读取</button></div>
  if(!run.data)return <p className="muted">正在读取运行记录…</p>
  const data=run.data
  return <section className="acm-results" aria-label="运行结果"><header><h3>运行结果 <span className={'run-status status-'+data.status}>{runLabel(data.status)}</span></h3><span>{data.passed} / {data.total} 组通过{data.python_version?` · Python ${data.python_version}`:''}</span></header><p className="muted small">结果仅针对本次保存的测试输入和期望输出。运行不会自动改变练习记录或复习安排。</p>{data.error&&<p className="local-error" role="alert">{data.error}</p>}{data.results?.map((result,i)=><details key={i} open={i===0||!['passed','executed'].includes(result.status)} className={'case-result result-'+result.status}><summary><strong>{i+1}. {result.name}</strong><span>{runLabel(result.status)}</span><small>{result.duration_ms.toFixed(1)} ms</small></summary><div className="result-columns"><div><h4>输入 stdin</h4><pre>{result.stdin||'（空输入）'}</pre></div><div><h4>期望输出</h4><pre>{result.expected_stdout===null?'（未设置）':result.expected_stdout===''?'（空输出）':result.expected_stdout}</pre></div><div><h4>实际输出 stdout</h4><pre>{result.stdout||'（空输出）'}</pre></div></div>{result.stderr&&<div className="result-stderr"><h4>错误输出 stderr</h4><pre>{result.stderr}</pre></div>}</details>)}{data.source_code&&<details className="submitted-source"><summary>查看本次提交的完整代码</summary><pre>{data.source_code}</pre></details>}</section>
}
