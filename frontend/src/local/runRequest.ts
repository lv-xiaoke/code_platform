import type {AcmSuite} from './acmTypes'

export function prepareRun(source:string,mode:'custom'|'suite',savedSuite:AcmSuite){
  const submission={source_code:source,mode,...(mode==='custom'?{cases:[savedSuite.draft]}:{})}
  // Retrying a lost response must target exactly the same saved test set.
  // The server owns suite cases; this fingerprint is only the client retry key.
  const signature=JSON.stringify({submission,...(mode==='suite'?{suite_revision:savedSuite.revision,suite_cases:savedSuite.cases}:{})})
  return {submission,signature}
}
