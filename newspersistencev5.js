(()=>{
'use strict';
const VERSION='news-persistence-v8-canonical-transfer-dom-authority';
const PREFIX='fmFantasyNewsSnapshotV4:';
const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
const SECTION_IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions'];
/* These two cards are derived deterministically from the canonical imported payload.
   Persist their model data, but never replay saved DOM over their canonical renderer. */
const CANONICAL_DOM_IDS=new Set(['newsTransfers','newsRegistrations']);
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase();
let captureUntil=0,captureReason='',captureQueued=false,restoring=false,sawImport=false,lastMode='',lastBoundary='',lastSavedAt=0,lastSavedQuality=0,lastRestoreAt=0,observer=null;

function worldRef(){try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}}
function payloadRef(){try{return worldRef()?.payload||null}catch(_e){return null}}
function stateRef(){try{return typeof state!=='undefined'?state:(window.state||null)}catch(_e){return window.state||null}}
function globalNewsRef(){try{if(Array.isArray(window.NEWS))return window.NEWS;if(typeof NEWS!=='undefined'&&Array.isArray(NEWS))return NEWS}catch(_e){}return null}
function importMode(){try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){return ''}}
function storageKey(){const w=worldRef(),id=String(w?.id||'local');return PREFIX+id}
function boundary(payload=payloadRef()){
 const m=payload?.meta||{};
 return [String(m.fingerprint||''),String(m.snapshot_date||''),String(m.completed_gameweek||''),String(m.played_results||''),String(arr(payload?.players).length)].join('|');
}
function markDatabaseActive(){
 if(!payloadRef())return false;
 try{localStorage.removeItem(CLEAR_KEY);sessionStorage.removeItem(CLEAR_KEY)}catch(_e){}
 try{window.FMNewsView?.markActive?.()}catch(_e){}
 return true;
}
function readLocal(){try{const raw=localStorage.getItem(storageKey());return raw?JSON.parse(raw):null}catch(_e){return null}}
function writeLocal(snap){if(!snap)return false;try{localStorage.setItem(storageKey(),JSON.stringify(snap));return true}catch(e){console.warn('[FM News persistence v8] local snapshot save failed',e);return false}}
function clearLocal(){try{localStorage.removeItem(storageKey())}catch(_e){};lastSavedAt=0;lastSavedQuality=0}
function compatible(snap,payload=payloadRef()){
 if(!snap||!payload)return false;
 const m=payload.meta||{},fp=String(m.fingerprint||''),sd=String(m.snapshot_date||'');
 if(snap.fingerprint&&fp&&String(snap.fingerprint)!==fp)return false;
 if(snap.snapshot_date&&sd&&String(snap.snapshot_date)!==sd)return false;
 if(!snap.fingerprint&&!snap.snapshot_date&&snap.boundary&&boundary(payload)&&String(snap.boundary)!==boundary(payload))return false;
 return true;
}
function fallbackName(p){return String(p?.display_name||p?.public_name||p?.name||p?.legal_name||'Player').trim()||'Player'}
function fmtDate(v){if(!v)return'';try{const d=new Date(String(v).length<=10?String(v)+'T12:00:00':v);return Number.isNaN(d.getTime())?String(v):d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}catch(_e){return String(v)}}
function deriveActiveStatuses(payload=payloadRef()){
 if(!payload)return {injuries:[],suspensions:[]};
 try{
  const t=window.FMAvailabilityTruth;
  if(t?.activeInjuries&&t?.activeSuspensions)return {injuries:clone(t.activeInjuries(payload)),suspensions:clone(t.activeSuspensions(payload))};
 }catch(_e){}
 const injuries=[],suspensions=[];
 for(const p of arr(payload.players)){
  const pid=String(p?.pid??p?.id??''),name=fallbackName(p),club=String(p?.club||''),pos=String(p?.pos||'');
  if(p?.injured===true||norm(p?.injury_status)==='injured'){
   const ret=p?.injury_return_date||p?.expected_return_date||p?.injury_expected_back||p?.injury_end_date||p?.injury_evidence?.expected_return||'';
   injuries.push({pid,name,club,pos,detail:`Injured${ret?` · expected back ${fmtDate(ret)}`:''}`});
  }
  if(p?.suspended===true||norm(p?.suspension_status)==='suspended'){
   const remaining=Math.max(Number(p?.suspension_remaining||0),Number(p?.suspension_games_remaining||0),Number(p?.ban_games_remaining||0),Number(p?.suspension_evidence_structural?.games_remaining||0));
   suspensions.push({pid,name,club,pos,detail:`Suspended${remaining?` · ${remaining} league match${remaining===1?'':'es'} remaining`:''}`});
  }
 }
 return {injuries,suspensions};
}
function ensureActiveStatuses(){
 const payload=payloadRef(),st=stateRef();if(!payload||!st)return null;
 const derived=deriveActiveStatuses(payload),current=st.activeStatuses&&typeof st.activeStatuses==='object'?st.activeStatuses:{};
 const next={...current,injuries:derived.injuries,suspensions:derived.suspensions};
 if(JSON.stringify(current.injuries||[])!==JSON.stringify(next.injuries)||JSON.stringify(current.suspensions||[])!==JSON.stringify(next.suspensions))st.activeStatuses=next;
 return clone(st.activeStatuses||next);
}
function captureDom(){
 const sections={};let count=0,meaningfulSections=0,rowCount=0,textLength=0;
 for(const id of SECTION_IDS){
  const el=document.getElementById(id);if(!el)continue;
  const clean=el.cloneNode(true);clean.querySelectorAll?.('.newsHead,.fmNewsCanonicalEmpty,.fmNewsClearedEmpty,input,button,[data-news-search]').forEach?.(n=>n.remove());
  const text=String(clean.textContent||'').replace(/\s+/g,' ').trim(),rows=clean.querySelectorAll?.('[data-news-text],.newsRegRow,.fmNewsTransferRow,.transfer,.injury,.suspension,.newsRow,.priceRow,.statusRow,tr')?.length||0;
  const cleared=el.dataset?.fmNewsCleared||'';const meaningful=cleared!=='1'&&(rows>0||text.length>=12);
  sections[id]={html:el.innerHTML,cleared};count++;if(meaningful)meaningfulSections++;rowCount+=rows;textLength+=text.length;
 }
 const stamp=document.getElementById('newsStamp');return {sections,stamp:stamp?.textContent||'',count,meaningfulSections,rowCount,textLength};
}
function modelCount(v,depth=0){if(v==null||depth>6)return 0;if(Array.isArray(v))return v.length+v.reduce((n,x)=>n+modelCount(x,depth+1),0);if(typeof v==='object')return Object.values(v).reduce((n,x)=>n+modelCount(x,depth+1),0);return 0}
function buildSnapshot(reason){
 const payload=payloadRef(),st=stateRef();if(!payload)return null;markDatabaseActive();
 const active=ensureActiveStatuses()||clone(st?.activeStatuses),stateNews=clone(st?.news),globalNews=clone(globalNewsRef()),dom=captureDom();
 const quality=(modelCount(stateNews)+modelCount(active)+modelCount(globalNews))*1000+(dom.meaningfulSections||0)*100+(dom.rowCount||0)*15+Math.min(200,Math.floor((dom.textLength||0)/10));
 const m=payload.meta||{};return {version:VERSION,boundary:boundary(payload),fingerprint:String(m.fingerprint||''),snapshot_date:String(m.snapshot_date||''),completed_gameweek:String(m.completed_gameweek||''),played_results:String(m.played_results||''),player_count:arr(payload.players).length,reason:String(reason||''),saved_at:new Date().toISOString(),quality,state_news:stateNews,active_statuses:active,global_news:globalNews,dom};
}
function saveCandidate(reason,force=false){
 if(restoring||(!force&&Date.now()>captureUntil))return false;
 const payload=payloadRef();if(!payload)return false;
 const snap=buildSnapshot(reason||captureReason);if(!snap||snap.quality<=0)return false;
 const existing=readLocal();if(existing&&compatible(existing,payload)&&Number(existing.quality||0)>snap.quality)return false;
 if(writeLocal(snap)){lastSavedAt=Date.now();lastSavedQuality=snap.quality;lastBoundary=boundary(payload);return true}return false;
}
function startCapture(reason,ms=30000){
 captureReason=String(reason||'FM import');captureUntil=Math.max(captureUntil,Date.now()+ms);markDatabaseActive();
 for(const delay of [0,60,150,300,600,1000,1600,2500,4000,6500,10000,15000,22000,29000])setTimeout(()=>saveCandidate(captureReason),delay);
}
function applyActiveStatuses(active){const st=stateRef();if(!st||active===undefined)return false;if(JSON.stringify(st.activeStatuses)!==JSON.stringify(active)){st.activeStatuses=clone(active);return true}return false}
function applyStateNews(news){const st=stateRef();if(!st||news===undefined)return false;if(JSON.stringify(st.news)!==JSON.stringify(news)){st.news=clone(news);return true}return false}
function applyGlobalNews(news){if(news===undefined)return false;const cur=globalNewsRef();if(cur){if(JSON.stringify(cur)===JSON.stringify(news))return false;cur.length=0;cur.push(...clone(arr(news)));return true}try{window.NEWS=clone(arr(news));return true}catch(_e){return false}}
function restoreDom(dom){
 if(!dom?.sections)return false;let changed=false;
 for(const [id,s] of Object.entries(dom.sections)){
  /* V41: canonical transfer/registration cards are never restored from saved HTML.
     Their canonical payload renderer is the single DOM authority. */
  if(CANONICAL_DOM_IDS.has(id))continue;
  const el=document.getElementById(id);if(!el||typeof s?.html!=='string')continue;
  if(el.innerHTML!==s.html){el.innerHTML=s.html;changed=true}
  if(el.dataset){if(s.cleared)el.dataset.fmNewsCleared=s.cleared;else delete el.dataset.fmNewsCleared}
 }
 const stamp=document.getElementById('newsStamp');if(stamp&&dom.stamp&&stamp.textContent!==dom.stamp){stamp.textContent=dom.stamp;changed=true}
 try{window.FMNewsClubFilter?.install?.(document.getElementById('newsRegistrations'))}catch(_e){}
 return changed;
}
function nativeRender(){try{if(typeof renderNews==='function'){renderNews();return true}if(typeof window.renderNews==='function'){window.renderNews();return true}if(typeof renderAll==='function'){renderAll();return true}if(typeof window.renderAll==='function'){window.renderAll();return true}}catch(e){console.warn('[FM News persistence v8] native News render failed',e)}return false}
function stabiliseCanonicalNews(){try{window.FMRegistrationNewsGuard?.refresh?.();window.FMNewsTransferStabilityV40?.stabilise?.()}catch(_e){}}
function restore(reason='refresh restore'){
 if(restoring||importMode())return false;
 const payload=payloadRef();if(!payload)return false;markDatabaseActive();
 const snap=readLocal();
 if(!snap||Number(snap.quality||0)<=0||!compatible(snap,payload))return recoverFromPayload(reason);
 restoring=true;
 try{
  applyActiveStatuses(snap.active_statuses);applyStateNews(snap.state_news);applyGlobalNews(snap.global_news);nativeRender();
  stabiliseCanonicalNews();
  const reapply=()=>{if(!importMode()){markDatabaseActive();restoreDom(snap.dom);stabiliseCanonicalNews()}};
  reapply();for(const ms of [40,120,300,800,1800,3500,7000])setTimeout(reapply,ms);
  lastRestoreAt=Date.now();return true;
 }finally{restoring=false}
}
function recoverFromPayload(reason='payload recovery'){
 if(restoring||importMode())return false;const payload=payloadRef(),st=stateRef();if(!payload||!st)return false;markDatabaseActive();
 restoring=true;try{const active=ensureActiveStatuses();nativeRender();stabiliseCanonicalNews();const has=!!(active&&(arr(active.injuries).length||arr(active.suspensions).length));if(has)setTimeout(()=>saveCandidate(reason,true),120);lastRestoreAt=Date.now();return has}finally{restoring=false}
}
function scheduleRestore(reason){for(const ms of [0,80,180,350,700,1200,2200,4000,7000,10000])setTimeout(()=>restore(reason),ms)}
function installObserver(){
 if(observer)return;observer=new MutationObserver(muts=>{
  if(restoring)return;
  if(importMode()||Date.now()<=captureUntil){if(!captureQueued){captureQueued=true;setTimeout(()=>{captureQueued=false;saveCandidate('import News mutation')},70)}return}
  const touchesNews=muts.some(m=>[...m.addedNodes,...m.removedNodes].some(n=>n?.nodeType===1&&(SECTION_IDS.includes(n.id)||n.querySelector?.(SECTION_IDS.map(id=>'#'+id).join(',')))));
  if(touchesNews&&readLocal())setTimeout(()=>restore('late News render guard'),80);
 });observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
}
window.FMNewsPersistence={version:VERSION,readLocal,clearLocal,restore,recoverFromPayload,startCapture,saveCandidate,deriveActiveStatuses,ensureActiveStatuses,boundary,compatible,markDatabaseActive,restoreDom,canonicalDomIds:[...CANONICAL_DOM_IDS],status:()=>({version:VERSION,importMode:importMode(),captureWindow:Math.max(0,captureUntil-Date.now()),captureReason,lastSavedAt,lastSavedQuality,lastRestoreAt,hasLocal:!!readLocal(),localQuality:Number(readLocal()?.quality||0),payloadReady:!!payloadRef(),boundary:boundary()})};
installObserver();
window.addEventListener('fmcanonicalpublished',()=>{startCapture('fmcanonicalpublished');setTimeout(()=>saveCandidate('canonical publish',true),100)});
window.addEventListener('fmworldloaded',()=>scheduleRestore('world loaded'));
window.addEventListener('fmcloudready',()=>scheduleRestore('cloud ready'));
window.addEventListener('focus',()=>setTimeout(()=>restore('focus'),100));
document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(()=>restore('visibility'),100)});
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=norm(b.textContent||b.dataset?.nav||b.getAttribute('data-page')||'');if(s.includes('news')){setTimeout(()=>restore('News navigation'),40);setTimeout(()=>restore('News navigation'),250)}},true);
let tries=0;const timer=setInterval(()=>{
 tries++;const mode=importMode(),payload=payloadRef(),b=boundary(payload);
 if(payload)markDatabaseActive();
 if(mode){if(!sawImport||mode!==lastMode){sawImport=true;lastMode=mode;startCapture(`import observed: ${mode}`)}if(tries%4===0)saveCandidate('import active')}
 else if(sawImport){sawImport=false;lastMode='';startCapture('import completed');setTimeout(()=>saveCandidate('import completed',true),100)}
 else if(payload&&!lastBoundary){lastBoundary=b;restore('initial payload')}
 else if(payload&&b&&lastBoundary&&b!==lastBoundary){lastBoundary=b;startCapture('imported payload boundary changed');setTimeout(()=>saveCandidate('payload boundary changed',true),120)}
 else if(payload&&tries%20===0)restore('steady-state guard');
 if(tries>1800)clearInterval(timer);
},100);
})();
