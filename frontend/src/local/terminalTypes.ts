export type TerminalState={id:string;problem_id:string;status:string;stdout:string;stderr:string;stdin:string;transcript:string;input_closed:boolean;python_version?:string|null;exit_code?:number|null;error?:string|null}
export type TerminalInputRequest={signature:string;body:{request_id:string;text:string;eof:boolean}}
export const terminalActive=(state?:TerminalState)=>!!state&&['starting','running','stopping'].includes(state.status)

export function prepareTerminalInput(previous:TerminalInputRequest|null,text:string,eof=false):TerminalInputRequest{
  const input=eof?'':text.endsWith('\n')?text:text+'\n'
  const signature=JSON.stringify({text:input,eof})
  return previous?.signature===signature?previous:{signature,body:{request_id:crypto.randomUUID(),text:input,eof}}
}
