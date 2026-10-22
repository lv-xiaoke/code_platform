import {lazy,Suspense,useEffect,useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {BookOpen,ChevronLeft,ChevronRight,Moon,Search,Settings,Star,Sun} from 'lucide-react'
import {api,type Dataset,type Problem,type ProblemList,type StudyState,type Taxonomy,dateLabel} from './api'
import {useDebouncedValue} from '../hooks/useDebouncedValue'
import {catalogParams,changeFilter,EMPTY_FILTERS,type CatalogFilters,type ListView} from './catalogFilters'
import {ProblemEntry} from './ProblemEntry'
import {DataPanel} from './DataPanel'
import {EditorBoundary} from './EditorBoundary'
import './local.css'
import './simple.css'
import './practice.css'

const NotesDrawer=lazy(()=>import('./NotesDrawer'))
const PracticeDialog=lazy(()=>import('./PracticeDialog'))
const views:[ListView,string][]=[['all','全部'],['todo','未做'],['done','已做'],['favorites','收藏']]

export function App(){
  const qc=useQueryClient()
  const [filters,setFilters]=useState(EMPTY_FILTERS),[view,setView]=useState<ListView>('all'),[page,setPage]=useState(1),[source,setSource]=useState('')
  const [settings,setSettings]=useState(false),[selected,setSelected]=useState<{id:string;dataset:string}|null>(null)
  const noteOpener=useRef<HTMLButtonElement|null>(null)
  const [practice,setPractice]=useState<{id:string;dataset:string}|null>(null)
  const practiceOpener=useRef<HTMLButtonElement|null>(null)
  const [error,setError]=useState(''),[busy,setBusy]=useState<Set<string>>(new Set()),locks=useRef(new Set<string>())
  const [theme,setTheme]=useState(()=>localStorage.getItem('algotop:theme')??'light')
  const search=useDebouncedValue(filters.search,250)
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('algotop:theme',theme)},[theme])
  const datasets=useQuery({queryKey:['datasets'],queryFn:()=>api<Dataset[]>('/catalog/datasets')})
  const taxonomy=useQuery({queryKey:['taxonomies',source],queryFn:()=>api<{items:Taxonomy[];dataset:Dataset|null}>('/catalog/taxonomies'+(source?'?source='+encodeURIComponent(source):''))})
  const params=catalogParams({...filters,search},page,source,view)
  const problems=useQuery({queryKey:['problems','simple',params.toString()],queryFn:()=>api<ProblemList>('/problems?'+params)})
  const data=problems.data
  useEffect(()=>{if(data){const last=Math.max(1,Math.ceil(data.count/20));if(page>last)setPage(last)}},[data?.count,page])
  const change=(key:keyof CatalogFilters,value:string)=>{setFilters(current=>changeFilter(current,key,value));setPage(1)}
  const reset=()=>{setFilters({...EMPTY_FILTERS});setPage(1)}
  const closeNotes=()=>{setSelected(null);requestAnimationFrame(()=>{if(noteOpener.current?.isConnected)noteOpener.current.focus();else document.querySelector<HTMLInputElement>('[aria-label="搜索题号或标题"]')?.focus()})}
  const closePractice=()=>{setPractice(null);requestAnimationFrame(()=>{if(practiceOpener.current?.isConnected)practiceOpener.current.focus({preventScroll:true});else document.querySelector<HTMLInputElement>('[aria-label="搜索题号或标题"]')?.focus({preventScroll:true})})}
  const types=(type:string)=>taxonomy.data?.items.filter(item=>item.type===type&&(type!=='department'||!filters.company||item.parent_company_key===filters.company))??[]
  function taxonomySelect(key:'company'|'department'|'job'|'tag',label:string){
    return <label>{label}<select aria-label={label} value={filters[key]} disabled={taxonomy.isPending||!!taxonomy.error} onChange={event=>change(key,event.target.value)}><option value="">全部{label}</option>{types(key).map(item=><option key={item.source_key} value={item.source_key}>{item.name}</option>)}</select></label>
  }
  async function mark(problem:Problem,patch:{done?:boolean;favorite?:boolean}){
    if(locks.current.has(problem.id))return
    locks.current.add(problem.id);setBusy(new Set(locks.current));setError('')
    try{
      const result=await api<StudyState>(`/problems/${problem.id}/state`,{method:'PATCH',body:JSON.stringify({revision:problem.state_revision,...patch})})
      qc.setQueriesData<ProblemList>({queryKey:['problems']},old=>old?{...old,items:old.items.map(item=>item.id===problem.id?{...item,favorite:result.favorite,done:result.done??item.done,state_revision:result.revision}:item)}:old)
    }catch(cause){setError((cause as Error).message)}
    finally{
      await qc.invalidateQueries({queryKey:['problems']})
      locks.current.delete(problem.id);setBusy(new Set(locks.current))
    }
  }
  const activeSources=Array.from(new Set(datasets.data?.filter(ds=>ds.status==='active').map(ds=>ds.source_name)??[]))
  return <div className="local-app compact-app">
    <header className="compact-header"><div className="compact-header-inner"><a className="compact-brand" href="/">CodeTop<span>题单</span></a><div className="compact-header-actions"><button className="icon-btn" aria-label="切换主题" title="切换主题" onClick={()=>setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}</button><button className="settings-button" onClick={()=>setSettings(true)}><Settings size={15}/>设置</button></div></div></header>
    <main className="compact-main">
      <section className="catalog-controls" aria-label="题目筛选">
        <div className="search-and-views"><div className="simple-search"><Search size={17}/><input aria-label="搜索题号或标题" placeholder="搜索题号或标题" value={filters.search} onChange={event=>change('search',event.target.value)}/>{filters.search&&<button aria-label="清空搜索" onClick={()=>change('search','')}>×</button>}</div><div className="list-tabs" role="group" aria-label="题目范围">{views.map(([value,label])=><button key={value} aria-pressed={view===value} onClick={()=>{setView(value);setPage(1)}}>{label}</button>)}</div></div>
        <div className="simple-filters">{taxonomySelect('company','公司')}{taxonomySelect('department','部门')}{taxonomySelect('job','岗位')}{taxonomySelect('tag','标签')}<label>难度<select aria-label="难度" value={filters.difficulty} onChange={event=>change('difficulty',event.target.value)}><option value="">全部难度</option><option value="1">简单</option><option value="2">中等</option><option value="3">困难</option></select></label><label>最近考察<select aria-label="最近考察" value={filters.recent_days} onChange={event=>change('recent_days',event.target.value)}><option value="">不限时间</option><option value="90">最近三个月</option><option value="180">最近半年</option></select></label><label>排序<select aria-label="排序" value={filters.ordering} onChange={event=>change('ordering',event.target.value)}><option value="-frequency">频次从高到低</option><option value="frequency">频次从低到高</option><option value="-time">最近考察优先</option><option value="display">题号从小到大</option></select></label></div>
        {taxonomy.error&&<div className="local-error" role="alert">筛选项读取失败：{taxonomy.error.message}<button onClick={()=>void taxonomy.refetch()}>重试</button></div>}
      </section>
      <div className="list-meta"><div><strong>{data?.count??'—'}</strong> 道题<span className="scope-description">{data?.scope_label}</span></div><button className="text-button" onClick={reset}>重置筛选</button></div>
      {error&&<div className="local-error" role="alert">{error}<button onClick={()=>setError('')}>关闭提示</button></div>}
      {problems.error?<div className="local-error" role="alert">{problems.error.message}<button onClick={()=>void problems.refetch()}>重试读取</button></div>:problems.isPending?<div className="empty">正在读取题单…</div>:<>
        <div className="problem-table-scroll"><table className="problem-table"><thead><tr><th>已做</th><th>题目</th><th>难度</th><th>{data?.frequency_kind==='source_score'?'来源评分':'累计频次'}</th><th>最近考察</th><th>收藏</th><th>笔记</th></tr></thead><tbody>{data?.items.map(problem=>{
          return <tr key={problem.id}><td><input className="completion-checkbox" type="checkbox" checked={problem.done} disabled={busy.has(problem.id)} aria-label={`标记已做：${problem.display_id} ${problem.title}`} onChange={event=>void mark(problem,{done:event.target.checked})}/></td><td><ProblemEntry displayId={problem.display_id} title={problem.title} url={problem.url} onOpen={event=>{practiceOpener.current=event.currentTarget;setPractice({id:problem.id,dataset:problem.dataset_id})}}/></td><td><span className={'difficulty d'+problem.difficulty}>{['','简单','中等','困难'][problem.difficulty]}</span></td><td className="problem-frequency">{problem.frequency??'—'}</td><td className="problem-last-seen">{problem.last_seen?.slice(0,10)??'—'}</td><td><button className={'row-icon '+(problem.favorite?'is-favorite':'')} aria-label={`收藏：${problem.display_id} ${problem.title}`} aria-pressed={problem.favorite} disabled={busy.has(problem.id)} onClick={()=>void mark(problem,{favorite:!problem.favorite})}><Star size={16} fill={problem.favorite?'currentColor':'none'}/></button></td><td><button className={'row-note '+(problem.has_note?'has-note':'')} aria-label={`笔记：${problem.display_id} ${problem.title}`} onClick={event=>{noteOpener.current=event.currentTarget;setSelected({id:problem.id,dataset:problem.dataset_id})}}><BookOpen size={15}/><span>{problem.has_note?'查看':'添加'}</span></button></td></tr>
        })}</tbody></table></div>
        {data?.items.length===0&&<div className="empty"><p>没有符合条件的题目</p><button onClick={()=>{reset();setView('all')}}>查看全部题目</button></div>}
        <footer className="simple-pagination"><span>每页 20 题</span><div><button aria-label="上一页" disabled={page===1} onClick={()=>setPage(page-1)}><ChevronLeft size={16}/></button><span>{page} / {Math.max(1,Math.ceil((data?.count??0)/20))}</span><button aria-label="下一页" disabled={page*20>=(data?.count??0)} onClick={()=>setPage(page+1)}><ChevronRight size={16}/></button></div></footer>
      </>}
      <footer className="compact-footer"><span>数据生成 {dateLabel(data?.source_generated_at)} · {data?.frequency_kind==='source_score'?'来源评分':'累计快照频次'}</span><span>笔记与进度保存在本机</span></footer>
    </main>
    {selected&&<EditorBoundary onClose={closeNotes} fallback={<section className="note-load-error" role="alert"><h3>笔记面板暂时无法载入</h3><p>题单仍可使用。恢复连接后刷新页面，再打开笔记。</p><div className="button-row"><button onClick={()=>window.location.reload()}>刷新页面</button><button onClick={closeNotes}>返回题单</button></div></section>}><Suspense fallback={<div className="note-loading" role="status">正在打开笔记…</div>}><NotesDrawer id={selected.id} datasetId={selected.dataset} onClose={closeNotes}/></Suspense></EditorBoundary>}
    {practice&&<EditorBoundary onClose={closePractice} fallback={<section className="note-load-error" role="alert"><h3>练习面板暂时无法载入</h3><p>恢复连接后刷新页面，再打开本地练习。</p><div className="button-row"><button onClick={()=>window.location.reload()}>刷新页面</button><button onClick={closePractice}>返回题单</button></div></section>}><Suspense fallback={<div className="note-loading" role="status">正在打开本地练习…</div>}><PracticeDialog id={practice.id} datasetId={practice.dataset} onClose={closePractice}/></Suspense></EditorBoundary>}
    {settings&&<DataPanel source={source} sources={activeSources} onSourceChange={value=>{setSource(value);reset()}} onClose={()=>setSettings(false)}/>}
  </div>
}
