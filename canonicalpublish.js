(()=>{
 'use strict';
 const VERSION='canonical-publish-v2-timeout-reconcile';
 const clone=v=>JSON.parse(JSON.stringify(v));
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 function replaceInPlace(target,source){
   if(!target||typeof target!=='object'||!source||typeof source!=='object')return source;
   for(const k of Object.keys(target))delete target[k];
   Object.assign(target,clone(source));
   return target;
 }
 function signature(payload){
   const m=payload?.meta||{};
   return {
     fingerprint:String(m.fingerprint||''),
     competition:String(m.competition_code||m.competition||''),
     snapshot:String(m.snapshot_date||''),
     completed:Number(m.completed_gameweek||0),
     latest:Number(m.latest_gameweek_with_result||0),
     players:Array.isArray(payload?.players)?payload.players.length:0,
     fixtures:Array.isArray(payload?.fixtures)?payload.fixtures.length:0
   };
 }
 function samePublish(expected,actual){
   if(!actual)return false;
   const a=signature(actual);
   if(expected.fingerprint&&a.fingerprint)return expected.fingerprint===a.fingerprint;
   return !!expected.competition&&expected.competition===a.competition&&
     expected.snapshot===a.snapshot&&expected.completed===a.completed&&expected.latest===a.latest&&
     expected.players===a.players&&expected.fixtures===a.fixtures;
 }
 function timeoutLike(err){const s=String(err?.message||err||'').toLowerCase();return /timeout|504|gateway|upstream|network|fetch/.test(s)}
 async function reconcilePublishedWorld(payload,err){
   if(!timeoutLike(err)||typeof window.FMCloud?.loadWorld!=='function')return null;
   const expected=signature(payload);
   for(const wait of [250,750,1500,2500,4000]){
     await sleep(wait);
     try{
       const canonical=await window.FMCloud.loadWorld();
       if(samePublish(expected,canonical)){
         console.warn('FM Fantasy publish response timed out, but the canonical world was committed successfully.',{version:VERSION,expected});
         try{if(typeof fmDebugAdd==='function')fmDebugAdd('warning','Publish response timed out but server commit was verified.',{version:VERSION,...expected})}catch(_e){}
         return canonical;
       }
     }catch(_e){}
   }
   return null;
 }
 async function install(){
   let original;try{original=typeof fmStoredSet==='function'?fmStoredSet:null}catch(_){original=null}
   if(!original||original.__fmCanonicalPublishWrapped)return false;
   const wrapped=async function(payload){
     if(!payload)return original(payload);
     if(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.()){
       let canonical=null;
       try{canonical=await window.FMCloud.publishWorld(payload)}
       catch(err){canonical=await reconcilePublishedWorld(payload,err);if(!canonical)throw err}
       if(!canonical)throw new Error('Server did not return the canonical FM world after publish.');
       replaceInPlace(payload,canonical);
       try{
         if(typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(payload);
         else {
           const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('FMFantasyStandalone',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('imports'))r.result.createObjectStore('imports')};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
           await new Promise((resolve,reject)=>{const t=db.transaction('imports','readwrite');t.objectStore('imports').put(payload,'championship');t.oncomplete=resolve;t.onerror=()=>reject(t.error)});
         }
       }catch(e){console.warn('Canonical FM world could not be mirrored to IndexedDB',e)}
       const w=window.FMCloud.getWorld?.();if(w)w.payload=payload;
       return payload;
     }
     return original(payload);
   };
   wrapped.__fmCanonicalPublishWrapped=true;
   wrapped.__fmCanonicalPublishOriginal=original;
   try{fmStoredSet=wrapped}catch(e){console.warn('Could not install canonical import publish wrapper',e);return false}
   window.FMCanonicalPublish={version:VERSION,replaceInPlace,signature,samePublish,reconcilePublishedWorld};
   return true;
 }
 let tries=0;const timer=setInterval(async()=>{tries++;if(await install()||tries>40)clearInterval(timer)},200);
 window.addEventListener('fmcloudready',()=>setTimeout(install,0));
})();