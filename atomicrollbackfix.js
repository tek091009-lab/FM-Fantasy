(()=>{
'use strict';
const VERSION='atomic-import-rollback-v4-preserve-failed-debug';
const DEBUG_DB='FMFantasyDiagnostics';
const DEBUG_STORE='failures';
const DEBUG_KEY='lastFailedImport';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
let lastCanonical=null,lastRestoreAt=0,reloadScheduled=false;
const debugEvents=[];
function safeClone(v){try{return clone(v)}catch(_e){try{return JSON.parse(JSON.stringify(v,(_k,x)=>typeof x==='bigint'?String(x):x))}catch(_e2){return String(v)}}}
function debugEvent(level,message,details){
  debugEvents.push({at:new Date().toISOString(),level:String(level??''),message:String(message??''),details:safeClone(details)});
  if(debugEvents.length>1200)debugEvents.splice(0,debugEvents.length-1200);
}
function installDebugTap(){
  let original=null;try{original=globalThis.fmDebugAdd}catch(_e){}
  if(typeof original!=='function'||original.__fmFailureDebugTap)return false;
  const wrapped=function(level,message,details,...rest){debugEvent(level,message,details);return original.call(this,level,message,details,...rest)};
  wrapped.__fmFailureDebugTap=true;wrapped.__fmFailureDebugOriginal=original;
  try{globalThis.fmDebugAdd=wrapped;return globalThis.fmDebugAdd===wrapped}catch(_e){return false}
}
function openDebugDb(){
  return new Promise((resolve,reject)=>{
    try{
      const r=indexedDB.open(DEBUG_DB,1);
      r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains(DEBUG_STORE))r.result.createObjectStore(DEBUG_STORE)};
      r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
    }catch(e){reject(e)}
  });
}
async function saveFailureDebug(payload,errorText){
  const world=(()=>{try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}})();
  const report={
    version:'failed-import-debug-v1',
    captured_at:new Date().toISOString(),
    error:String(errorText||''),
    page:String(location?.href||''),
    user_agent:String(navigator?.userAgent||''),
    import_mode:String(payload?.meta?.import_mode||window.__FM_IMPORT_MODE_ACTIVE||''),
    rejected_payload:safeClone(payload),
    rejected_meta:safeClone(payload?.meta||null),
    update_validation:safeClone(payload?.meta?.update_validation||null),
    weekly_match_detail_repair:safeClone(payload?.meta?.weekly_match_detail_repair||null),
    canonical_world:{id:world?.id||null,payload_version:world?.payload_version??world?.version??null,meta:safeClone(world?.payload?.meta||null)},
    captured_debug_events:safeClone(debugEvents),
    visible_debug_text:(()=>{try{return [...document.querySelectorAll('[id*=debug i],[class*=debug i],[id*=import i][class*=log i],[class*=import i][class*=log i]')].slice(0,20).map(el=>String(el.innerText||el.textContent||'').trim()).filter(Boolean).join('\n\n---\n\n').slice(0,250000)}catch(_e){return ''}})()
  };
  try{
    const db=await openDebugDb();
    await new Promise((resolve,reject)=>{const t=db.transaction(DEBUG_STORE,'readwrite');t.objectStore(DEBUG_STORE).put(report,DEBUG_KEY);t.oncomplete=()=>resolve();t.onerror=()=>reject(t.error);t.onabort=()=>reject(t.error)});
    try{sessionStorage.setItem('fmFantasyFailedImportDebugSaved',JSON.stringify({at:Date.now(),error:report.error,version:report.version}))}catch(_e){}
    return true;
  }catch(e){
    console.warn('Could not persist failed-import debug report',e);
    try{sessionStorage.setItem('fmFantasyFailedImportDebugFallback',JSON.stringify({...report,rejected_payload:undefined,captured_debug_events:report.captured_debug_events.slice(-300)}))}catch(_e){}
    return false;
  }
}
async function readFailureDebug(){
  try{const db=await openDebugDb();return await new Promise((resolve,reject)=>{const t=db.transaction(DEBUG_STORE,'readonly'),r=t.objectStore(DEBUG_STORE).get(DEBUG_KEY);r.onsuccess=()=>resolve(r.result||null);r.onerror=()=>reject(r.error)})}catch(_e){try{return JSON.parse(sessionStorage.getItem('fmFantasyFailedImportDebugFallback')||'null')}catch(_e2){return null}}
}
async function clearFailureDebug(){try{const db=await openDebugDb();await new Promise((resolve,reject)=>{const t=db.transaction(DEBUG_STORE,'readwrite');t.objectStore(DEBUG_STORE).delete(DEBUG_KEY);t.oncomplete=resolve;t.onerror=()=>reject(t.error)})}catch(_e){}try{sessionStorage.removeItem('fmFantasyFailedImportDebugSaved');sessionStorage.removeItem('fmFantasyFailedImportDebugFallback')}catch(_e){}}
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
  try{sessionStorage.setItem('fmFantasyFailedImportRollback',JSON.stringify({at:Date.now(),error:String(errorText||''),debug_saved:true}))}catch(_e){}
  setTimeout(()=>location.reload(),180);
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
  installDebugTap();
  const c=window.FMCloud;if(!c||c.__atomicImportRollbackV4||typeof c.publishWorld!=='function')return false;
  c.__atomicImportRollbackV4=true;
  const original=c.publishWorld.bind(c);
  c.publishWorld=async(payload,...args)=>{
    if(payload==null)return original(payload,...args);
    try{return await original(payload,...args)}
    catch(err){
      const errorText=String(err?.message||err);
      await saveFailureDebug(payload,errorText);
      await restoreCanonical({hardReload:true,errorText});
      try{if(typeof fmDebugAdd==='function')fmDebugAdd('warning','Rejected/failed import debug preserved; canonical world restored and clean runtime reload scheduled.',{version:VERSION,error:errorText})}catch(_e){}
      throw err;
    }
  };
  window.FMAtomicImportRollback={version:VERSION,restoreCanonical,saveFailureDebug,readFailureDebug,clearFailureDebug};
  return true;
}
window.FMAtomicImportRollback={version:VERSION,restoreCanonical,saveFailureDebug,readFailureDebug,clearFailureDebug};
window.addEventListener('fmcloudready',()=>setTimeout(install,0));let tries=0;const timer=setInterval(()=>{tries++;installDebugTap();if(install()||tries>50)clearInterval(timer)},200);
})();