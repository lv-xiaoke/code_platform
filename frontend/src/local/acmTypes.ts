export type Comparison='tokens'|'exact'|'unordered_lines'|'float'
export type AcmCase={id?:string|null;name:string;stdin:string;expected_stdout:string|null;comparison:Comparison}
export type AcmSuite={revision:number;cases:AcmCase[];draft:AcmCase|null;updated_at?:string|null}
export type RunnerHealth={available:boolean;image_ref:string;python_series:string;error?:string;limits:{case_timeout_seconds:number;memory_mb:number;output_limit_bytes:number}}
export type CaseResult=AcmCase&{stdout:string;stderr:string;status:string;exit_code:number|null;duration_ms:number}
export type CodeRun={id:string;problem_id:string;status:string;passed:number;total:number;created_at:string;finished_at:string|null;error:string|null;source_code?:string;cases?:AcmCase[];results?:CaseResult[];python_version?:string;image_ref?:string}
