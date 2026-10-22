import {ExternalLink} from 'lucide-react'
import {problemDestination} from './links'
import type {MouseEvent} from 'react'

export function ProblemEntry({displayId,title,url,onOpen}:{displayId:string;title:string;url:string|null;onOpen:(event:MouseEvent<HTMLButtonElement>)=>void}){
  const destination=problemDestination(url)
  return <div className="problem-entry"><button className="problem-link local-problem-button" aria-label={`本地练习：${displayId} ${title}`} title="查看本地题目并练习" onClick={onOpen}><span className="problem-number">{displayId}</span><span>{title}</span></button>{destination?<a className="problem-source-link" href={destination.href} target="_blank" rel="noreferrer" aria-label={`在${destination.platform}打开：${title}`} title={`在${destination.platform}打开原题`}><ExternalLink size={13}/></a>:<small className="muted">暂无原题链接</small>}</div>
}
