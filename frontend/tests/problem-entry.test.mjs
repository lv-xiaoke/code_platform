import {test} from 'node:test'
import assert from 'node:assert/strict'
import {buildSync} from '../node_modules/esbuild/lib/main.js'
import {mkdtempSync,mkdirSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'

mkdirSync('runtime/tests',{recursive:true})
const output=path.resolve(mkdtempSync('runtime/tests/problem-entry-'),'render.cjs')
buildSync({stdin:{contents:`import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import {ProblemEntry} from './src/local/ProblemEntry'; import {PracticeBody} from './src/local/PracticeBody'; export function render(url){return renderToStaticMarkup(React.createElement(ProblemEntry,{displayId:'3',title:'无重复字符',url,onOpen:()=>{}}))} export function renderBody(saving){return renderToStaticMarkup(React.createElement(PracticeBody,{saving},React.createElement('textarea')))}`,resolveDir:path.resolve('frontend'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output,jsx:'automatic',logLevel:'silent'})
const {render,renderBody}=createRequire(import.meta.url)(output)

test('the local practice button and original source link are separate controls',()=>{
  const html=render('https://leetcode.cn/problems/test/')
  assert.match(html,/<button[^>]*aria-label="本地练习：3 无重复字符"/)
  assert.match(html,/<a[^>]*href="https:\/\/leetcode.cn\/problems\/test\/"[^>]*target="_blank"/)
  assert.match(html,/<\/button><a /)
})

test('missing or unsafe source URLs still provide local practice without an external link',()=>{
  for(const url of [null,'javascript:alert(1)','file:///data.txt']){
    const html=render(url)
    assert.match(html,/<button/)
    assert.doesNotMatch(html,/<a /)
    assert.match(html,/暂无原题链接/)
  }
})

test('saving makes the entire practice body inert so late keyboard edits cannot be lost on close',()=>{
  assert.match(renderBody(true),/inert=""/)
  assert.match(renderBody(true),/aria-busy="true"/)
  assert.doesNotMatch(renderBody(false),/inert=/)
})
