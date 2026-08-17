(()=>{
 'use strict';
 const VERSION='canonical-publish-v1';
 const clone=v=>JSON.parse(JSON.stringify(v));
 function replaceInPlace(target,source){
   if(!target||typeof target!=='object'||!source||typeof source!=='object')return source;
   for(const k of Object.keys(target))delete target[k];
   Object.assign(target,clone(source));
   return target;
 }
 async function install(){
   let original;try{original=typeof fmStoredSet==='function'?fmStoredSet:null}catch(_){original=null}
   if(!original||original.__fmCanonicalPublishWrapped)return false;
   const wrapped=async function(payload){
     if(!payload)return original(payload);
     if(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.()){
       const canonical=await window.FMCloud.publishWorld(payload);
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
   window.FMCanonicalPublish={version:VERSION,replaceInPlace};
   return true;
 }
 let tries=0;const timer=setInterval(async()=>{tries++;if(await install()||tries>40)clearInterval(timer)},200);
 window.addEventListener('fmcloudready',()=>setTimeout(install,0));
})();