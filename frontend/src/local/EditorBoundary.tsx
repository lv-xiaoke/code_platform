import {Component,type ReactNode} from 'react'

export class EditorBoundary extends Component<{children:ReactNode;onClose:()=>void},{failed:boolean}> {
  state={failed:false}
  static getDerivedStateFromError(){return {failed:true}}
  render(){
    if(this.state.failed)return <section className="data-panel" role="alert"><h3>编辑器暂时无法载入</h3><p>当前笔记与代码草稿仍保留。恢复连接后重新打开页面，或先导出草稿。</p><button onClick={this.props.onClose}>返回题目</button></section>
    return this.props.children
  }
}
