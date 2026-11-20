import type {CompileResult,Budget} from './languageTypes'
export type TerminalState={id:string;problem_id:string;status:string;stdout:string;stderr:string;stdin:string;transcript:string;input_closed:boolean;language?:string;runtime_version?:string;toolchain_id?:string;compile?:CompileResult;limits?:Budget;python_version?:string|null;exit_code?:number|null;error?:string|null}
export type TerminalInputRequest={signature:string;body:{request_id:string;text:string;eof:boolean}}
export const terminalActive=(state?:TerminalState)=>!!state&&['starting','preparing','compiling','running','stopping'].includes(state.status)
export type TerminalStartBody={request_id:string;source_code:string;language:string}
export function prepareTerminalStart(previous:TerminalStartBody|null,source:string,language='python'):TerminalStartBody{
  return previous?.source_code===source&&previous.language===language?previous:{request_id:crypto.randomUUID(),source_code:source,language}
}

export function prepareTerminalInput(previous:TerminalInputRequest|null,text:string,eof=false):TerminalInputRequest{
  const input=eof?'':text.endsWith('\n')?text:text+'\n'
  const signature=JSON.stringify({text:input,eof})
  return previous?.signature===signature?previous:{signature,body:{request_id:crypto.randomUUID(),text:input,eof}}
}
