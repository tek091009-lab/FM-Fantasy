(()=>{
 const VERSION='manager-authoritative-v6-preserve-team-management-drafts';
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 let client=null,busy=false,lastStamp='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 const copy=v=>v==null?v:clone(v);
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
  // Bench order is meaningful for autosubs, so compare it in order rather than as a set.
  if(ids(a.bench)!==ids(b.bench))return true;
  if(String(a.captain??'')!==String(b.captain??''))return true;
  if(String(a.vice??'')!==String(b.vice??''))return true;
  const ab=Number(a.bank),bb=Number(b.bank);
  if(Number.isFinite(ab)&&Number.isFinite(bb)&&Math.abs(ab-bb)>1e-9)return true;
  return false;
 }
 function validConfirmedManagementShape(st){
  if(!st?.teamConfirmed)return false;
  const squad=arr(st.squad),starters=arr(st.starters),bench=arr(st.bench);
  if(squad.length!==15||starters.length!==11||bench.length!==4)return false;
  const squadIds=squad.map(String),lineupIds=[...starters,...bench].map(String);
  if(new Set(squadIds).size!==15||new Set(lineupIds).size!==15)return false;
  if([...squadIds].sort().join('|')!==[...lineupIds].sort().join('|'))return false;
  const starterSet=new Set(starters.map(String));
  const cap=String(st.captain??''),vice=String(st.vice??'');
  if(cap&&!starterSet.has(cap))return false;
  if(vice&&!starterSet.has(vice))return false;
  if(cap&&vice&&cap===vice)return false;
  return true;
 }
 function hasTransferDraft(st){
  st=st||(typeof state!=='undefined'?state:null);
  if(!st?.teamConfirmed||arr(st.lockedSquad).length!==15)return false;
  const squad=arr(st.squad),locked=arr(st.lockedSquad);
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
  const server=window.FMCloud?.managerState||null;
  if(!server)return true;
  if(server.teamConfirmed)return false;
  return editableDiff(st,server);
 }
 function hasConfirmedTeamManagementDraft(st){
  st=st||(typeof state!=='undefined'?state:null);
  if(!st?.teamConfirmed||hasTransferDraft(st))return false;
  const server=window.FMCloud?.managerState||null;
  if(!server?.teamConfirmed)return false;
  if(!validConfirmedManagementShape(st)||!validConfirmedManagementShape(server))return false;
  if(idSet(st.squad)!==idSet(server.squad))return false;
  return editableDiff(st,server);
 }
 function hasManagerDraft(st){return hasTransferDraft(st)||hasInitialSquadDraft(st)||hasConfirmedTeamManagementDraft(st)}
 function captureManagerDraft(){
  if(typeof state==='undefined'||!hasManagerDraft(state))return null;
  const out={};
  for(const k of ['squad','starters','bench','captain','vice','bank'])if(Object.prototype.hasOwnProperty.call(state,k))out[k]=copy(state[k]);
  return out;
 }
 function restoreManagerDraft(saved){
  if(typeof state==='undefined'||!state||!saved)return false;
  for(const k of ['squad','starters','bench','captain','vice','bank'])if(Object.prototype.hasOwnProperty.call(saved,k))state[k]=copy(saved[k]);
  return true;
 }
 const captureTransferDraft=captureManagerDraft;
 const restoreTransferDraft=restoreManagerDraft;
 function signature(remote,updatedAt=''){
  return [updatedAt,ids(remote?.squad),ids(remote?.lockedSquad),ids(remote?.starters),ids(remote?.bench),String(remote?.captain??''),String(remote?.vice??''),String(remote?.bank??''),String(remote?.lockedBank??''),String(!!remote?.teamConfirmed),num(remote?.currentGameweek),num(remote?.completedGameweek),arr(remote?.pointsHistory).length,num(remote?.totalPoints),num(remote?.freeTransfers),num(remote?.lastTransferRollGW),String(remote?.teamName??''),String(remote?.managerName??'')].join('~');
 }
 function criticalHealthy(remote){
  if(typeof state==='undefined'||!state)return false;
  const draft=hasManagerDraft(state);
  if(state.teamConfirmed){
    if(!draft&&(!validConfirmedManagementShape(state)||editableDiff(state,remote)))return false;
    if(draft&&(!arr(state.squad).length||arr(state.squad).length>15))return false;
  }else{
    if(arr(state.squad).length>15)return false;
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
   const managerDraft=captureManagerDraft();
   const worldDerived=captureWorldDerivedState();
   state=Object.assign({},DEFAULT,clean);
   state.chips=state.chips||clone(DEFAULT.chips);
   restoreWorldDerivedState(worldDerived);
   restoreManagerDraft(managerDraft);
   // This must remain the pure server snapshot. Draft detection compares the live
   // editable manager fields against it until the queued save catches up.
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
 window.FMManagerAuthoritative={version:VERSION,restore,captureWorldDerivedState,restoreWorldDerivedState,editableDiff,validConfirmedManagementShape,hasTransferDraft,hasInitialSquadDraft,hasConfirmedTeamManagementDraft,hasManagerDraft,captureManagerDraft,restoreManagerDraft,captureTransferDraft,restoreTransferDraft,criticalHealthy,signature};
 window.addEventListener('fmcloudready',()=>schedule(250));
 window.addEventListener('fmcanonicalpublished',()=>schedule(60));
 window.addEventListener('fmworldmanagersscored',()=>schedule(60));
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&window.FMCloud?.ready?.())schedule(120)});
})();
