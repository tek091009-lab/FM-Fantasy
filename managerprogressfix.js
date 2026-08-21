(()=>{
'use strict';
const VERSION='manager-progress-v6-server-authoritative-no-local-flicker';
const cfg=window.FM_FANTASY_CONFIG||{};
let busy=false,lastRemoteCheck=0,watchClient=null;
const num=v=>Number(v||0)||0;
function sharedMeta(){return window.FMCloud?.getWorld?.()?.payload?.meta||{}}
function targetCompletedGameweek(){return num(sharedMeta().completed_gameweek)}
function historyCompletedGameweek(){if(typeof state==='undefined')return 0;const entry=Math.max(1,num(state.entryGameweek)||1),h=Array.isArray(state.pointsHistory)?state.pointsHistory:[];return h.length?Math.max(entry-1,...h.map(x=>num(x?.gw))):entry-1}
async function refreshSharedWorldIfNeeded(force=false){
 try{
  if(!window.FMCloud?.ready?.())return false;const world=window.FMCloud.getWorld?.();if(!world?.id)return false;const now=Date.now();if(!force&&now-lastRemoteCheck<5000)return false;lastRemoteCheck=now;
  if(!watchClient&&window.supabase&&cfg.supabaseUrl&&cfg.supabaseAnonKey)watchClient=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
  if(!watchClient)return false;const{data,error}=await watchClient.from('worlds').select('updated_at,payload_version').eq('id',world.id).single();if(error||!data?.updated_at)return false;
  const remote=Date.parse(data.updated_at)||0,local=Date.parse(world.updated_at||0)||0;if(!force&&remote<=local)return false;if(remote>local)world.updated_at='';
  const payload=await window.FMCloud.loadWorld?.(true);if(!payload)return false;world.payload=payload;world.updated_at=data.updated_at;world.payload_version=num(data.payload_version);return true;
 }catch(e){console.warn('[FM manager progress v6] shared world refresh failed',e);return false}
}
async function restoreOwn(){try{if(typeof window.fmRestoreManagerFromCloud==='function')return await window.fmRestoreManagerFromCloud()}catch(e){console.warn('[FM manager progress v6] manager restore failed',e)}return false}
async function finaliseOwnManagerProgress(force=false){
 if(busy||!window.FMCloud?.ready?.())return false;busy=true;
 try{
  if(force)await refreshSharedWorldIfNeeded(true);else await refreshSharedWorldIfNeeded(false);
  const target=targetCompletedGameweek();
  if(window.FMCloud.isCreator?.()&&target>historyCompletedGameweek()){
   try{if(window.FMManagerStateAuthority?.kickCreatorScoring)await window.FMManagerStateAuthority.kickCreatorScoring(true);else if(typeof globalThis.fmCreatorFinaliseWorldManagers==='function')await globalThis.fmCreatorFinaliseWorldManagers(true)}catch(e){console.warn('[FM manager progress v6] creator scoring failed',e)}
  }
  await restoreOwn();
  if(typeof renderAll==='function')renderAll();if(typeof renderLeagues==='function')renderLeagues();
  return historyCompletedGameweek()>=target;
 }finally{busy=false}
}
async function forceRefreshData(button){const old=button?.textContent||'Refresh Data';try{if(button){button.disabled=true;button.textContent='Refreshing…'}await finaliseOwnManagerProgress(true);if(button)button.textContent='Refreshed ✓';setTimeout(()=>{if(button){button.disabled=false;button.textContent=old}},1200)}catch(e){console.warn('[FM manager progress v6] refresh failed',e);if(button){button.disabled=false;button.textContent='Refresh failed';setTimeout(()=>button.textContent=old,1500)}}}
function installRefreshButton(){if(document.getElementById('fmForceRefreshDataBtn'))return;const anchor=document.getElementById('updateImportBtn')||document.getElementById('seasonImportBtn')||document.getElementById('exportDebugBtn');if(!anchor?.parentNode)return;const btn=document.createElement('button');btn.id='fmForceRefreshDataBtn';btn.type='button';btn.textContent='↻ Refresh Data';btn.className=anchor.className||'';btn.style.marginLeft='8px';btn.title='Reload the canonical world and server-scored manager progress';btn.addEventListener('click',()=>forceRefreshData(btn));anchor.insertAdjacentElement('afterend',btn)}
window.fmFinaliseOwnManagerProgress=()=>finaliseOwnManagerProgress(false);window.fmForceRefreshFantasyData=()=>forceRefreshData(document.getElementById('fmForceRefreshDataBtn'));window.FMManagerProgressV6={version:VERSION,finaliseOwnManagerProgress,historyCompletedGameweek,targetCompletedGameweek};
window.addEventListener('fmcloudready',()=>setTimeout(()=>{installRefreshButton();finaliseOwnManagerProgress(false)},500));window.addEventListener('fmworldmanagersscored',()=>setTimeout(()=>finaliseOwnManagerProgress(false),180));window.addEventListener('focus',()=>setTimeout(()=>finaliseOwnManagerProgress(true),300));document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(()=>finaliseOwnManagerProgress(true),300)});setTimeout(()=>{installRefreshButton();finaliseOwnManagerProgress(false)},900);setInterval(()=>{if(targetCompletedGameweek()>historyCompletedGameweek())finaliseOwnManagerProgress(false)},5000);
})();
