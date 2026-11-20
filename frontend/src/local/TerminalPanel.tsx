import {useEffect,useRef,useState} from 'react'
import {Send,Square} from 'lucide-react'
import type {TerminalState} from './terminalTypes'
import {terminalActive} from './terminalTypes'

const labels:Record<string,string>={starting:'启动中…',preparing:'准备中…',compiling:'编译中…',compile_error:'编译错误',compile_time_limit:'编译超时',running:'运行中 · 可输入',stopping:'正在停止…',executed:'程序已结束',runtime_error:'运行异常',syntax_error:'语法错误',memory_limit:'内存超限',time_limit:'运行超时',output_limit:'输出超限',stopped:'已停止',failed:'执行器错误',interrupted:'服务中断'}
type Props={state:TerminalState;sending:boolean;error:string;onSend:(text:string)=>Promise<boolean>;onEof:()=>void;onStop:()=>void}

export function TerminalPanel({state,sending,error,onSend,onEof,onStop}:Props){
  const [input,setInput]=useState('')
  const output=useRef<HTMLPreElement>(null)
  const active=terminalActive(state)
  const inputEnabled=state.status==='running'&&!state.input_closed
  const canInput=inputEnabled&&!sending
  useEffect(()=>{if(output.current)output.current.scrollTop=output.current.scrollHeight},[state.transcript])
  async function send(){const sent=input;if(await onSend(sent))setInput(current=>current===sent?'':current)}
  return <section className="interactive-terminal" aria-label="交互终端"><header><h3>终端 {state.language} {state.runtime_version}</h3><span role="status">{state.input_closed&&state.status==='running'?'运行中 · 输入已结束':labels[state.status]??state.status}</span>{active&&<button onClick={onStop} disabled={state.status==='stopping'}><Square size={12}/>停止</button>}</header>{state.compile&&(state.compile.stderr||state.compile.stdout)&&<details open className="compile-diagnostics"><summary>编译诊断</summary><pre>{state.compile.stdout}{state.compile.stderr}</pre></details>}<pre ref={output} className="terminal-transcript" aria-label="终端输出" tabIndex={0}>{state.transcript||(state.status==='running'?'程序运行中，可以在下方输入…':'（程序没有输出）')}</pre>{(error||state.error)&&<div className="local-error" role="alert">{error||state.error}</div>}<form onSubmit={event=>{event.preventDefault();void send()}}><textarea aria-label="终端输入" autoFocus value={input} disabled={!inputEnabled} readOnly={sending} rows={2} spellCheck={false} placeholder={active?'输入内容后按 Enter 发送，Shift+Enter 换行':'程序已结束，重新点击运行可再次执行'} onChange={event=>setInput(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.nativeEvent.isComposing){event.preventDefault();if(canInput)void send()}}}/><div className="terminal-input-actions"><button type="submit" disabled={!canInput}><Send size={13}/>{sending?'发送中…':'发送'}</button><button type="button" disabled={!canInput} onClick={onEof}>结束输入</button><span className="muted">{active?'Enter 发送 · 结束输入发送 EOF':'输出与输入已保留在运行历史'}</span></div></form></section>
}
