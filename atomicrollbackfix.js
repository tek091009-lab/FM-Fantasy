(()=>{
'use strict';
const VERSION='atomic-import-rollback-v3-hard-runtime-reset';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
let lastCanonical=null,lastRestoreAt=0,reloadScheduled=false;
async function writeLocal(payload){
  if(!payload)return;
  try{
    if(typeof fmStoredSetLocalOnly==='function'){await fmStoredSetLocalOnly(payload);return;}
    const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('FMFantasyStandalone',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('imports'))r.result.createObjectStore('imports')};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
    await new Promise((resolve,reject)=>{const t=db.transaction('imports','readwrite');t.objectStore('imports').put(payload,'championship');t.oncomplete=resolve;t.onerror=()=>reject(t.error)});
  }catch(e){console.warn('Atomic rollback could not mirror canonical world locally',e)}
}
function scheduleHardReload(errorText){
  if(reloadScheduled)return;
  reloadScheduled=true;
  try{sessionStorage.setItem('fmFantasyFailedImportRollback',JSON.stringify({at:Date.now(),error:String(errorText||'')}))}catch(_e){}
  setTimeout(()=>location.reload(),80);
}
async function restoreCanonical(options={}){
  const hardReload=!!options.hardReload,errorText=String(options.errorText||'');
  let canonical=null;
  if(lastCanonical&&Date.now()-lastRestoreAt<2500){canonical=clone(lastCanonical)}
  if(!canonical){
    try{if(typeof window.FMCloud?.loadWorld==='function')canonical=await window.FMCloud.loadWorld(true)}catch(e){console.warn('Atomic rollback could not reload canonical server world',e)}
    if(!canonical){try{canonical=clone(window.FMCloud?.getWorld?.()?.payload||null)}catch(_e){}}
    if(canonical){lastCanonical=clone(canonical);lastRestoreAt=Date.now()}
  }
  if(!canonical){if(hardReload)scheduleHardReload(errorText);return null}
  await writeLocal(canonical);
  try{const w=window.FMCloud?.getWorld?.();if(w)w.payload=canonical}catch(_e){}
  if(hardReload){scheduleHardReload(errorText);return canonical}
  try{if(typeof applyImportedPayload==='function')applyImportedPayload(canonical,'load')}catch(e){console.warn('Atomic rollback could not re-render canonical world',e)}
  try{if(typeof fmProcessCompletedGameweeks==='function')fmProcessCompletedGameweeks()}catch(_e){}
  try{if(typeof renderAll==='function')renderAll()}catch(_e){}
  return canonical;
}
function install(){
  const c=window.FMCloud;if(!c||c.__atomicImportRollbackV3||typeof c.publishWorld!=='function')return false;
  c.__atomicImportRollbackV3=true;
  const original=c.publishWorld.bind(c);
  c.publishWorld=async(payload,...args)=>{
    if(payload==null)return original(payload,...args);
    try{return await original(payload,...args)}
    catch(err){
      const errorText=String(err?.message||err);
      await restoreCanonical({hardReload:true,errorText});
      try{if(typeof fmDebugAdd==='function')fmDebugAdd('warning','Rejected/failed import restored canonical world and scheduled a clean runtime reload.',{version:VERSION,error:errorText})}catch(_e){}
      throw err;
    }
  };
  window.FMAtomicImportRollback={version:VERSION,restoreCanonical};
  return true;
}
window.addEventListener('fmcloudready',()=>setTimeout(install,0));let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>50)clearInterval(timer)},200);
})();