import type {CaseResult} from './acmTypes'

export function ConsoleOutput({result,statusLabel}:{result:CaseResult;statusLabel:string}){
  return <div className="console-output"><div className="console-status"><span className={result.status==='executed'?'muted':'error-text'}>{statusLabel}</span><small>{result.duration_ms.toFixed(1)} ms</small></div><h4>标准输出</h4><pre>{result.stdout||'（无输出）'}</pre>{result.stderr&&<div className="console-stderr"><h4>错误信息</h4><pre>{result.stderr}</pre></div>}{result.stdin!==''&&<details className="submitted-source"><summary>本次输入</summary><pre>{result.stdin}</pre></details>}</div>
}
