(()=>{
  const RX_BTN=/^clear\s+(?:saved\s+)?database$/i;
  const RX_DB=/(fm|fantasy|world|save|import|database)/i;
  const RX_AUTH=/(supabase|auth|session|token|login|user)/i;
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

  async function clearImportedWorld(){
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

    // Remove only imported-world local/session keys; preserve Supabase/auth/account keys.
    for(const store of [localStorage,sessionStorage]){
      try{
        const doomed=[];
        for(let i=0;i<store.length;i++){
          const k=String(store.key(i)||'');
          if(!k||RX_AUTH.test(k))continue;
          if(/(fm|fantasy)/i.test(k)&&/(db|database|world|save|import|payload|fixture|player|history)/i.test(k))doomed.push(k);
        }
        doomed.forEach(k=>store.removeItem(k));
      }catch(e){console.warn('[FM clear] storage fallback failed',e)}
    }

    // A few builds expose a setter but no clearer. Null it only as a last resort.
    if(!helper&&typeof window.fmStoredSetLocalOnly==='function'){
      try{await window.fmStoredSetLocalOnly(null)}catch(e){console.warn('[FM clear] null setter fallback failed',e)}
    }

    // Prevent a service-worker-controlled reload from immediately restoring stale app state.
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

  // Capture phase deliberately beats the broken bundled handler.
  document.addEventListener('click',e=>{
    const b=isClearButton(e.target);if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(b.dataset.fmClearing==='1')return;
    const ok=window.confirm('Clear the imported FM database from this device? Your account/login will be kept.');
    if(!ok)return;
    b.dataset.fmClearing='1';b.disabled=true;
    const old=b.textContent;b.textContent='Clearing…';
    clearImportedWorld().catch(err=>{
      console.error('[FM clear] failed',err);
      b.disabled=false;b.dataset.fmClearing='0';b.textContent=old;
      alert('Could not clear the local FM database. Please export debug and send it over.');
    });
  },true);

  window.FMClearImportedDatabase=clearImportedWorld;
})();
