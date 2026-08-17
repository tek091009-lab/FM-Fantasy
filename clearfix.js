(()=>{
  const RX_BTN=/^clear\s+(?:saved\s+)?database$/i;
  const RX_DB=/(fm|fantasy|world|save|import|database)/i;
  const RX_AUTH=/(supabase|auth|session|token|login|user)/i;
  const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));

  async function callFirst(names){
    for(const n of names){
      try{
        const fn=window[n];
        if(typeof fn==='function'){
          const r=fn();
          if(r&&typeof r.then==='function')await r;
          return n;
        }
      }catch(e){console.warn('[FM clear] helper failed',n,e)}
    }
    return null;
  }

  async function clearSharedWorld(){
    // Mark cleared before touching local state so every auto-loader stands down
    // immediately and stays down across the reload below.
    try{localStorage.setItem(CLEAR_KEY,'1')}catch(_){ }
    try{sessionStorage.setItem(CLEAR_KEY,'1')}catch(_){ }

    // For the creator, clearing the database also clears the canonical shared
    // payload in Supabase. publishWorld(null) updates worlds.payload to NULL;
    // accounts, memberships, join code and manager states are intentionally kept.
    try{
      if(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.()&&typeof window.FMCloud.publishWorld==='function'){
        await window.FMCloud.publishWorld(null);
      }
    }catch(e){
      console.error('[FM clear] shared payload clear failed',e);
      throw new Error('Could not clear the shared saved database. Please try again.');
    }
  }

  async function clearImportedWorld(){
    await clearSharedWorld();

    // Prefer the app's own storage API when available.
    const helper=await callFirst([
      'fmStoredClear','fmStoredDelete','fmClearStored','clearImportedDatabase',
      'deleteImportedDatabase','resetImportedDatabase','clearFmDatabase','clearFMDatabase'
    ]);

    // IndexedDB fallback. Imported-world DBs only; auth/session stores are excluded.
    try{
      if(indexedDB?.databases){
        const dbs=await indexedDB.databases();
        await Promise.all((dbs||[]).map(info=>new Promise(resolve=>{
          const name=String(info?.name||'');
          if(!name||!RX_DB.test(name)||RX_AUTH.test(name))return resolve();
          try{
            const req=indexedDB.deleteDatabase(name);
            req.onsuccess=req.onerror=req.onblocked=()=>resolve();
          }catch(_){resolve()}
        })));
      }
    }catch(e){console.warn('[FM clear] IndexedDB fallback failed',e)}

    // Remove only imported-world local/session keys; preserve Supabase/auth/account keys
    // and preserve CLEAR_KEY itself so the cloud loader remains suppressed after reload.
    for(const store of [localStorage,sessionStorage]){
      try{
        const doomed=[];
        for(let i=0;i<store.length;i++){
          const k=String(store.key(i)||'');
          if(!k||k===CLEAR_KEY||RX_AUTH.test(k))continue;
          if(/(fm|fantasy)/i.test(k)&&/(db|database|world|save|import|payload|fixture|player|history)/i.test(k))doomed.push(k);
        }
        doomed.forEach(k=>store.removeItem(k));
      }catch(e){console.warn('[FM clear] storage fallback failed',e)}
    }

    if(!helper&&typeof window.fmStoredSetLocalOnly==='function'){
      try{await window.fmStoredSetLocalOnly(null)}catch(e){console.warn('[FM clear] null setter fallback failed',e)}
    }

    try{if('caches' in window){for(const key of await caches.keys())if(/fm|fantasy/i.test(key))await caches.delete(key)}}catch(_){ }
    await sleep(80);
    location.reload();
  }

  function isClearButton(el){
    const b=el?.closest?.('button,[role="button"]');
    if(!b)return null;
    const t=String(b.textContent||'').trim().replace(/\s+/g,' ');
    return RX_BTN.test(t)?b:null;
  }

  document.addEventListener('click',e=>{
    const b=isClearButton(e.target);if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(b.dataset.fmClearing==='1')return;
    const cloud=!!window.FMCloud?.isCreator?.();
    const ok=window.confirm(cloud
      ?'Clear the imported FM database from this device AND remove the saved shared database? Your account, league and join code will be kept.'
      :'Clear the imported FM database from this device? Your account/login will be kept.');
    if(!ok)return;
    b.dataset.fmClearing='1';b.disabled=true;
    const old=b.textContent;b.textContent='Clearing…';
    clearImportedWorld().catch(err=>{
      console.error('[FM clear] failed',err);
      b.disabled=false;b.dataset.fmClearing='0';b.textContent=old;
      alert(err?.message||'Could not clear the FM database. Please export debug and send it over.');
    });
  },true);

  window.FMClearImportedDatabase=clearImportedWorld;
  window.FMCloudDatabaseClearKey=CLEAR_KEY;
})();
