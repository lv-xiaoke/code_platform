export type StudyState = {problem_id:string;mastery:number;favorite:boolean;review_enabled:boolean;review_step:number;next_review_date:string|null;revision:number;updated_at:string;done?:boolean}
export type Note = {body_md:string;code_text:string;language:string;revision:number;updated_at:string;draft_revision?:number;draft_exists?:boolean}
export type CodeVersion = {id:number;problem_id:string;code_text:string;language:string;created_at:string}
export type Problem = {id:string;dataset_id:string;display_id:string;title:string;difficulty:1|2|3;frequency:number|null;last_seen:string|null;url:string|null;mastery:number;favorite:boolean;done:boolean;state_revision:number;has_note:boolean;next_review_date:string|null;review_enabled:boolean}
export type Detail = Problem & {content_html:string|null;source_name:string;generated_at:string|null;imported_at:string;state:StudyState;note:Note;attempts:{id:string;practiced_at:string;outcome:string;duration_seconds:number|null}[]}
export type ProblemList = {items:Problem[];count:number;ranking_scope:string;scope_label:string;window_key:string;frequency_kind:string;source_generated_at:string|null;dataset_id:string}
export type Dataset = {id:string;source_name:string;generated_at:string|null;imported_at:string;status:string;sha256:string;source_commit:string|null;summary:{questions:number}}
export type Taxonomy = {type:string;source_key:string;name:string;parent_company_key:string|null}
export type Backup = {filename:string;bytes:number;download_url:string}
export type Preview = {id:string;kind:string;source_name:string;sha256:string;questions:number;generated_at:string|null;new:number;changed:number;missing_content:number;missing_url:number;notes:number;unmatched:string[];warnings:string[];ambiguous:{source_record_id:string;title:string;candidates:{problem_id:string;title:string}[]}[];scopes:Record<string,number>;existing_dataset_id?:string}

let session:Promise<string>|undefined
export class ApiError extends Error { constructor(public status:number,message:string){super(message)} }
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  const headers = new Headers(init.headers)
  if(init.method && init.method!=='GET'){
    session ??= fetch('/api/v1/session').then(async r=>{if(!r.ok)throw new Error('本地服务不可用');return (await r.json()).token as string}).catch(e=>{session=undefined;throw e})
    headers.set('X-Session-Token',await session)
    if(init.body && !(init.body instanceof FormData))headers.set('Content-Type','application/json')
  }
  const response=await fetch('/api/v1'+path,{...init,headers})
  if(!response.ok){
    const data=await response.json().catch(()=>({detail:'服务暂时不可用'}))
    if(response.status===403)session=undefined
    const detail=data.detail
    throw new ApiError(response.status,typeof detail==='string'?detail:detail?.message??JSON.stringify(detail))
  }
  return response.json() as Promise<T>
}
export function downloadText(name:string,text:string){
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}))
  const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)
}
export function dateLabel(value:string|null|undefined){return value?new Date(value).toLocaleDateString('zh-CN',{timeZone:'Asia/Shanghai'}):'来源未提供'}
export {safeLink} from './links'
