(()=>{
'use strict';
const VERSION='news-persistence-v6-import-snapshot-authority';
const PREFIX='fmFantasyNewsSnapshotV3:';
const SECTION_IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions'];
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase();
let captureUntil=0,captureReason='',captureQueued=false,restoring=false,observer=null,sawImport=false,lastMode='',lastSavedAt=0,lastSavedQuality=0,lastRestoreAt=0;

function worldRef(){try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}}
function payloadRef(){try{return worldRef()?.payload||null}catch(_e){return null}}
function stateRef(){try{return typeof state!=='undefined'?state:null}catch(_e){return null}}
function globalNewsRef(){try{if(Array.isArray(window.NEWS))return window.NEWS;if(typeof NEWS!=='undefined'&&Array.isArray(NEWS))return NEWS}catch(_e){}return null}
function importMode(){try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){return ''}}
function key(){const id=String(worldRef()?.id||'');return id?PREFIX+id:''}
function signature(payload=payloadRef()){
 const m=payload?.meta||{};
 // Refresh/load mechanics such as payload_version are intentionally excluded. News identity
 // is tied only to the imported FM database boundary.
 return [String(m.fingerprint||''),String(m.snapshot_date||''),String(m.completed_gameweek||''),String(m.played_results||''),String(arr(payload?.players).length)].join('|');
}
function readLocal(){const k=key();if(!k)return null;try{const raw=localStorage.getItem(k);return raw?JSON.parse(raw):null}catch(_e){return null}}
function writeLocal(snap){const k=key();if(!k||!snap)return false;try{localStorage.setItem(k,JSON.stringify(snap));return true}catch(e){console.warn('[FM News persistence v6] local snapshot save failed',e);return false}}
function clearLocal(){const k=key();if(k)try{localStorage.removeItem(k)}catch(_e){};lastSavedAt=0;lastSavedQuality=0}
function captureStateNews(){const st=stateRef();return clone(st?.news)}
function captureGlobalNews(){const n=globalNewsRef();return n?clone(n):undefined}
function modelItemCount(v,depth=0){
 if(v==null||depth>6)return 0;
 if(Array.isArray(v))return v.length+v.reduce((n,x)=>n+modelItemCount(x,depth+1),0);
 if(typeof v==='object')return Object.values(v).reduce((n,x)=>n+modelItemCount(x,depth+1),0);
 return 0;
}
function sectionSnapshot(el){
 if(!el)return null;
 const clean=el.cloneNode(true);
 clean.querySelectorAll('.newsHead,.fmNewsCanonicalEmpty,.fmNewsClearedEmpty,input,button,[data-news-search]').forEach(n=>n.remove());
 const text=String(clean.textContent||'').replace(/\s+/g,' ').trim();
 const rowCount=clean.querySelectorAll('[data-news-text],.newsRegRow,.fmNewsTransferRow,.transfer,.injury,.suspension,.newsRow,.priceRow,.statusRow,tr').length;
 const cleared=el.dataset?.fmNewsCleared||'';
 const meaningful=cleared!=='1'&&(rowCount>0||text.length>=12);
 return {html:el.innerHTML,cleared,textLength:text.length,rowCount,meaningful};
}
function captureDom(){
 const sections={};let meaningfulSections=0,rowCount=0,textLength=0,count=0;
 for(const id of SECTION_IDS){
  const el=document.getElementById(id);if(!el)continue;
  const snap=sectionSnapshot(el);if(!snap)continue;
  sections[id]={html:snap.html,cleared:snap.cleared};count++;
  if(snap.meaningful)meaningfulSections++;
  rowCount+=snap.rowCount;textLength+=snap.textLength;
 }
 const stamp=document.getElementById('newsStamp');
 return {sections,stamp:stamp?.textContent||'',count,meaningfulSections,rowCount,textLength};
}
function qualityOfParts(stateNews,globalNews,dom){
 const model=modelItemCount(stateNews)+modelItemCount(globalNews);
 const domScore=(dom?.meaningfulSections||0)*100+(dom?.rowCount||0)*15+Math.min(200,Math.floor((dom?.textLength||0)/10));
 return model*1000+domScore;
}
function buildSnapshot(reason){
 const payload=payloadRef();if(!payload)return null;
 const stateNews=captureStateNews(),globalNews=captureGlobalNews(),dom=captureDom();
 const quality=qualityOfParts(stateNews,globalNews,dom);
 return {version:VERSION,signature:signature(payload),fingerprint:String(payload?.meta?.fingerprint||''),snapshot_date:String(payload?.meta?.snapshot_date||''),completed_gameweek:String(payload?.meta?.completed_gameweek||''),played_results:String(payload?.meta?.played_results||''),player_count:arr(payload?.players).length,reason:String(reason||''),saved_at:new Date().toISOString(),quality,state_news:stateNews,global_news:globalNews,dom};
}
function compatible(snap,payload=payloadRef()){
 if(!snap||!payload)return false;
 const fp=String(payload?.meta?.fingerprint||''),sd=String(payload?.meta?.snapshot_date||'');
 if(snap.fingerprint&&fp&&String(snap.fingerprint)!==fp)return false;
 if(snap.snapshot_date&&sd&&String(snap.snapshot_date)!==sd)return false;
 const sig=signature(payload);return !snap.signature||!sig||String(snap.signature)===sig;
}
function armed(){return Date.now()<=captureUntil}
function saveCandidate(reason){
 // Saving is passive/read-only and is therefore allowed while the import flag is still active.
 // This is essential because the app can render final News before __FM_IMPORT_MODE_ACTIVE clears.
 if(restoring||!armed())return false;
 const payload=payloadRef();if(!payload)return false;
 const snap=buildSnapshot(reason||captureReason);if(!snap||snap.quality<=0)return false;
 const existing=readLocal();
 if(existing&&compatible(existing,payload)&&Number(existing.quality||0)>snap.quality)return false;
 if(writeLocal(snap)){lastSavedAt=Date.now();lastSavedQuality=snap.quality;return true}
 return false;
}
function queueCapture(reason){
 if(!armed()||restoring||captureQueued)return;
 captureQueued=true;setTimeout(()=>{captureQueued=false;saveCandidate(reason)},60);
}
function startCapture(reason,ms=180000){
 captureReason=String(reason||'FM import');captureUntil=Math.max(captureUntil,Date.now()+ms);
 for(const delay of [0,80,200,400,700,1100,1700,2500,4000,6500,9000,13000,18000,24000,32000,45000,60000,90000,120000,150000,179000])setTimeout(()=>saveCandidate(captureReason),delay);
}
function restoreDom(dom){
 if(!dom?.sections)return false;let changed=false;
 for(const [id,s] of Object.entries(dom.sections)){
  const el=document.getElementById(id);if(!el||typeof s?.html!=='string')continue;
  if(el.innerHTML!==s.html){el.innerHTML=s.html;changed=true}
  if(el.dataset){if(s.cleared)el.dataset.fmNewsCleared=s.cleared;else delete el.dataset.fmNewsCleared}
 }
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
function applyGlobalNews(news){
 if(news===undefined)return false;
 const current=globalNewsRef();
 if(current){if(JSON.stringify(current)===JSON.stringify(news))return false;current.length=0;current.push(...clone(arr(news)));return true}
 try{window.NEWS=clone(arr(news));return true}catch(_e){return false}
}
function restore(reason='refresh restore'){
 // Never write old News into a live import. Between imports, however, the saved snapshot is
 // authoritative for this exact imported FM database and must survive every refresh.
 if(restoring||importMode()||armed())return false;
 const payload=payloadRef();if(!payload)return false;
 const snap=readLocal();if(!snap||Number(snap.quality||0)<=0||!compatible(snap,payload))return false;
 restoring=true;
 try{
  const stateChanged=applyStateNews(snap.state_news),globalChanged=applyGlobalNews(snap.global_news);
  if(stateChanged||globalChanged){try{if(typeof renderAll==='function')renderAll()}catch(_e){}}
  try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}
  const reapply=()=>{if(!importMode())restoreDom(snap.dom)};
  reapply();setTimeout(reapply,30);setTimeout(reapply,120);setTimeout(reapply,350);setTimeout(reapply,900);
  lastRestoreAt=Date.now();return true;
 }finally{restoring=false}
}
function scheduleRestore(){for(const ms of [80,180,350,700,1200,2000,3500,5500,8000])setTimeout(()=>restore(),ms)}
function installObserver(){
 if(observer)return;
 observer=new MutationObserver(()=>{if(armed())queueCapture('import News mutation');});
 observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
}
window.FMNewsPersistence={version:VERSION,readLocal,clearLocal,restore,startCapture,saveCandidate,signature,compatible,status:()=>({version:VERSION,importMode:importMode(),captureWindow:Math.max(0,captureUntil-Date.now()),captureReason,lastSavedAt,lastSavedQuality,lastRestoreAt,hasLocal:!!readLocal(),localQuality:Number(readLocal()?.quality||0),payloadReady:!!payloadRef(),signature:signature()})};
installObserver();
window.addEventListener('fmcanonicalpublished',()=>startCapture('fmcanonicalpublished',180000));
window.addEventListener('fmworldloaded',scheduleRestore);
window.addEventListener('fmcloudready',scheduleRestore);
window.addEventListener('focus',()=>setTimeout(()=>restore('focus'),120));
document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(()=>restore('visibility'),120)});
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=norm(b.textContent||b.dataset?.nav||b.getAttribute('data-page')||'');if(s.includes('news')){setTimeout(()=>restore('News navigation'),60);setTimeout(()=>restore('News navigation'),250)}},true);
let tries=0;const timer=setInterval(()=>{
 tries++;const mode=importMode();
 if(mode){
  if(!sawImport||mode!==lastMode){sawImport=true;lastMode=mode;startCapture(`import observed: ${mode}`,180000)}
  // Keep harvesting meaningful News even if the importer leaves its mode flag set after render.
  if(tries%5===0)saveCandidate('import still active');
 }else if(sawImport){
  sawImport=false;lastMode='';startCapture('import mode cleared',180000);
 }else if(payloadRef()&&!armed()&&tries%20===0){restore('startup poll');}
 if(tries>1800)clearInterval(timer);
},100);
})();