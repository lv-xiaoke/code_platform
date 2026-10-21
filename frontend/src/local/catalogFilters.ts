export type CatalogFilters={search:string;company:string;department:string;job:string;tag:string;difficulty:string;recent_days:string;ordering:string}
export type ListView='all'|'todo'|'done'|'favorites'
export const EMPTY_FILTERS:CatalogFilters={search:'',company:'',department:'',job:'',tag:'',difficulty:'',recent_days:'',ordering:'-frequency'}

export function changeFilter(current:CatalogFilters,key:keyof CatalogFilters,value:string):CatalogFilters{
  return {...current,[key]:value,...(key==='company'?{department:''}:{})}
}

export function catalogParams(filters:CatalogFilters,page:number,source:string,view:ListView){
  const params=new URLSearchParams({page:String(page),page_size:'20',...(source?{source}:{})})
  Object.entries(filters).forEach(([key,value])=>{if(value)params.set(key,value)})
  if(view==='todo'||view==='done')params.set('completion',view)
  if(view==='favorites')params.set('favorite','true')
  return params
}
