(()=>{
 'use strict';
 const VERSION='cloud-apply-v2-canonical-world-beats-stale-clear-flag';
 let done=false,timer=null,tries=0;
 const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
 const wasCleared=()=>{try{return localStorage.getItem(CLEAR_KEY)==='1'||sessionStorage.getItem(CLEAR_KEY)==='1'}catch(_){return false}};
 const markActive=()=>{try{localStorage.removeItem(CLEAR_KEY);sessionStorage.removeItem(CLEAR_KEY)}catch(_){}};
 async function applyCloudWorld(){
   if(done||!window.FMCloud?.ready?.())return;
   try{
     // The canonical shared world is authoritative. A local clear marker is only a UI hint
     // while the canonical world is genuinely empty; it must never block a later successful import.
     const payload=await window.FMCloud.loadWorld();
     if(!payload)return;
     markActive();
     try{window.FMNewsView?.markActive?.()}catch(_e){}
     if(typeof window.fmStoredSetLocalOnly==='function')await window.fmStoredSetLocalOnly(payload);
     if(typeof window.applyImportedPayload==='function')window.applyImportedPayload(payload,'cloud');
     else if(typeof window.loadServerImportState==='function')await window.loadServerImportState();
     if(window.FMCloud.managerState&&typeof window.state==='object'){
       try{Object.assign(window.state,window.FMCloud.managerState)}catch(_e){}
     }
     if(typeof window.renderAll==='function')window.renderAll();
     try{window.FMNewsPersistence?.recoverFromPayload?.('cloud world applied')}catch(_e){}
     try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}
     done=true;
     if(timer)clearInterval(timer);
     console.info('FM Fantasy shared world applied',{version:VERSION,players:payload.players?.length||0,fixtures:payload.fixtures?.length||0,staleClearFlagRemoved:!wasCleared()});
   }catch(e){console.error('FM Fantasy shared world apply failed',e)}
 }
 window.FMCloudApply={version:VERSION,applyCloudWorld,markActive,wasCleared};
 window.addEventListener('fmcloudready',()=>setTimeout(applyCloudWorld,0));
 timer=setInterval(()=>{tries++;applyCloudWorld();if(done||tries>80)clearInterval(timer)},500);
 setTimeout(applyCloudWorld,50);
})();
