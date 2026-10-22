import type {ReactNode} from 'react'

export function PracticeBody({saving,children}:{saving:boolean;children:ReactNode}){
  // inert also blocks contenteditable CodeMirror input, unlike a disabled fieldset.
  return <div className="practice-body" aria-busy={saving} {...(saving?{inert:''}:{})}>{children}</div>
}
