(()=>{
'use strict';
const VERSION='news-world-recovery-v1-canonical-payload-authority';
const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
let loading=false,applied=false,attempts=0;
function payloadRef(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function markActive(){
 try{localStorage.removeItem(CLEAR_KEY);sessionStorage.removeItem(CLEAR_KEY)}catch(_e){}
 try{window.FMNewsView?.markActive?.()}catch(_e){}
 try{window.FMNewsPersistence?.markDatabaseActive?.()}catch(_e){}
}
function restoreNews(reason){
 try{if(window.FMNewsPersistence?.restore?.(reason))return true}catch(_e){}
 try{return !!window.FMNewsPersistence?.recoverFromPayload?.(reason)}catch(_e){return false}
}
async function applyCanonicalPayload(reason='canonical recovery'){
 if(loading)return false;
 const existing=payloadRef();
 if(existing){markActive();restoreNews(reason);return true}
 if(!window.FMCloud?.ready?.()||typeof window.FMCloud.loadWorld!=='function')return false;
 loading=true;
 try{
  // Deliberately ignore the local "database cleared" flag here. The server world is the
  // authority: if a later import exists, a stale browser marker must not hide it.
  const payload=await window.FMCloud.loadWorld(true);
  if(!payload)return false;
  const world=window.FMCloud.getWorld?.();if(world)world.payload=payload;
  markActive();
  try{if(typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(payload)}catch(e){console.warn('[FM News world recovery] local mirror failed',e)}
  try{if(typeof applyImportedPayload==='function')applyImportedPayload(payload,'news-recovery');else if(typeof window.applyImportedPayload==='function')window.applyImportedPayload(payload,'news-recovery')}catch(e){console.warn('[FM News world recovery] payload apply failed',e)}
  try{if(typeof renderAll==='function')renderAll();else if(typeof window.renderAll==='function')window.renderAll()}catch(_e){}
  restoreNews(reason);
  try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}
  applied=true;return true;
 }catch(e){console.warn('[FM News world recovery] canonical world load failed',e);return false}
 finally{loading=false}
}
window.FMNewsWorldRecovery={version:VERSION,applyCanonicalPayload,markActive,restoreNews,status:()=>({version:VERSION,loading,applied,attempts,payloadReady:!!payloadRef()})};
window.addEventListener('fmcloudready',()=>{setTimeout(()=>applyCanonicalPayload('cloud ready recovery'),0);setTimeout(()=>applyCanonicalPayload('cloud ready recovery'),500)});
window.addEventListener('fmworldloaded',()=>{markActive();setTimeout(()=>restoreNews('world loaded recovery'),0)});
window.addEventListener('fmcanonicalpublished',()=>{markActive();setTimeout(()=>restoreNews('canonical published recovery'),50)});
const timer=setInterval(()=>{attempts++;applyCanonicalPayload('startup recovery');if((applied&&payloadRef())||attempts>80)clearInterval(timer)},250);
setTimeout(()=>applyCanonicalPayload('startup recovery'),50);
})();
