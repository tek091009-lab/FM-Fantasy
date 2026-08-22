(()=>{
'use strict';
const VERSION='manager-state-authority-v2-pure-server-draft-baseline';
const cfg=window.FM_FANTASY_CONFIG||{};
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const num=v=>Number(v||0)||0;
let client=null,queueTimer=null,installTries=0,kickBusy=false;
function getClient(){
 if(client)return client;
 try{if(window.supabase&&cfg.supabaseUrl&&cfg.supabaseAnonKey)client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}})}catch(_e){}
 return client;
}
function historyDone(st){const entry=Math.max(1,num(st?.entryGameweek)||1),h=arr(st?.pointsHistory);return h.length?Math.max(entry-1,...h.map(x=>num(x?.gw))):entry-1}
function historyTotal(st){return arr(st?.pointsHistory).reduce((n,x)=>n+num(x?.net??x?.gross),0)}
function mergeHistoricalLineups(local,remote,done){const l=(local?.gameweekLineups&&typeof local.gameweekLineups==='object'&&!Array.isArray(local.gameweekLineups))?clone(local.gameweekLineups):{};const r=(remote?.gameweekLineups&&typeof remote.gameweekLineups==='object'&&!Array.isArray(remote.gameweekLineups))?remote.gameweekLineups:{};for(const [k,v] of Object.entries(r)){const gw=num(k||v?.gw);if(gw&&gw<=done)l[String(gw)]=clone(v)}return l}
function mergeProgress(local,remote){
 const out=clone(local||{}),rd=historyDone(remote),ld=historyDone(local),rh=arr(remote?.pointsHistory),lh=arr(local?.pointsHistory);
 const remoteWins=rd>ld||(rd===ld&&rh.length>lh.length)||(rd===ld&&rh.length&&historyTotal(remote)!==historyTotal(local));
 if(!remoteWins)return out;
 out.pointsHistory=clone(rh);
 out.totalPoints=num(remote?.totalPoints)||historyTotal(remote);
 out.completedGameweek=rd;
 out.currentGameweek=Math.max(num(remote?.currentGameweek),rd+1,num(out?.entryGameweek)||1);
 out.firstGameweekPlayed=!!remote?.firstGameweekPlayed||rh.length>0;
 out.gameweekLineups=mergeHistoricalLineups(out,remote,rd);
 if(num(remote?.lastTransferRollGW)>num(out?.lastTransferRollGW)){
   out.lastTransferRollGW=num(remote.lastTransferRollGW);
   out.freeTransfers=num(remote?.freeTransfers);
 }
 if(remote?.chips&&typeof remote.chips==='object'){
   out.chips=out.chips&&typeof out.chips==='object'?out.chips:{};
   for(const half of ['first','second']){
     out.chips[half]=Object.assign({},remote.chips?.[half]||{},out.chips?.[half]||{});
     for(const key of ['wildcard','triple','bench'])if(remote.chips?.[half]?.[key])out.chips[half][key]=true;
   }
 }
 return out;
}
function applyProgressToLive(merged,serverSnapshot=null){
 try{
   if(typeof state!=='undefined'&&state){
     for(const k of ['pointsHistory','totalPoints','completedGameweek','currentGameweek','firstGameweekPlayed','gameweekLineups','lastTransferRollGW','freeTransfers','chips'])if(Object.prototype.hasOwnProperty.call(merged,k))state[k]=clone(merged[k]);
   }
   // managerauthoritative.js uses FMCloud.managerState as the last pure server
   // snapshot to detect an in-flight squad/lineup/captain edit. Never contaminate
   // that baseline with local editable fields just because server progress won.
   if(window.FMCloud)window.FMCloud.managerState=clone(serverSnapshot||merged);
 }catch(_e){}
}
async function remoteOwnState(){
 const c=getClient(),world=window.FMCloud?.getWorld?.();if(!c||!world?.id)return null;
 try{const sess=(await c.auth.getSession()).data.session;if(!sess)return null;const{data,error}=await c.from('manager_states').select('state').eq('world_id',world.id).eq('user_id',sess.user.id).maybeSingle();if(error)throw error;return data?.state||null}catch(e){console.warn('[FM manager authority] remote state read failed',e);return null}
}
function installQueueGuard(){
 const c=window.FMCloud;if(!c||c.__managerStateAuthorityV1||typeof c.queueManagerSave!=='function')return false;
 c.__managerStateAuthorityV1=true;
 const original=c.queueManagerSave.bind(c);
 c.__managerStateAuthorityOriginalQueueV1=original;
 c.queueManagerSave=st=>{
   const snap=clone(st||{});clearTimeout(queueTimer);
   queueTimer=setTimeout(async()=>{
     const remote=await remoteOwnState();const merged=remote?mergeProgress(snap,remote):snap;
     if(remote&&historyDone(remote)>historyDone(snap))applyProgressToLive(merged,remote);
     original(merged);
   },120);
 };
 return true;
}
async function refreshOwnFromServer(){try{if(typeof window.fmRestoreManagerFromCloud==='function')return await window.fmRestoreManagerFromCloud();}catch(e){console.warn('[FM manager authority] own restore failed',e)}return false}
async function kickCreatorScoring(force=true){
 if(kickBusy||!window.FMCloud?.ready?.()||!window.FMCloud?.isCreator?.())return false;kickBusy=true;
 try{
   const fn=globalThis.fmCreatorFinaliseWorldManagers;if(typeof fn!=='function')return false;
   const ok=await fn(force);
   await new Promise(r=>setTimeout(r,220));
   await refreshOwnFromServer();
   return ok!==false;
 }catch(e){console.warn('[FM manager authority] creator scoring kick failed',e);return false}
 finally{kickBusy=false}
}
function install(){installQueueGuard()}
window.FMManagerStateAuthority={version:VERSION,historyDone,mergeProgress,applyProgressToLive,refreshOwnFromServer,kickCreatorScoring,install};
window.addEventListener('fmcloudready',()=>setTimeout(async()=>{install();await kickCreatorScoring(true);await refreshOwnFromServer()},700));
window.addEventListener('fmworldmanagersscored',()=>setTimeout(refreshOwnFromServer,120));
window.addEventListener('fmcanonicalpublished',()=>setTimeout(()=>kickCreatorScoring(true),180));
window.addEventListener('focus',()=>setTimeout(async()=>{install();await kickCreatorScoring(true);await refreshOwnFromServer()},300));
document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(async()=>{install();await kickCreatorScoring(true);await refreshOwnFromServer()},300)});
const timer=setInterval(()=>{installTries++;install();if(window.FMCloud?.ready?.()){if(window.FMCloud?.isCreator?.())kickCreatorScoring(true);else refreshOwnFromServer()}if(installTries>240)clearInterval(timer)},2500);
})();
