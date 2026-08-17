(()=>{
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 let client=null,busy=false,lastStamp='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 function cloudClient(){
  if(!window.FMCloud?.ready?.())return null;
  if(!client)client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
  return client;
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
   state=Object.assign({},DEFAULT,clean);
   state.chips=state.chips||clone(DEFAULT.chips);
   if(window.FMCloud)window.FMCloud.managerState=clone(clean);
   lastStamp=sig;
   if(typeof renderTransferPitch==='function')renderTransferPitch();
   if(typeof renderTransferSummary==='function')renderTransferSummary();
   if(typeof renderMarket==='function')renderMarket();
   if(typeof renderTeam==='function')renderTeam();
   if(typeof renderSidebar==='function')renderSidebar();
   requestAnimationFrame(()=>{try{if(typeof fitActivePage==='function')fitActivePage()}catch(_){}});
   return true;
  }catch(e){console.warn('[FM authoritative manager hydrate]',e);return false}finally{busy=false}
 }
 window.fmRestoreManagerFromCloud=restore;
 window.addEventListener('fmcloudready',()=>setTimeout(restore,250));
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&window.FMCloud?.ready?.())setTimeout(restore,250)});
})();
