import {Fragment,useState,type ReactNode} from 'react'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import cpp from 'highlight.js/lib/languages/cpp'
import java from 'highlight.js/lib/languages/java'
for(const [name,language] of Object.entries({python,javascript,cpp,java}))hljs.registerLanguage(name,language)

function inline(text:string):ReactNode[]{
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\s)]+\))/g).map((part,i)=>{
    if(part.startsWith('`'))return <code key={i}>{part.slice(1,-1)}</code>
    if(part.startsWith('**'))return <strong key={i}>{part.slice(2,-2)}</strong>
    const match=part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if(match){
      try{const url=new URL(match[2]);if(['https:','http:'].includes(url.protocol))return <a key={i} href={url.href} target="_blank" rel="noreferrer">{match[1]}</a>}catch{/* Render unsupported destinations as text. */}
    }
    return <Fragment key={i}>{part}</Fragment>
  })
}
function Code({language,code}:{language:string;code:string}){
  const [message,setMessage]=useState('')
  async function copy(){try{await navigator.clipboard.writeText(code);setMessage('已复制')}catch{setMessage('复制失败，请手动选择代码')}}
  return <div className="ai-code"><header><span>{language||'代码'}</span><button onClick={()=>void copy()}>{message||'复制代码'}</button></header><pre><code>{hljs.getLanguage(language)?<span dangerouslySetInnerHTML={{__html:hljs.highlight(code,{language}).value}}/>:code}</code></pre></div>
}
export function AiMarkdown({content}:{content:string}){
  const lines=content.replace(/\r\n/g,'\n').split('\n'),blocks:ReactNode[]=[]
  for(let i=0;i<lines.length;i++){
    const line=lines[i],fence=line.match(/^\s*```([\w+-]*)/)
    if(fence){const code:string[]=[];while(++i<lines.length&&!/^\s*```\s*$/.test(lines[i]))code.push(lines[i]);blocks.push(<Code key={i} language={fence[1].toLowerCase()} code={code.join('\n')}/>);continue}
    if(!line.trim())continue
    const heading=line.match(/^#{1,6}\s+(.+)$/),list=line.match(/^\s*(?:[-*]|\d+\.)\s+(.+)$/)
    blocks.push(heading?<h4 key={i}>{inline(heading[1])}</h4>:list?<div className="ai-list-line" key={i}>• {inline(list[1])}</div>:<p key={i}>{inline(line)}</p>)
  }
  return <div className="ai-markdown">{blocks}</div>
}
