export type CodeDraft={problem_id:string;language:string;code_text:string;revision:number;exists:boolean;created_at:string;updated_at:string}
export type Budget={wall_seconds:number;cpu_seconds:number;memory_mb:number;output_bytes:number;heap_mb?:number|null;interactive_wall_seconds?:number;compile?:Budget|null}
export type CompileResult={status?:string;stdout?:string;stderr?:string;exit_code?:number|null;duration_ms?:number}
export type LanguageCapability={language:string;label?:string;template?:string;compiled?:boolean;kind:'native'|'docker';state:string;available:boolean;runtime_version?:string;toolchain_id?:string;error?:string;job_id?:string;limits?:Budget;memory_enforcement?:string;sdk?:string|null}
export type RewriteResult={draft:CodeDraft;preference:{language:string;revision:number}}
export const runningStates=['queued','starting','preparing','compiling','running','stopping']
