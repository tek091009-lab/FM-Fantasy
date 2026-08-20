(()=>{
  const ID='fmCloudDbControls';
  const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const wasCleared=()=>{try{return localStorage.getItem(CLEAR_KEY)==='1'||sessionStorage.getItem(CLEAR_KEY)==='1'}catch(_){return false}};
  const markActive=()=>{try{localStorage.removeItem(CLEAR_KEY);sessionStorage.removeItem(CLEAR_KEY)}catch(_){}};
  function note(text,bad=false){const el=document.getElementById('fmCloudDbStatus');if(el){el.textContent=text;el.style.color=bad?'#ff7b9e':'#b8ffd9';}}
  function syncLoadedStatus(){
    const payload=window.FMCloud?.getWorld?.()?.payload;
    if(!payload||!Array.isArray(payload.players))return false;
    const n=Number(payload?.meta?.players||payload.players.length||0);
    const syncBox=document.querySelector('.sidebar .syncbox')||document.querySelector('.syncbox');
    if(syncBox){
      for(const el of syncBox.querySelectorAll('*')){
        const t=String(el.textContent||'').trim();
        if(/^No FM save imported yet\.?$/i.test(t))el.textContent=n?`FM database loaded · ${n} players`:'FM database loaded';
      }
    }
    note(n?`Loaded ${n} players from shared database.`:'Shared database loaded.');
    return true;
  }
  async function waitReady(){for(let i=0;i<80;i++){if(window.FMCloud?.ready?.())return true;await sleep(250)}return false}
  async function forceLoad(){try{if(!(await waitReady()))throw new Error('Cloud account is not ready yet.');if(wasCleared())throw new Error('No shared FM database is saved. Import and save a new database first.');note('Loading saved database…');const payload=await window.FMCloud.loadWorld(true);if(!payload)throw new Error('No shared FM database has been saved yet.');if(typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(payload);if(typeof applyImportedPayload==='function')applyImportedPayload(payload,'load');else if(typeof loadServerImportState==='function')await loadServerImportState();if(window.FMCloud.managerState&&typeof state!=='undefined'&&typeof DEFAULT!=='undefined'){state=Object.assign({},DEFAULT,window.FMCloud.managerState);state.chips=state.chips||JSON.parse(JSON.stringify(DEFAULT.chips))}if(typeof fmProcessCompletedGameweeks==='function')fmProcessCompletedGameweeks();if(typeof renderAll==='function')renderAll();syncLoadedStatus();return payload}catch(e){console.error('Manual cloud database load failed',e);note(e?.message||'Could not load saved database.',true);throw e}}
  async function forceSave(){try{if(!(await waitReady()))throw new Error('Cloud account is not ready yet.');if(!window.FMCloud.isCreator?.())throw new Error('Only the FPL Creator can save the shared database.');note('Saving database to cloud…');let payload=null;if(typeof fmStoredGet==='function')payload=await fmStoredGet();if(!payload)throw new Error('No imported FM database is currently available to save.');await window.FMCloud.publishWorld(payload);markActive();note(`Database saved · ${payload?.meta?.players||payload?.players?.length||''} players.`);return payload}catch(e){console.error('Manual cloud database save failed',e);note(e?.message||'Could not save database.',true);throw e}}
  async function undoLastImport(){
    try{
      if(!(await waitReady()))throw new Error('Cloud account is not ready yet.');
      if(!window.FMCloud.isCreator?.())throw new Error('Only the FPL Creator can undo an import.');
      const world=window.FMCloud.getWorld?.();if(!world?.id)throw new Error('Shared world is not ready.');
      if(!confirm('Undo the most recent successful FM import? This restores the exact world from immediately before that import.'))return;
      const cfg=window.FM_FANTASY_CONFIG||{};if(!cfg.supabaseUrl||!cfg.supabaseAnonKey||!window.supabase)throw new Error('Cloud connection is not ready.');
      note('Undoing last import…');
      const client=window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
      const {data:ses,error:se}=await client.auth.getSession();if(se||!ses?.session)throw new Error('Creator session is not ready.');
      const {error}=await client.rpc('fmfantasy_undo_last_import',{p_world_id:world.id});if(error)throw error;
      try{localStorage.removeItem(`fmFantasyWorldVersion:${world.id}`)}catch(_e){}
      note('Last import undone. Reloading…');
      location.reload();
    }catch(e){console.error('Undo Last Import failed',e);note(e?.message||'Could not undo the last import.',true);alert(e?.message||'Could not undo the last import.');throw e}
  }
  function mount(){
    if(document.getElementById(ID))return true;
    if(!window.FMCloud?.ready?.())return false;
    const syncBox=document.querySelector('.sidebar .syncbox')||document.querySelector('.syncbox');
    const syncBtns=syncBox?.querySelector('.syncBtns');
    if(!syncBox||!syncBtns)return false;
    const wrap=document.createElement('div');wrap.id=ID;wrap.style.cssText='display:grid;grid-template-columns:1fr;gap:7px;margin-top:7px';
    const mk=label=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.className='syncBtn';return b};
    if(window.FMCloud?.isCreator?.()){
      const save=mk('Save Database');save.onclick=()=>forceSave().catch(()=>{});wrap.appendChild(save);
      const undo=mk('Undo Last Import');undo.id='fmUndoLastImportBtn';undo.style.cssText='border-color:#ff8aaa;color:#ffd7e3';undo.onclick=()=>undoLastImport().catch(()=>{});wrap.appendChild(undo);
    }
    const load=mk('Load Saved Database');load.onclick=()=>forceLoad().catch(()=>{});wrap.appendChild(load);
    const status=document.createElement('div');status.id='fmCloudDbStatus';status.className='syncStatus';status.style.marginTop='1px';status.textContent=wasCleared()?'No shared database saved':(window.FMCloud?.isCreator?.()?'Shared creator database':'Shared database');wrap.appendChild(status);
    syncBtns.insertAdjacentElement('afterend',wrap);
    syncLoadedStatus();
    return true;
  }
  function activate(){
    if(!window.FMCloud?.ready?.())return;
    if(!mount()){let tries=0;const timer=setInterval(()=>{tries++;if(mount()||tries>=20)clearInterval(timer)},250)}
    syncLoadedStatus();
  }
  window.FMCloudDatabase={save:forceSave,load:forceLoad,undoLastImport,markActive,syncLoadedStatus};
  window.addEventListener('fmcloudready',activate);
  if(window.FMCloud?.ready?.())activate();
})();
