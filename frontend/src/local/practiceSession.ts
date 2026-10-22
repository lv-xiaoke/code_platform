export async function flushPractice(saveNote:()=>Promise<boolean>,saveTests:(()=>Promise<boolean>)|null):Promise<boolean>{
  const results=await Promise.allSettled([Promise.resolve().then(saveNote),Promise.resolve().then(()=>saveTests?.()??true)])
  return results.every(result=>result.status==='fulfilled'&&result.value===true)
}
