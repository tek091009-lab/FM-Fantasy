(()=>{
  const ID='fmCloudDbControls';
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  function note(text,bad=false){const el=document.getElementById('fmCloudDbStatus');if(el){el.textContent=text;el.style.color=bad?'#ff7b9e':'#b8ffd9';}}
  async function waitReady(){for(let i=0;i<80;i++){if(window.FMCloud?.ready?.())return true;await sleep(250)}return false}
  async function forceLoad(){try{if(!(await waitReady()))throw new Error('Cloud account is not ready yet.');note('Loading saved database…');const payload=await window.FMCloud.loadWorld();if(!payload)throw new Error('No shared FM database has been saved yet.');if(typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(payload);if(typeof applyImportedPayload==='function')applyImportedPayload(payload,'load');else if(typeof loadServerImportState==='function')await loadServerImportState();if(window.FMCloud.managerState&&typeof state!=='undefined'&&typeof DEFAULT!=='undefined'){state=Object.assign({},DEFAULT,window.FMCloud.managerState);state.chips=state.chips||JSON.parse(JSON.stringify(DEFAULT.chips))}if(typeof fmProcessCompletedGameweeks==='function')fmProcessCompletedGameweeks();if(typeof renderAll==='function')renderAll();note(`Loaded ${payload?.meta?.players||payload?.players?.length||''} players from shared database.`);return payload}catch(e){console.error('Manual cloud database load failed',e);note(e?.message||'Could not load saved database.',true);throw e}}
  async function forceSave(){try{if(!(await waitReady()))throw new Error('Cloud account is not ready yet.');if(!window.FMCloud.isCreator?.())throw new Error('Only the FPL Creator can save the shared database.');note('Saving database to cloud…');let payload=null;if(typeof fmStoredGet==='function')payload=await fmStoredGet();if(!payload)throw new Error('No imported FM database is currently available to save.');await window.FMCloud.publishWorld(payload);note(`Database saved · ${payload?.meta?.players||payload?.players?.length||''} players.`);return payload}catch(e){console.error('Manual cloud database save failed',e);note(e?.message||'Could not save database.',true);throw e}}
  function findImportAnchor(){
    const all=[...document.querySelectorAll('button,a,[role="button"],label,div')];
    const exact=all.find(el=>/^import(\s+fm|\s+database|\s+save)?$/i.test((el.textContent||'').trim()));
    if(exact)return exact;
    return all.find(el=>/import/i.test((el.textContent||'').trim())&&((el.closest('aside,.sidebar,nav,[class*="side"]'))||el.getBoundingClientRect().left<330))||null;
  }
  function mount(){
    if(document.getElementById(ID))return;
    const wrap=document.createElement('div');wrap.id=ID;
    wrap.style.cssText='display:flex;flex-direction:column;gap:7px;width:100%;margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.09);font:700 11px/1.25 Inter,system-ui,sans-serif;color:#fff;box-sizing:border-box';
    const mk=label=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.style.cssText='width:100%;border:1px solid rgba(255,255,255,.12);border-radius:9px;padding:8px 9px;background:rgba(111,53,255,.16);color:#fff;font-weight:850;cursor:pointer;text-align:left';return b};
    if(window.FMCloud?.isCreator?.()){const save=mk('Save Database');save.onclick=()=>forceSave().catch(()=>{});wrap.appendChild(save)}
    const load=mk('Load Saved Database');load.onclick=()=>forceLoad().catch(()=>{});wrap.appendChild(load);
    const status=document.createElement('div');status.id='fmCloudDbStatus';status.style.cssText='color:#9189ad;font-weight:650;font-size:10px;padding:1px 2px 0';status.textContent=window.FMCloud?.isCreator?.()?'Shared creator database':'Shared database';wrap.appendChild(status);
    const anchor=findImportAnchor();
    if(anchor){const host=anchor.parentElement||anchor;host.insertBefore(wrap,anchor.nextSibling)}
    else{const side=document.querySelector('aside,.sidebar,[class*="sidebar"],nav');(side||document.body).appendChild(wrap)}
  }
  window.FMCloudDatabase={save:forceSave,load:forceLoad};
  window.addEventListener('fmcloudready',()=>{mount();setTimeout(()=>forceLoad().catch(()=>{}),250)});
  (async()=>{if(await waitReady()){mount();setTimeout(()=>forceLoad().catch(()=>{}),250)}})();
})();
