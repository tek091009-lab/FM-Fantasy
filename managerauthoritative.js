(()=>{
 const VERSION='manager-authoritative-v5-preserve-all-manager-drafts';
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 let client=null,busy=false,lastStamp='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 const arr=v=>Array.isArray(v)?v:[];
 const num=v=>Number(v||0)||0;
 const ids=v=>arr(v).map(String).join('|');
 const idSet=v=>arr(v).map(String).sort().join('|');
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
 function editableDiff(a,b){
  if(!a||!b)return true;
  if(idSet(a.squad)!==idSet(b.squad))return true;
  if(idSet(a.starters)!==idSet(b.starters))return true;
  if(idSet(a.bench)!==idSet(b.bench))return true;
  if(String(a.captain??'')!==String(b.captain??''))return true;
  if(String(a.vice??'')!==String(b.vice??''))return true;
  const ab=Number(a.bank),bb=Number(b.bank);
  if(Number.isFinite(ab)&&Number.isFinite(bb)&&Math.abs(ab-bb)>1e-9)return true;
  return false;
 }
 function hasTransferDraft(st){
  st=st||(typeof state!=='undefined'?state:null);
  if(!st?.teamConfirmed||arr(st.lockedSquad).length!==15)return false;
  const squad=arr(st.squad),locked=arr(st.lockedSquad);
  // An empty/broken startup state is not treated as a user draft. The transfer
  // integrity guard/server restore is allowed to repair it from lockedSquad.
  if(!squad.length||squad.length>15)return false;
  if(squad.length!==15)return true;
  if(idSet(squad)!==idSet(locked))return true;
  const bank=Number(st.bank),lockedBank=Number(st.lockedBank);
  return Number.isFinite(bank)&&Number.isFinite(lockedBank)&&Math.abs(bank-lockedBank)>1e-9;
 }
 function hasInitialSquadDraft(st){
  st=st||(typeof state!=='undefined'?state:null);
  if(!st||st.teamConfirmed)return false;
  const squad=arr(st.squad);if(!squad.length||squad.length>15)return false;
  // FMCloud.managerState is deliberately kept as the last server snapshot.
  // If the live builder differs from it, the user has an unsaved/in-flight
  // squad edit and a delayed server hydrate must not paint the older snapshot
  // back over the click that just happened.
  const server=window.FMCloud?.managerState||null;
  if(!server)return true;
  if(server.teamConfirmed)return false;
  return editableDiff(st,server);
 }
 function hasManagerDraft(st){return hasTransferDraft(st)||hasInitialSquadDraft(st)}
 function captureManagerDraft(){
  if(typeof state==='undefined'||!hasManagerDraft(state))return null;
  const out={};
  for(const k of ['squad','starters','bench','captain','vice','bank'])if(Object.prototype.hasOwnProperty.call(state,k))out[k]=clone(state[k]);
  return out;
 }
 function restoreManagerDraft(saved){
  if(typeof state==='undefined'||!state||!saved)return false;
  for(const k of ['squad','starters','bench','captain','vice','bank'])if(Object.prototype.hasOwnProperty.call(saved,k))state[k]=clone(saved[k]);
  return true;
 }
 // Backward-compatible names retained for the V37 transfer regression/API.
 const captureTransferDraft=captureManagerDraft;
 const restoreTransferDraft=restoreManagerDraft;
 function signature(remote,updatedAt=''){
  return [updatedAt,ids(remote?.squad),ids(remote?.lockedSquad),arr(remote?.starters).length,arr(remote?.bench).length,num(remote?.currentGameweek),num(remote?.completedGameweek),arr(remote?.pointsHistory).length,num(remote?.totalPoints),num(remote?.freeTransfers),num(remote?.lastTransferRollGW),String(remote?.lockedBank??''),String(remote?.teamName??''),String(remote?.managerName??'')].join('~');
 }
 function criticalHealthy(remote){
  if(typeof state==='undefined'||!state)return false;
  const draft=hasManagerDraft(state);
  if(state.teamConfirmed){
    if(!draft&&(arr(state.squad).length!==15||arr(state.starters).length!==11||arr(state.bench).length!==4))return false;
    if(draft&&(!arr(state.squad).length||arr(state.squad).length>15))return false;
  }else{
    if(arr(state.squad).length>15)return false;
    // A partial initial squad is a valid live state. If it is not a local draft,
    // it must exactly match the server snapshot before we call it healthy.
    if(!draft&&editableDiff(state,remote))return false;
  }
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
   // Server progress remains authoritative, but editable manager work must survive
   // a stale hydrate while its queued save is still in flight. This covers both
   // initial squad construction and confirmed-team transfer drafting.
   const managerDraft=captureManagerDraft();
   const worldDerived=captureWorldDerivedState();
   state=Object.assign({},DEFAULT,clean);
   state.chips=state.chips||clone(DEFAULT.chips);
   restoreWorldDerivedState(worldDerived);
   restoreManagerDraft(managerDraft);
   // Keep this as the pure server snapshot so the next local edit can be
   // distinguished from data that genuinely arrived from the server.
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
 window.FMManagerAuthoritative={version:VERSION,restore,captureWorldDerivedState,restoreWorldDerivedState,editableDiff,hasTransferDraft,hasInitialSquadDraft,hasManagerDraft,captureManagerDraft,restoreManagerDraft,captureTransferDraft,restoreTransferDraft,criticalHealthy,signature};
 window.addEventListener('fmcloudready',()=>schedule(250));
 window.addEventListener('fmcanonicalpublished',()=>schedule(60));
 window.addEventListener('fmworldmanagersscored',()=>schedule(60));
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&window.FMCloud?.ready?.())schedule(120)});
})();
