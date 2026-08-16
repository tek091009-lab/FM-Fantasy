(()=>{
  const ID='fmCloudDbControls';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  function note(text,bad=false){
    const el=document.getElementById('fmCloudDbStatus');
    if(el){el.textContent=text;el.style.color=bad?'#ff7b9e':'#b8ffd9';}
  }
  async function waitReady(){
    for(let i=0;i<80;i++){
      if(window.FMCloud?.ready?.()) return true;
      await sleep(250);
    }
    return false;
  }
  async function forceLoad(){
    try{
      if(!(await waitReady())) throw new Error('Cloud account is not ready yet.');
      note('Loading saved database…');
      const payload=await window.FMCloud.loadWorld();
      if(!payload) throw new Error('No shared FM database has been saved yet.');
      if(typeof fmStoredSetLocalOnly==='function') await fmStoredSetLocalOnly(payload);
      if(typeof applyImportedPayload==='function') applyImportedPayload(payload,'load');
      else if(typeof loadServerImportState==='function') await loadServerImportState();
      if(window.FMCloud.managerState && typeof state!=='undefined' && typeof DEFAULT!=='undefined'){
        state=Object.assign({},DEFAULT,window.FMCloud.managerState);
        state.chips=state.chips||JSON.parse(JSON.stringify(DEFAULT.chips));
      }
      if(typeof fmProcessCompletedGameweeks==='function') fmProcessCompletedGameweeks();
      if(typeof renderAll==='function') renderAll();
      note(`Loaded ${payload?.meta?.players||payload?.players?.length||''} players from shared database.`);
      return payload;
    }catch(e){
      console.error('Manual cloud database load failed',e);
      note(e?.message||'Could not load saved database.',true);
      throw e;
    }
  }
  async function forceSave(){
    try{
      if(!(await waitReady())) throw new Error('Cloud account is not ready yet.');
      if(!window.FMCloud.isCreator?.()) throw new Error('Only the FPL Creator can save the shared database.');
      note('Saving database to cloud…');
      let payload=null;
      if(typeof fmStoredGet==='function') payload=await fmStoredGet();
      if(!payload) throw new Error('No imported FM database is currently available to save.');
      await window.FMCloud.publishWorld(payload);
      note(`Database saved · ${payload?.meta?.players||payload?.players?.length||''} players.`);
      return payload;
    }catch(e){
      console.error('Manual cloud database save failed',e);
      note(e?.message||'Could not save database.',true);
      throw e;
    }
  }
  function mount(){
    if(document.getElementById(ID)) return;
    const wrap=document.createElement('div');
    wrap.id=ID;
    wrap.style.cssText='position:fixed;right:18px;bottom:18px;z-index:99998;display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 12px;border:1px solid rgba(255,255,255,.14);border-radius:14px;background:rgba(15,8,38,.94);box-shadow:0 14px 34px rgba(0,0,0,.35);backdrop-filter:blur(12px);font:700 12px/1.2 Inter,system-ui,sans-serif;color:#fff';
    const mk=(label)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.style.cssText='border:0;border-radius:10px;padding:9px 12px;background:linear-gradient(135deg,#6f35ff,#ef3f94);color:#fff;font-weight:900;cursor:pointer';return b};
    const load=mk('Load Saved Database');
    load.onclick=()=>forceLoad().catch(()=>{});
    wrap.appendChild(load);
    if(window.FMCloud?.isCreator?.()){
      const save=mk('Save Database');
      save.onclick=()=>forceSave().catch(()=>{});
      wrap.insertBefore(save,load);
    }
    const status=document.createElement('span');status.id='fmCloudDbStatus';status.style.cssText='max-width:230px;color:#a9a1c6;font-weight:700';status.textContent=window.FMCloud?.isCreator?.()?'Creator cloud database controls':'Shared database controls';wrap.appendChild(status);
    document.body.appendChild(wrap);
  }
  window.FMCloudDatabase={save:forceSave,load:forceLoad};
  window.addEventListener('fmcloudready',()=>{mount();setTimeout(()=>forceLoad().catch(()=>{}),250)});
  (async()=>{if(await waitReady()){mount();setTimeout(()=>forceLoad().catch(()=>{}),250)}})();
})();
