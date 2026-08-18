(()=>{
  'use strict';
  const VERSION='creator-clear-v2-single-auth-client';
  const RX_BTN=/^clear\s+(?:saved\s+)?database$/i;
  const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
  const RX_AUTH=/(supabase|auth|session|token|login|user)/i;
  const RX_DB=/(fm|fantasy|world|save|import|database)/i;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));

  function isButton(target){
    const b=target?.closest?.('button,[role="button"]');
    if(!b)return null;
    const text=String(b.textContent||'').trim().replace(/\s+/g,' ');
    return RX_BTN.test(text)?b:null;
  }
  function isImportedKey(k){
    if(!k||k===CLEAR_KEY||RX_AUTH.test(k))return false;
    return /(fm|fantasy)/i.test(k)&&/(db|database|world|save|import|payload|fixture|player|history|injur|suspend|ban|availability|status|news|discipline|match|club|competition|gameweek|price)/i.test(k);
  }
  async function clearLocalImport(){
    try{if(typeof window.fmStoredClear==='function')await window.fmStoredClear()}catch(e){console.warn('[FM clear v2] local store clear failed',e)}
    try{
      if(indexedDB?.databases){
        const dbs=await indexedDB.databases();
        await Promise.all((dbs||[]).map(info=>new Promise(resolve=>{
          const name=String(info?.name||'');
          if(!name||!RX_DB.test(name)||RX_AUTH.test(name))return resolve();
          try{const req=indexedDB.deleteDatabase(name);req.onsuccess=req.onerror=req.onblocked=()=>resolve()}catch(_){resolve()}
        })));
      }
    }catch(e){console.warn('[FM clear v2] IndexedDB cleanup failed',e)}
    for(const store of [localStorage,sessionStorage]){
      try{
        const doomed=[];
        for(let i=0;i<store.length;i++){const k=String(store.key(i)||'');if(isImportedKey(k))doomed.push(k)}
        doomed.forEach(k=>store.removeItem(k));
      }catch(e){console.warn('[FM clear v2] storage cleanup failed',e)}
    }
    for(const name of ['PLAYERS','MATCHES','SEASON_FIXTURES','NEWS','INJURIES','SUSPENSIONS']){
      try{const v=window[name];if(Array.isArray(v))v.length=0}catch(_){ }
    }
    try{if('caches' in window){for(const key of await caches.keys())if(/fm|fantasy/i.test(key))await caches.delete(key)}}catch(_){ }
  }
  async function clearCreator(button){
    if(!window.FMCloud?.ready?.())throw new Error('Cloud account is not ready yet.');
    if(!window.FMCloud?.isCreator?.())throw new Error('Only the FPL Creator can clear the shared database.');
    if(typeof window.FMCloud.publishWorld!=='function')throw new Error('Cloud reset service is unavailable.');
    window.__fmSeasonResetInProgress=true;
    await window.FMCloud.publishWorld(null);
    try{localStorage.setItem(CLEAR_KEY,'1')}catch(_){ }
    try{sessionStorage.setItem(CLEAR_KEY,'1')}catch(_){ }
    await clearLocalImport();
    await sleep(120);
    location.reload();
  }

  document.addEventListener('click',e=>{
    const b=isButton(e.target);if(!b||!window.FMCloud?.isCreator?.())return;
    e.preventDefault();e.stopImmediatePropagation();
    if(b.dataset.fmClearingV2==='1')return;
    const ok=window.confirm('Reset this FM Fantasy season and clear the imported database? A full server backup is created first. Accounts, world membership, league/join code are kept; squads, points, chips, transfers, prices and imported FM data are reset for a clean rebuild.');
    if(!ok)return;
    b.dataset.fmClearingV2='1';b.disabled=true;const old=b.textContent;b.textContent='Backing up & clearing…';
    clearCreator(b).catch(err=>{
      console.error('[FM clear v2] failed',err);
      window.__fmSeasonResetInProgress=false;
      b.disabled=false;b.dataset.fmClearingV2='0';b.textContent=old;
      alert(`Could not safely reset the shared season. Nothing has been cleared. ${err?.message||''}`.trim());
    });
  },true);

  window.FMCreatorClearV2={version:VERSION,clearLocalImport};
})();
