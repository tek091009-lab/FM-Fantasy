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

  function repairSequentialState(){
    if(typeof state==='undefined')return 0;
    const entry=Math.max(1,Number(state.entryGameweek||1));
    const done=historyCompletedGameweek();
    state.completedGameweek=done;
    state.currentGameweek=Math.max(entry,done+1);
    return done;
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
      if(remote>local)world.updated_at='';
      const payload=await window.FMCloud.loadWorld?.();
      if(!payload)return false;
      world.payload=payload;world.updated_at=data.updated_at;
      return true;
    }catch(e){console.warn('Shared world progress refresh failed',e);return false}
  }

  async function runCoreProgressFinaliser(){
    /* loadServerImportState lives inside the production bundle and calls the
       bundle's private fmProcessCompletedGameweeks() directly. External scripts
       cannot safely call that private scorer themselves, so always enter via
       this public core path. */
    if(typeof loadServerImportState==='function'){
      await loadServerImportState();
      return true;
    }
    return false;
  }

  async function finaliseOwnManagerProgress(force=false){
    try{
      if(busy||typeof state==='undefined'||!state?.teamConfirmed)return false;
      busy=true;

      if(force)await refreshSharedWorldIfNeeded(true);
      let target=targetCompletedGameweek();
      let done=repairSequentialState();
      if(!target||target<=done){
        const changed=await refreshSharedWorldIfNeeded(false);
        if(changed){target=targetCompletedGameweek();done=repairSequentialState()}
      }
      if(!target||done>=target)return false;

      for(let gw=done+1;gw<=target;gw++)ensureLineupSnapshot(gw);
      state.completedGameweek=done;
      state.currentGameweek=Math.max(Number(state.entryGameweek||1),done+1);

      const beforeDone=done;
      const beforeTotal=Number(state.totalPoints||0);
      const usedCore=await runCoreProgressFinaliser();
      if(!usedCore)return false;
      await sleep(80);

      const afterDone=historyCompletedGameweek();
      if(afterDone>beforeDone||Number(state.totalPoints||0)!==beforeTotal){
        state.completedGameweek=afterDone;
        state.currentGameweek=Math.max(Number(state.entryGameweek||1),afterDone+1);
        if(typeof save==='function')save();
        window.FMCloud?.queueManagerSave?.(state);
        if(typeof renderAll==='function')renderAll();
        if(typeof renderLeagues==='function')renderLeagues();
        window.dispatchEvent(new CustomEvent('fmmanagerprogressfinalised',{detail:{from:beforeDone,to:afterDone,total:Number(state.totalPoints||0)}}));
      }
      return afterDone>=target;
    }catch(e){console.warn('Manager progress finalisation failed',e);return false}
    finally{busy=false}
  }

  async function forceRefreshData(button){
    const oldText=button?.textContent||'Refresh Data';
    try{
      if(button){button.disabled=true;button.textContent='Refreshing…'}
      repairSequentialState();
      await finaliseOwnManagerProgress(true);
      if(typeof renderAll==='function')renderAll();
      if(button)button.textContent='Refreshed ✓';
      setTimeout(()=>{if(button){button.disabled=false;button.textContent=oldText}},1200);
    }catch(e){
      console.warn('Manual fantasy refresh failed',e);
      if(button){button.disabled=false;button.textContent='Refresh failed';setTimeout(()=>button.textContent=oldText,1600)}
    }
  }

  function installRefreshButton(){
    if(document.getElementById('fmForceRefreshDataBtn'))return;
    const anchor=document.getElementById('updateImportBtn')||document.getElementById('seasonImportBtn')||document.getElementById('exportDebugBtn');
    if(!anchor?.parentNode)return;
    const btn=document.createElement('button');
    btn.id='fmForceRefreshDataBtn';
    btn.type='button';
    btn.textContent='↻ Refresh Data';
    btn.className=anchor.className||'';
    btn.style.marginLeft='8px';
    btn.title='Reload the shared FM world and recalculate any missing completed Gameweek points';
    btn.addEventListener('click',()=>forceRefreshData(btn));
    anchor.insertAdjacentElement('afterend',btn);
  }

  window.fmFinaliseOwnManagerProgress=()=>finaliseOwnManagerProgress(false);
  window.fmForceRefreshFantasyData=()=>forceRefreshData(document.getElementById('fmForceRefreshDataBtn'));
  const kick=()=>setTimeout(()=>finaliseOwnManagerProgress(false),180);
  window.addEventListener('fmcloudready',()=>{installRefreshButton();kick()});
  window.addEventListener('focus',()=>{refreshSharedWorldIfNeeded(true).finally(kick)});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshSharedWorldIfNeeded(true).finally(kick)});
  setTimeout(()=>{installRefreshButton();finaliseOwnManagerProgress(false)},700);
  setInterval(()=>finaliseOwnManagerProgress(false),5000);
})();
