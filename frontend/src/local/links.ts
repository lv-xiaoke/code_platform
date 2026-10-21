export function safeLink(value:string|null|undefined){
  try{const url=new URL(value??'');return ['https:','http:'].includes(url.protocol)?url.href:undefined}catch{return undefined}
}

export function problemDestination(value:string|null|undefined){
  const href=safeLink(value)
  if(!href)return undefined
  const host=new URL(href).hostname.toLowerCase()
  const official=['leetcode.cn','leetcode.com'].some(domain=>host===domain||host.endsWith('.'+domain))
  return {href,platform:official?'LeetCode':'原题网站'}
}
