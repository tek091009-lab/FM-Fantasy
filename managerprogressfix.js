(()=>{
  const cfg=window.FM_FANTASY_CONFIG||{};
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  let busy=false,lastRemoteCheck=0,watchClient=null;

  function sharedMeta(){
    const w=window.FMCloud?.getWorld?.();
    return w?.payload?.meta||{};
  }

  function targetCompletedGameweek(){
    return Number(sharedMeta().completed_gameweek||0);
  }

  function historyCompletedGameweek(){
    if(typeof state==='undefined')return 0;
    const entry=Math.max(1,Number(state.entryGameweek||1));
    const hist=Array.isArray(state.pointsHistory)?state.pointsHistory:[];
    return hist.length?Math.max(...hist.map(x=>Number(x?.gw)||0),entry-1):entry-1;
  }

  function ensureLineupSnapshot(gw){
    if(typeof state==='undefined'||!state?.teamConfirmed)return;
    if(!state.gameweekLineups||typeof state.gameweekLineups!=='object'||Array.isArray(state.gameweekLineups))state.gameweekLineups={};
    if(state.gameweekLineups[String(gw)]||state.gameweekLineups[gw])return;
    const squad=[...(Array.isArray(state.lockedSquad)&&state.lockedSquad.length?state.lockedSquad:(state.squad||[]))];
    state.gameweekLineups[String(gw)]={
      gw:Number(gw),
      squad,
      starters:[...(state.starters||[])],
      bench:[...(state.bench||[])],
      captain:state.captain||null,
      vice:state.vice||null,
      chip:state.activeChip||null,
      hit:Number(state.transferHitThisGW||0)
    };
  }

  async function refreshSharedWorldIfNeeded(force=false){
    try{
      if(!window.FMCloud?.ready?.())return false;
      const world=window.FMCloud.getWorld?.();
      if(!world?.id)return false;
      const now=Date.now();
      if(!force&&now-lastRemoteCheck<5000)return false;
      lastRemoteCheck=now;
      if(!watchClient&&window.supabase&&cfg.supabaseUrl&&cfg.supabaseAnonKey){
        watchClient=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
      }
      if(!watchClient)return false;
      const{data,error}=await watchClient.from('worlds').select('updated_at').eq('id',world.id).single();
      if(error||!data?.updated_at)return false;
      const remote=Date.parse(data.updated_at)||0,local=Date.parse(world.updated_at||0)||0;
      if(!force&&remote<=local)return false;
      const payload=await window.FMCloud.loadWorld?.();
      if(!payload)return false;
      world.payload=payload;world.updated_at=data.updated_at;
      const apply=typeof window.applyImportedPayload==='function'
        ? window.applyImportedPayload
        : (typeof applyImportedPayload==='function'?applyImportedPayload:null);
      if(apply)await apply(payload,'load');
      else if(typeof loadServerImportState==='function')await loadServerImportState();
      return true;
    }catch(e){console.warn('Shared world progress refresh failed',e);return false}
  }

  async function finaliseOwnManagerProgress(){
    try{
      if(busy||typeof state==='undefined'||!state?.teamConfirmed)return false;
      busy=true;

      let target=targetCompletedGameweek();
      let done=historyCompletedGameweek();
      if(!target||target<=done){
        const changed=await refreshSharedWorldIfNeeded(false);
        if(changed){target=targetCompletedGameweek();done=historyCompletedGameweek()}
      }
      if(!target||done>=target)return false;

      /* A cloud manager must never be jumped to the shared world's NEXT GW before
         their missing completed GW has actually been scored. Rewind to the first
         unscored GW, then let the app's own finaliser advance normally. */
      const entry=Math.max(1,Number(state.entryGameweek||1));
      state.completedGameweek=done;
      state.currentGameweek=Math.max(entry,done+1);

      for(let gw=state.currentGameweek;gw<=target;gw++)ensureLineupSnapshot(gw);

      const processFn=typeof window.fmProcessCompletedGameweeks==='function'
        ? window.fmProcessCompletedGameweeks
        : (typeof fmProcessCompletedGameweeks==='function'?fmProcessCompletedGameweeks:null);
      if(!processFn){console.warn('Manager progress finaliser unavailable');return false}

      const before={done,total:Number(state.totalPoints||0)};
      const processed=processFn()||[];
      await sleep(50);
      const afterDone=historyCompletedGameweek();

      if(afterDone>before.done||processed.length){
        state.completedGameweek=afterDone;
        state.currentGameweek=Math.max(Number(state.currentGameweek||0),afterDone+1);
        if(typeof save==='function')save();
        window.FMCloud?.queueManagerSave?.(state);
        if(typeof renderAll==='function')renderAll();
        if(typeof renderLeagues==='function')renderLeagues();
        window.dispatchEvent(new CustomEvent('fmmanagerprogressfinalised',{detail:{from:before.done,to:afterDone,total:Number(state.totalPoints||0),processed:processed.length}}));
      }
      return afterDone>=target;
    }catch(e){console.warn('Manager progress finalisation failed',e);return false}
    finally{busy=false}
  }

  window.fmFinaliseOwnManagerProgress=finaliseOwnManagerProgress;
  const kick=()=>setTimeout(finaliseOwnManagerProgress,180);
  window.addEventListener('fmcloudready',kick);
  window.addEventListener('focus',()=>{refreshSharedWorldIfNeeded(true).finally(kick)});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshSharedWorldIfNeeded(true).finally(kick)});
  setTimeout(finaliseOwnManagerProgress,700);
  setInterval(finaliseOwnManagerProgress,5000);
})();
