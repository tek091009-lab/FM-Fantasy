(()=>{
  const RX_BTN=/^clear\s+(?:saved\s+)?database$/i;
  const RX_DB=/(fm|fantasy|world|save|import|database)/i;
  const RX_AUTH=/(supabase|auth|session|token|login|user)/i;
  const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
  const RESET_BACKUP_KEY='fmFantasyLastSeasonResetBackup';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));

  async function callFirst(names){
    for(const n of names){
      try{const fn=window[n];if(typeof fn==='function'){const r=fn();if(r&&typeof r.then==='function')await r;return n}}
      catch(e){console.warn('[FM clear] helper failed',n,e)}
    }
    return null;
  }

  function resetLeagueSnapshots(leagues){
    return (Array.isArray(leagues)?leagues:[]).map(l=>({...l,members:(Array.isArray(l?.members)?l.members:[]).map(m=>({...m,points:0,pointsHistory:[],squad:[],starters:[],bench:[],captain:null,vice:null,teamConfirmed:false,entryGameweek:1,currentGameweek:1}))}));
  }
  function cleanSeasonState(src){
    const s={...(src||{})};
    Object.assign(s,{squad:[],lockedSquad:[],starters:[],bench:[],captain:null,vice:null,lockedCaptain:null,lockedVice:null,bank:100,lockedBank:100,totalPoints:0,pointsHistory:[],history:[],gameweekLineups:{},completedGameweek:0,currentGameweek:1,entryGameweek:1,firstGameweekPlayed:false,freeTransfers:1,lastTransferRollGW:0,transferHitThisGW:0,activeChip:null,chips:{first:{bench:false,triple:false,wildcard:false},second:{bench:false,triple:false,wildcard:false}},teamConfirmed:false,activeStatuses:{},news:[]});
    s.leagues=resetLeagueSnapshots(s.leagues);
    return s;
  }
  function clearBrowserManagerSeason(){
    try{if(typeof state!=='undefined')state=Object.assign({},typeof DEFAULT!=='undefined'?DEFAULT:{},cleanSeasonState(state))}catch(e){console.warn('[FM clear] in-memory state reset failed',e)}
    try{if(window.FMCloud)window.FMCloud.managerState=cleanSeasonState(window.FMCloud.managerState)}catch(_){ }
    for(const store of [localStorage,sessionStorage]){
      try{
        const doomed=[];
        for(let i=0;i<store.length;i++){
          const k=String(store.key(i)||'');
          if(!k||k===RESET_BACKUP_KEY||RX_AUTH.test(k))continue;
          if(/(fm|fantasy)/i.test(k)&&/(manager|team|squad|points|transfer|chip|league|state|gameweek)/i.test(k))doomed.push(k);
        }
        doomed.forEach(k=>store.removeItem(k));
      }catch(_){ }
    }
  }

  async function resetSharedSeasonSafely(){
    if(!(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.()))return null;
    const cfg=window.FM_FANTASY_CONFIG||{},world=window.FMCloud.getWorld?.();
    if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey||!world?.id)throw new Error('Cloud reset service is not ready.');
    const c=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
    const {data:sessionData,error:sessionError}=await c.auth.getSession();
    if(sessionError||!sessionData?.session)throw new Error('Your login session could not be confirmed for the reset.');
    window.__fmSeasonResetInProgress=true;
    const {data,error}=await c.rpc('fmfantasy_reset_world_season',{p_world_id:world.id});
    if(error){window.__fmSeasonResetInProgress=false;throw error}
    const backupId=String(data||'');
    try{localStorage.setItem(RESET_BACKUP_KEY,backupId)}catch(_){ }
    try{world.payload=null}catch(_){ }
    clearBrowserManagerSeason();
    try{if(typeof window.fmRestoreManagerFromCloud==='function')await window.fmRestoreManagerFromCloud()}catch(e){console.warn('[FM clear] cloud manager rehydrate failed',e)}
    return backupId;
  }

  async function clearSharedWorld(){
    try{
      if(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.()){
        const backupId=await resetSharedSeasonSafely();if(!backupId)throw new Error('Season reset did not return a backup id.');
      }
      try{localStorage.setItem(CLEAR_KEY,'1')}catch(_){ }
      try{sessionStorage.setItem(CLEAR_KEY,'1')}catch(_){ }
    }catch(e){console.error('[FM clear] safe shared reset failed',e);throw new Error(`Could not safely reset the shared season. Nothing has been cleared. ${e?.message||''}`.trim())}
  }

  function isImportedFantasyKey(k){
    if(!k||k===CLEAR_KEY||k===RESET_BACKUP_KEY||RX_AUTH.test(k))return false;
    return /(fm|fantasy)/i.test(k)&&/(db|database|world|save|import|payload|fixture|player|history|injur|suspend|ban|availability|status|news|discipline|match|club|competition|gameweek)/i.test(k);
  }

  async function clearImportedWorld(){
    await clearSharedWorld();
    const helper=await callFirst(['fmStoredClear','fmStoredDelete','fmClearStored','clearImportedDatabase','deleteImportedDatabase','resetImportedDatabase','clearFmDatabase','clearFMDatabase']);
    try{if(indexedDB?.databases){const dbs=await indexedDB.databases();await Promise.all((dbs||[]).map(info=>new Promise(resolve=>{const name=String(info?.name||'');if(!name||!RX_DB.test(name)||RX_AUTH.test(name))return resolve();try{const req=indexedDB.deleteDatabase(name);req.onsuccess=req.onerror=req.onblocked=()=>resolve()}catch(_){resolve()}})))}}catch(e){console.warn('[FM clear] IndexedDB fallback failed',e)}
    for(const store of [localStorage,sessionStorage]){try{const doomed=[];for(let i=0;i<store.length;i++){const k=String(store.key(i)||'');if(isImportedFantasyKey(k))doomed.push(k)}doomed.forEach(k=>store.removeItem(k))}catch(e){console.warn('[FM clear] storage fallback failed',e)}}
    for(const name of ['PLAYERS','MATCHES','SEASON_FIXTURES','NEWS','INJURIES','SUSPENSIONS']){try{const v=window[name];if(Array.isArray(v))v.length=0}catch(_){ }}
    if(!helper&&typeof window.fmStoredSetLocalOnly==='function'){try{await window.fmStoredSetLocalOnly(null)}catch(e){console.warn('[FM clear] null setter fallback failed',e)}}
    try{if('caches' in window){for(const key of await caches.keys())if(/fm|fantasy/i.test(key))await caches.delete(key)}}catch(_){ }
    await sleep(120);
    location.reload();
  }

  function isClearButton(el){const b=el?.closest?.('button,[role="button"]');if(!b)return null;const t=String(b.textContent||'').trim().replace(/\s+/g,' ');return RX_BTN.test(t)?b:null}
  document.addEventListener('click',e=>{
    const b=isClearButton(e.target);if(!b)return;e.preventDefault();e.stopImmediatePropagation();if(b.dataset.fmClearing==='1')return;
    const cloud=!!window.FMCloud?.isCreator?.();
    const ok=window.confirm(cloud?'Reset this FM Fantasy season and clear the imported database? A full server backup is created first. Accounts, world membership, league/join code are kept; squads, points, chips, transfers, prices and imported FM data are reset for a clean rebuild.':'Clear the imported FM database from this device? Your account/login will be kept.');
    if(!ok)return;b.dataset.fmClearing='1';b.disabled=true;const old=b.textContent;b.textContent='Backing up & clearing…';
    clearImportedWorld().catch(err=>{console.error('[FM clear] failed',err);window.__fmSeasonResetInProgress=false;b.disabled=false;b.dataset.fmClearing='0';b.textContent=old;alert(err?.message||'Could not safely clear the FM database. Nothing has been reset.')});
  },true);
  window.FMClearImportedDatabase=clearImportedWorld;window.FMCloudDatabaseClearKey=CLEAR_KEY;window.FMSeasonResetBackupKey=RESET_BACKUP_KEY;
})();
