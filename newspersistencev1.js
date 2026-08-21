(()=>{
'use strict';
const VERSION='news-persistence-v1-import-snapshot-only';
const PREFIX='fmFantasyNewsSnapshotV1:';
const SECTION_IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions'];
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase();
let queueInstalled=false,storeInstalled=false,restoring=false,committed=null,pendingImport=null;

function stateRef(){try{return typeof state!=='undefined'?state:null}catch(_e){return null}}
function worldRef(){try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}}
function payloadRef(){try{return worldRef()?.payload||null}catch(_e){return null}}
function importMode(){try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){return ''}}
function key(){const id=String(worldRef()?.id||'');return id?PREFIX+id:''}
function signature(payload=payloadRef()){
 const m=payload?.meta||{},w=worldRef()||{};
 return [String(m.fingerprint||''),String(m.snapshot_date||''),String(m.completed_gameweek||''),String(m.played_results||''),String(arr(payload?.players).length),String(w.payload_version||'')].join('|');
}
function readLocal(){const k=key();if(!k)return null;try{const raw=localStorage.getItem(k);return raw?JSON.parse(raw):null}catch(_e){return null}}
function writeLocal(snap){const k=key();if(!k||!snap)return;try{localStorage.setItem(k,JSON.stringify(snap))}catch(e){console.warn('[FM News persistence] local snapshot save failed',e)}}
function clearLocal(){const k=key();if(k)try{localStorage.removeItem(k)}catch(_e){};committed=null;pendingImport=null}
function captureDom(){
 const sections={};let count=0;
 for(const id of SECTION_IDS){const el=document.getElementById(id);if(!el)continue;sections[id]={html:el.innerHTML,cleared:el.dataset?.fmNewsCleared||''};count++}
 const stamp=document.getElementById('newsStamp');
 return {sections,stamp:stamp?.textContent||'',count};
}
function captureStateNews(){const st=stateRef();return clone(st?.news)}
function canonicalSnapshot(payload=payloadRef()){
 const x=payload?.meta?.news_snapshot_v1;
 if(!x||typeof x!=='object')return null;
 return {version:String(x.version||VERSION),signature:String(x.signature||''),snapshot_date:String(x.snapshot_date||payload?.meta?.snapshot_date||''),fingerprint:String(x.fingerprint||payload?.meta?.fingerprint||''),import_mode:String(x.import_mode||''),state_news:clone(x.state_news),dom:null};
}
function compatible(snap,payload=payloadRef()){
 if(!snap||!payload)return false;
 const fp=String(payload?.meta?.fingerprint||''),sd=String(payload?.meta?.snapshot_date||'');
 if(snap.fingerprint&&fp&&String(snap.fingerprint)!==fp)return false;
 if(snap.snapshot_date&&sd&&String(snap.snapshot_date)!==sd)return false;
 return true;
}
function chooseSnapshot(){
 const payload=payloadRef(),local=readLocal(),canon=canonicalSnapshot(payload);
 if(local&&compatible(local,payload))return local;
 if(canon&&compatible(canon,payload))return canon;
 return null;
}
function restoreDom(dom){
 if(!dom?.sections)return false;let changed=false;
 for(const [id,s] of Object.entries(dom.sections)){const el=document.getElementById(id);if(!el||typeof s?.html!=='string')continue;if(el.innerHTML!==s.html){el.innerHTML=s.html;changed=true}if(el.dataset){if(s.cleared)el.dataset.fmNewsCleared=s.cleared;else delete el.dataset.fmNewsCleared}}
 const stamp=document.getElementById('newsStamp');if(stamp&&dom.stamp&&stamp.textContent!==dom.stamp){stamp.textContent=dom.stamp;changed=true}
 try{window.FMNewsClubFilter?.install?.(document.getElementById('newsRegistrations'))}catch(_e){}
 return changed;
}
function applyStateNews(news){
 if(news===undefined)return false;let changed=false;
 const st=stateRef();if(st&&JSON.stringify(st.news)!==JSON.stringify(news)){st.news=clone(news);changed=true}
 try{if(window.FMCloud?.managerState&&JSON.stringify(window.FMCloud.managerState.news)!==JSON.stringify(news)){window.FMCloud.managerState.news=clone(news);changed=true}}catch(_e){}
 return changed;
}
function restore(){
 if(restoring)return false;
 if(!payloadRef()){clearLocal();return false}
 const snap=chooseSnapshot();if(!snap)return false;
 committed=snap;restoring=true;
 try{
  const stateChanged=applyStateNews(snap.state_news);
  if(stateChanged)try{if(typeof renderAll==='function')renderAll()}catch(_e){}
  if(snap.dom)restoreDom(snap.dom);
  try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}
  return true;
 }finally{restoring=false}
}
function persistDomForCommitted(){
 if(!committed)return;
 const dom=captureDom();if(!dom.count)return;
 committed={...committed,dom};writeLocal(committed);
}
function makeImportSnapshot(payload,mode){
 const stNews=captureStateNews();
 return {version:VERSION,signature:signature(payload),snapshot_date:String(payload?.meta?.snapshot_date||''),fingerprint:String(payload?.meta?.fingerprint||''),import_mode:mode,state_news:clone(stNews),dom:null};
}
function sealIntoPayload(payload,mode){
 if(!payload||!mode)return null;
 payload.meta=payload.meta||{};
 const snap=makeImportSnapshot(payload,mode);
 payload.meta.news_snapshot_v1={version:VERSION,signature:snap.signature,snapshot_date:snap.snapshot_date,fingerprint:snap.fingerprint,import_mode:mode,state_news:clone(snap.state_news)};
 pendingImport=snap;
 return snap;
}
function installStoreWrapper(){
 let fn;try{fn=typeof fmStoredSet==='function'?fmStoredSet:null}catch(_e){fn=null}
 if(!fn||!fn.__fmCanonicalPublishWrapped||fn.__fmNewsPersistenceWrapped)return false;
 const original=fn;
 const wrapped=async function(payload){
  const mode=importMode();
  if(payload==null){clearLocal();return original(payload)}
  const snap=mode?sealIntoPayload(payload,mode):null;
  const result=await original(payload);
  if(snap){
   const canonical=result||payload,canon=canonicalSnapshot(canonical);
   committed=canon&&compatible(canon,canonical)?{...snap,...canon}:snap;
   writeLocal(committed);
   for(const ms of [0,120,350,800,1600,3000])setTimeout(()=>{persistDomForCommitted();restore()},ms);
  }
  pendingImport=null;
  return result;
 };
 wrapped.__fmNewsPersistenceWrapped=true;wrapped.__fmNewsPersistenceOriginal=original;
 try{fmStoredSet=wrapped;storeInstalled=true;return true}catch(e){console.warn('[FM News persistence] could not wrap import store',e);return false}
}
function installQueueGuard(){
 const c=window.FMCloud;if(!c||typeof c.queueManagerSave!=='function'||c.__newsPersistenceQueueV1)return false;
 if(!c.__managerNewsQueueV2)return false;
 c.__newsPersistenceQueueV1=true;
 const original=c.queueManagerSave.bind(c);
 c.queueManagerSave=st=>{
  const snap=clone(st||{}),mode=importMode();
  if(!mode){const keep=committed||chooseSnapshot();if(keep&&keep.state_news!==undefined)snap.news=clone(keep.state_news)}
  return original(snap);
 };
 queueInstalled=true;return true;
}
function scheduleRestore(){for(const ms of [0,80,250,700,1500])setTimeout(restore,ms)}
window.FMNewsPersistence={version:VERSION,restore,readLocal,chooseSnapshot,captureDom,captureStateNews,clearLocal,status:()=>({version:VERSION,queueInstalled,storeInstalled,hasCommitted:!!committed,local:readLocal(),canonical:canonicalSnapshot()})};
window.addEventListener('fmcloudready',()=>{installQueueGuard();installStoreWrapper();scheduleRestore()});
window.addEventListener('fmworldloaded',scheduleRestore);
window.addEventListener('focus',scheduleRestore);
window.addEventListener('fmcanonicalpublished',()=>{if(pendingImport){committed=pendingImport;writeLocal(committed);for(const ms of [50,250,750,1500])setTimeout(persistDomForCommitted,ms)}});
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=norm(b.textContent||b.dataset?.nav||b.getAttribute('data-page')||'');if(s.includes('news'))scheduleRestore()},true);
let tries=0;const timer=setInterval(()=>{tries++;installQueueGuard();installStoreWrapper();if(payloadRef()&&!importMode())restore();if((queueInstalled&&storeInstalled)||tries>180)clearInterval(timer)},100);
})();
