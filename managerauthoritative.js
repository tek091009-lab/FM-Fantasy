(()=>{
 const VERSION='manager-authoritative-v3-critical-state-integrity';
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 let client=null,busy=false,lastStamp='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 const arr=v=>Array.isArray(v)?v:[];
 const num=v=>Number(v||0)||0;
 const ids=v=>arr(v).map(String).join('|');
 function cloudClient(){
  if(!window.FMCloud?.ready?.())return null;
  if(!client)client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
  return client;
 }
 function captureWorldDerivedState(){
  if(typeof state==='undefined'||!state)return {};
  const out={};
  if(Object.prototype.hasOwnProperty.call(state,'news'))out.news=clone(state.news);
  if(Object.prototype.hasOwnProperty.call(state,'activeStatuses'))out.activeStatuses=clone(state.activeStatuses);
  return out;
 }
 function restoreWorldDerivedState(saved){
  if(typeof state==='undefined'||!state||!saved)return;
  if(Object.prototype.hasOwnProperty.call(saved,'news'))state.news=saved.news;
  if(Object.prototype.hasOwnProperty.call(saved,'activeStatuses'))state.activeStatuses=saved.activeStatuses;
 }
 function signature(remote,updatedAt=''){
  return [updatedAt,ids(remote?.squad),ids(remote?.lockedSquad),arr(remote?.starters).length,arr(remote?.bench).length,num(remote?.currentGameweek),num(remote?.completedGameweek),arr(remote?.pointsHistory).length,num(remote?.totalPoints),num(remote?.freeTransfers),num(remote?.lastTransferRollGW),String(remote?.lockedBank??''),String(remote?.teamName??''),String(remote?.managerName??'')].join('~');
 }
 function criticalHealthy(remote){
  if(typeof state==='undefined'||!state)return false;
  if(arr(state.squad).length!==15||arr(state.starters).length!==11||arr(state.bench).length!==4)return false;
  if(remote?.teamConfirmed&&arr(remote?.lockedSquad).length===15){
    if(arr(state.lockedSquad).length!==15||ids(state.lockedSquad)!==ids(remote.lockedSquad))return false;
    if(String(state.lockedBank??'')!==String(remote.lockedBank??''))return false;
  }
  if(num(state.currentGameweek)!==num(remote?.currentGameweek))return false;
  if(num(state.completedGameweek)!==num(remote?.completedGameweek))return false;
  if(arr(state.pointsHistory).length!==arr(remote?.pointsHistory).length)return false;
  if(num(state.totalPoints)!==num(remote?.totalPoints))return false;
  if(num(state.freeTransfers)!==num(remote?.freeTransfers))return false;
  if(num(state.lastTransferRollGW)!==num(remote?.lastTransferRollGW))return false;
  if(String(state.teamName??'')!==String(remote?.teamName??''))return false;
  if(String(state.managerName??'')!==String(remote?.managerName??''))return false;
  return true;
 }
 async function restore(){
  if(busy||!window.FMCloud?.ready?.())return false;busy=true;
  try{
   const c=cloudClient();if(!c)return false;
   const sess=(await c.auth.getSession()).data.session;if(!sess)return false;
   const world=window.FMCloud?.getWorld?.();if(!world?.id)return false;
   const{data,error}=await c.from('manager_states').select('state,updated_at').eq('world_id',world.id).eq('user_id',sess.user.id).maybeSingle();
   if(error||!data?.state)return false;
   const raw=clone(data.state),clean=window.FMCloud?.normaliseManagerState?window.FMCloud.normaliseManagerState(raw):raw;
   const sig=signature(clean,data.updated_at||'');
   if(sig===lastStamp&&criticalHealthy(clean))return true;
   if(typeof state==='undefined'||typeof DEFAULT==='undefined')return false;
   const worldDerived=captureWorldDerivedState();
   state=Object.assign({},DEFAULT,clean);
   state.chips=state.chips||clone(DEFAULT.chips);
   restoreWorldDerivedState(worldDerived);
   if(window.FMCloud)window.FMCloud.managerState=clone(clean);
   lastStamp=sig;
   if(typeof renderTransferPitch==='function')renderTransferPitch();
   if(typeof renderTransferSummary==='function')renderTransferSummary();
   if(typeof renderMarket==='function')renderMarket();
   if(typeof renderTeam==='function')renderTeam();
   if(typeof renderSidebar==='function')renderSidebar();
   if(typeof renderNews==='function')renderNews();
   if(typeof renderLeagues==='function')renderLeagues();
   try{setTimeout(()=>window.FMNewsPersistence?.restore?.('manager authoritative restore'),0)}catch(_e){}
   requestAnimationFrame(()=>{try{if(typeof fitActivePage==='function')fitActivePage()}catch(_){}});
   return true;
  }catch(e){console.warn('[FM authoritative manager hydrate]',e);return false}finally{busy=false}
 }
 const schedule=(ms=80)=>setTimeout(restore,ms);
 window.fmRestoreManagerFromCloud=restore;
 window.FMManagerAuthoritative={version:VERSION,restore,captureWorldDerivedState,restoreWorldDerivedState,criticalHealthy,signature};
 window.addEventListener('fmcloudready',()=>schedule(250));
 window.addEventListener('fmcanonicalpublished',()=>schedule(60));
 window.addEventListener('fmworldmanagersscored',()=>schedule(60));
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&window.FMCloud?.ready?.())schedule(120)});
})();
