import {test} from 'node:test'
import assert from 'node:assert/strict'
import {problemDestination} from '../src/local/links.ts'
import {catalogParams,changeFilter,EMPTY_FILTERS} from '../src/local/catalogFilters.ts'

test('company changes clear a department belonging to the previous company',()=>{
  assert.deepEqual(changeFilter({...EMPTY_FILTERS,company:'1',department:'2',job:'3'},'company','9'),
    {...EMPTY_FILTERS,company:'9',department:'',job:'3'})
})
test('all chosen filters including recent activity reach the catalog API',()=>{
  const params=catalogParams({...EMPTY_FILTERS,search:'树',company:'1',department:'2',job:'3',tag:'4',difficulty:'2',recent_days:'90',ordering:'-time'},2,'mine','todo')
  assert.deepEqual(Object.fromEntries(params),{page:'2',page_size:'20',source:'mine',search:'树',company:'1',department:'2',job:'3',tag:'4',difficulty:'2',recent_days:'90',ordering:'-time',completion:'todo'})
})
test('favorite view sends a favorite filter without a completion restriction',()=>{
  const params=catalogParams(EMPTY_FILTERS,1,'','favorites')
  assert.equal(params.get('favorite'),'true')
  assert.equal(params.has('completion'),false)
  assert.equal(params.has('source'),false)
})
test('official LeetCode links and external supplemental links are labeled accurately',()=>{
  assert.deepEqual(problemDestination('https://leetcode.cn/problems/two-sum/'),{href:'https://leetcode.cn/problems/two-sum/',platform:'LeetCode'})
  assert.equal(problemDestination('https://www.leetcode.com/problems/two-sum/').platform,'LeetCode')
  assert.equal(problemDestination('https://example.com/leetcode.cn/').platform,'原题网站')
  assert.equal(problemDestination('https://leetcode.cn.example.com/').platform,'原题网站')
})
test('missing and unsafe URLs never create a guessed problem link',()=>{
  for(const input of [null,undefined,'','not a url','javascript:alert(1)','file:///D:/data.txt','data:text/html,hello']){
    assert.equal(problemDestination(input),undefined)
  }
})
