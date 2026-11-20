import {useEffect,useMemo,useState} from 'react'
import CodeMirror from '@uiw/react-codemirror'
import {python} from '@codemirror/lang-python'
import {cpp} from '@codemirror/lang-cpp'
import {java} from '@codemirror/lang-java'
import {javascript} from '@codemirror/lang-javascript'
import {go} from '@codemirror/lang-go'
import {rust} from '@codemirror/lang-rust'
import {sql} from '@codemirror/lang-sql'
import {EditorView} from '@codemirror/view'
import {githubDark,githubLight} from '@uiw/codemirror-theme-github'

export default function CodeEditor({language,value,onChange,readOnly=false,ariaLabel,height='300px'}:{language:string;value:string;onChange?:(value:string)=>void;readOnly?:boolean;ariaLabel:string;height?:string}){
  const [mounted,setMounted]=useState(false)
  useEffect(()=>{setMounted(true)},[])
  const extensions=useMemo(()=>{
    const syntax=language==='python'?python():language==='c'||language==='cpp'?cpp():language==='java'?java():language==='javascript'||language==='typescript'?javascript({typescript:language==='typescript'}):language==='go'?go():language==='rust'?rust():language==='sql'?sql():null
    return [...(syntax?[syntax]:[]),EditorView.contentAttributes.of({'aria-label':ariaLabel})]
  },[language,ariaLabel])
  const dark=typeof document!=='undefined'&&document.documentElement.dataset.theme==='dark'
  if(!mounted)return <textarea className="other-code" aria-label={ariaLabel} value={value} readOnly={readOnly} onChange={event=>onChange?.(event.target.value)} style={{height}} spellCheck={false}/>
  return <div aria-label={ariaLabel}><CodeMirror key={language} value={value} onChange={onChange} extensions={extensions} height={height} theme={dark?githubDark:githubLight} editable={!readOnly} readOnly={readOnly} basicSetup={{lineNumbers:true,foldGutter:true,highlightActiveLine:!readOnly}}/></div>
}
