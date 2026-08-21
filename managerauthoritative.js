(()=>{
 const VERSION='manager-authoritative-v2-preserve-world-derived-news';
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 let client=null,busy=false,lastStamp='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 function cloudClient(){
  if(!window.FMCloud?.ready?.())return null;
  if(!client)client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
  return client;
 }
 function captureWorldDerivedState(){
  if(typeof state==='undefined'||!state)return {};
  const out={};
  // News and availability belong to the imported FM world, not the manager save.
  // A manager-state refresh must never replace them with DEFAULT/old manager-state values.
  if(Object.prototype.hasOwnProperty.call(state,'news'))out.news=JSON.parse(JSON.stringify(state.news));
  if(Object.prototype.hasOwnProperty.call(state,'activeStatuses'))out.activeStatuses=JSON.parse(JSON.stringify(state.activeStatuses));
  return out;
 }
 function restoreWorldDerivedState(saved){
  if(typeof state==='undefined'||!state||!saved)return;
  if(Object.prototype.hasOwnProperty.call(saved,'news'))state.news=saved.news;
  if(Object.prototype.hasOwnProperty.call(saved,'activeStatuses'))state.activeStatuses=saved.activeStatuses;
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
   const sig=`${data.updated_at||''}|${(clean.squad||[]).length}|${(clean.starters||[]).length}|${(clean.bench||[]).length}|${clean.currentGameweek||''}`;
   if(sig===lastStamp&&typeof state!=='undefined'&&(state.squad||[]).length===15&&(state.starters||[]).length===11&&(state.bench||[]).length===4)return true;
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
   // Persistence is a second line of defence, but the manager rehydrate itself is now non-destructive.
   try{setTimeout(()=>window.FMNewsPersistence?.restore?.('manager authoritative restore'),0)}catch(_e){}
   requestAnimationFrame(()=>{try{if(typeof fitActivePage==='function')fitActivePage()}catch(_){}});
   return true;
  }catch(e){console.warn('[FM authoritative manager hydrate]',e);return false}finally{busy=false}
 }
 window.fmRestoreManagerFromCloud=restore;
 window.FMManagerAuthoritative={version:VERSION,restore,captureWorldDerivedState,restoreWorldDerivedState};
 window.addEventListener('fmcloudready',()=>setTimeout(restore,250));
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&window.FMCloud?.ready?.())setTimeout(restore,250)});
})();
