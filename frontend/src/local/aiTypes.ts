export type AiConfig={configured:boolean;model:string;key_hint:string;error?:string|null}
export type AiOptions={statement:boolean;code:boolean;notes:boolean;history:boolean}
export type AiContext={code:string;language:string;datasetId:string;notes:string}
export type AiRequest={request_id:string;question:string;dataset_id:string;code:string;language:string;include_statement:boolean;include_code:boolean;notes:string|null;include_history:boolean;run_id:string|null}
export type AiMessage={id:string;role:'user'|'assistant';content:string;status:string;error?:string;created_at:string;attachments?:string[];retry?:AiRequest}
export type AiChat={messages:AiMessage[];busy:boolean}
export function makeAiRequest(question:string,context:AiContext,options:AiOptions,runId?:string):AiRequest{
  if(!question.trim())throw new Error('请输入问题')
  if(question.trim().length>4000)throw new Error('问题最多 4000 字')
  if(options.code&&context.code.length>65536)throw new Error('代码过长，请减少附带内容')
  if(options.notes&&context.notes.length>16000)throw new Error('笔记过长，请减少附带内容')
  return {request_id:crypto.randomUUID(),question:question.trim(),dataset_id:context.datasetId,
    code:options.code?context.code:'',language:context.language,include_statement:options.statement,
    include_code:options.code,notes:options.notes?context.notes:null,include_history:options.history,run_id:runId??null}
}
