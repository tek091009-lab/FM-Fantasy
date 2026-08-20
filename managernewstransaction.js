(()=>{
'use strict';
const VERSION='manager-news-transaction-v1-success-only-canonical-transfers';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const num=v=>Number(v||0)||0;
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const pid=p=>String(p?.pid??p?.player_id??p?.person_id??p?.eid??p?.id??'');
let pending=null;
function importActive(){try{return !!norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_){return false}}
function guardedTransferRows(payload){
 const events=arr(payload?.meta?.transfer_news_guard?.events),byId=new Map(arr(payload?.players).map(p=>[pid(p),p]).filter(([id])=>id));
 return events.map(e=>{const p=byId.get(String(e?.id??''))||null,newClub=String(e?.new_club||p?.club||'').trim(),oldClub=String(e?.old_club||'').trim();return {pid:String(e?.id??''),pos:p?.pos||null,club:newClub,name:String(e?.name||p?.name||'Player'),price:num(p?.price),value:'—',new_club:newClub,old_club:oldClub,date:e?.date||null}}).filter(x=>x.name&&x.new_club&&x.old_club);
}
function sanitize(st,payload){const out=clone(st||{});if(out.news&&typeof out.news==='object'&&!Array.isArray(out.news))out.news.transfers=guardedTransferRows(payload);return out}
function installQueue(){
 const c=window.FMCloud;if(!c||c.__managerNewsQueueV1||typeof c.queueManagerSave!=='function')return false;c.__managerNewsQueueV1=true;const original=c.queueManagerSave.bind(c);c.__managerNewsOriginalQueueV1=original;
 c.queueManagerSave=st=>{const snap=clone(st||{});if(importActive()){pending=snap;return}return original(sanitize(snap,c.getWorld?.()?.payload||null))};return true;
}
function installPublish(){
 const c=window.FMCloud;if(!c||!c.__registrationNewsV2||!c.__historicalBoundaryV12||!c.__atomicImportRollbackV4||c.__managerNewsPublishV1||typeof c.publishWorld!=='function')return false;c.__managerNewsPublishV1=true;const publish=c.publishWorld.bind(c),queue=c.__managerNewsOriginalQueueV1||c.queueManagerSave.bind(c);
 c.publishWorld=async(payload,...args)=>{if(payload==null)return publish(payload,...args);try{const result=await publish(payload,...args),canonical=c.getWorld?.()?.payload||result||payload;if(pending){const clean=sanitize(pending,canonical);pending=null;try{c.managerState=clone(clean)}catch(_){}queue(clean)}return result}catch(e){pending=null;throw e}};
 window.FMManagerNewsTransaction={version:VERSION,sanitize,guardedTransferRows};return true;
}
function install(){installQueue();return installPublish()}
window.FMManagerNewsTransaction={version:VERSION,sanitize,guardedTransferRows};window.addEventListener('fmcloudready',()=>setTimeout(install,0));let tries=0;const timer=setInterval(()=>{tries++;installQueue();if(installPublish()||tries>80)clearInterval(timer)},100);
})();