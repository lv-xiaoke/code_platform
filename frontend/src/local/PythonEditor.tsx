import CodeMirror from '@uiw/react-codemirror'
import {python} from '@codemirror/lang-python'
import {EditorView} from '@codemirror/view'
import {githubDark,githubLight} from '@uiw/codemirror-theme-github'
import {useMemo} from 'react'

export default function PythonEditor({value,onChange,label,readOnly=false,height='300px'}:{value:string;onChange?:(value:string)=>void;label:string;readOnly?:boolean;height?:string}){
  const extensions=useMemo(()=>[python(),EditorView.contentAttributes.of({'aria-label':label})],[label])
  return <CodeMirror value={value} onChange={onChange} extensions={extensions} height={height} theme={document.documentElement.dataset.theme==='dark'?githubDark:githubLight} editable={!readOnly} readOnly={readOnly} basicSetup={{lineNumbers:true,foldGutter:true,highlightActiveLine:!readOnly}}/>
}
