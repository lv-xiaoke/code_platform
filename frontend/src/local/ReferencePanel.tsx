import {useState} from 'react'
import type {AcmReference} from './acmTypes'
import PythonEditor from './PythonEditor'

export function ReferencePanel({reference,onRun,disabled=false}:{reference:AcmReference|null;onRun?:(source:string)=>void;disabled?:boolean}){
  const [copied,setCopied]=useState(false),[copyError,setCopyError]=useState('')
  async function copy(){try{await navigator.clipboard.writeText(reference!.source_code);setCopied(true);setCopyError('')}catch{setCopyError('复制失败，可以从下方代码中选择并复制。')}}
  if(!reference)return <div className="acm-reference-empty">本题暂未收录完整参考实现，可以在原题网站查看题解。</div>
  return <details className="acm-reference"><summary>查看完整 Python 参考实现 <span>思路 · 复杂度 · 完整代码</span></summary><div className="reference-body"><p className="reference-attribution">{reference.attribution}</p><h4>解题思路</h4><p>{reference.explanation}</p><p className="muted small">{reference.complexity}</p><div className="button-row">{onRun&&<button disabled={disabled} onClick={()=>onRun(reference.source_code)}>运行参考实现（全部测试）</button>}<button onClick={()=>void copy()}>{copied?'已复制':'复制完整代码'}</button></div>{copyError&&<p role="alert">{copyError}</p>}<PythonEditor value={reference.source_code} label="Python 参考代码" readOnly height="360px"/></div></details>
}
