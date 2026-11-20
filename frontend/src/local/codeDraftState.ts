import type {CodeDraft,RewriteResult} from './languageTypes.ts'

export const initialCode=(draft:CodeDraft,template:string)=>draft.exists?draft.code_text:template
type Dependencies={
  stopActive:()=>Promise<boolean>;read:(language:string)=>Promise<CodeDraft>;
  write:(language:string,code:string,revision:number)=>Promise<CodeDraft>;
  select:(language:string)=>Promise<unknown>;template:(language:string)=>Promise<string>;
  rewrite:(language:string,revision:number,historyId?:number)=>Promise<RewriteResult>;
}
type Snapshot={draft:CodeDraft;status:string;error:string;changing:boolean;dirty:boolean}

/** One owner for save/switch races. React only subscribes to immutable snapshots. */
export class DraftController{
  private state:Snapshot
  private saved:CodeDraft
  private touched=false
  private listeners=new Set<()=>void>()
  private saving:Promise<boolean>|null=null
  private transition:Promise<boolean>|null=null
  deps:Dependencies
  constructor(initial:CodeDraft,deps:Dependencies){
    this.saved=initial;this.deps=deps
    this.state={draft:initial,status:'已保存',error:'',changing:false,dirty:false}
  }
  getSnapshot=()=>this.state
  subscribe=(listener:()=>void)=>{this.listeners.add(listener);return()=>{this.listeners.delete(listener)}}
  private changed=()=>this.state.draft.code_text!==this.saved.code_text||(!this.saved.exists&&this.touched)
  private update(patch:Partial<Snapshot>){
    this.state={...this.state,...patch}
    this.state={...this.state,dirty:this.changed()}
    for(const listener of this.listeners)listener()
  }
  setCode=(code:string)=>{
    if(this.transition)return
    this.touched=true
    this.update({draft:{...this.state.draft,code_text:code},status:'等待保存'})
  }
  save=():Promise<boolean>=>{
    if(this.saving)return this.saving
    const task=Promise.resolve().then(async()=>{
      try{
        while(this.changed()){
          const sent=this.state.draft
          this.update({status:'保存中',error:''})
          const result=await this.deps.write(sent.language,sent.code_text,sent.revision)
          this.saved=result
          this.touched=this.state.draft.code_text!==sent.code_text
          this.update({draft:{...result,code_text:this.state.draft.code_text},status:'已保存'})
        }
        return true
      }catch(error){this.update({status:'保存失败',error:(error as Error).message});return false}
      finally{this.saving=null}
    })
    this.saving=task
    return task
  }
  flush=async()=>{
    if(this.transition&&!await this.transition)return false
    return this.save()
  }
  private commit(remote:CodeDraft,code=remote.code_text){
    this.saved=remote;this.touched=!remote.exists&&code!==remote.code_text
    this.update({draft:{...remote,code_text:code},status:this.touched?'等待保存':'已保存',error:''})
  }
  private change(action:()=>Promise<void>,save=true):Promise<boolean>{
    if(this.transition)return this.transition
    this.update({changing:true,error:''})
    const task=Promise.resolve().then(async()=>{
      try{
        if(!await this.deps.stopActive())throw Error('活动运行或测试尚未停止，当前草稿已保留。')
        if(save&&!await this.save())return false
        await action()
        return true
      }catch(error){this.update({error:(error as Error).message,status:'操作未完成'});return false}
      finally{this.transition=null;this.update({changing:false})}
    })
    this.transition=task
    return task
  }
  switchLanguage=(language:string):Promise<boolean>=>{
    if(this.transition)return this.transition
    if(language===this.state.draft.language)return Promise.resolve(true)
    return this.change(async()=>{
      const remote=await this.deps.read(language)
      const code=initialCode(remote,remote.exists?'':await this.deps.template(language))
      await this.deps.select(language)
      this.commit(remote,code)
    })
  }
  rewriteCode=(historyId?:number,language=this.state.draft.language):Promise<boolean>=>this.change(async()=>{
    const target=language===this.state.draft.language?this.state.draft:await this.deps.read(language)
    const result=await this.deps.rewrite(language,target.revision,historyId)
    this.commit(result.draft)
  })
  reloadServer=()=>this.change(async()=>{
    this.commit(await this.deps.read(this.state.draft.language))
  },false)
  loadInitialTemplate=async()=>{
    const initial=this.state.draft
    if(initial.exists||initial.code_text||this.touched)return
    try{
      const template=await this.deps.template(initial.language)
      if(this.state.draft!==initial||this.transition||this.touched)return
      if(template)this.commit(initial,template)
    }catch{/* Editing and saving work even when the template lookup is unavailable. */}
  }
}
