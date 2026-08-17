(()=>{
  const copy=v=>JSON.parse(JSON.stringify(v));
  const ids=v=>Array.isArray(v)?v.map(String):[];
  const validSnap=s=>!!s&&ids(s.squad).length===15&&ids(s.starters).length===11&&ids(s.bench).length===4;
  function latestLineup(){if(typeof state==='undefined'||!state?.gameweekLineups||typeof state.gameweekLineups!=='object')return null;const keys=Object.keys(state.gameweekLineups).map(Number).filter(Number.isFinite).sort((a,b)=>b-a);for(const gw of keys){const x=state.gameweekLineups[String(gw)]||state.gameweekLineups[gw];if(validSnap(x))return copy(x)}return null;}
  function snapshotCurrent(){
    if(typeof state==='undefined')return null;
    const snap={squad:ids(state.squad),starters:ids(state.starters),bench:ids(state.bench),captain:state.captain?String(state.captain):null,vice:state.vice?String(state.vice):null,bank:Number(state.bank||0),currentGameweek:Number(state.currentGameweek||0),savedAt:new Date().toISOString()};
    if(validSnap(snap)){state.fmDraftBackup=snap;return snap}
    return validSnap(state.fmDraftBackup)?state.fmDraftBackup:null;
  }
  function rebuildFromLocked(){
    if(typeof state==='undefined')return null;const locked=ids(state.lockedSquad);if(locked.length!==15)return null;const prev=latestLineup();
    if(!prev)return null;
    const current=new Set(locked),prevSquad=ids(prev.squad),newcomers=locked.filter(x=>!prevSquad.includes(x));let ni=0;const used=new Set();
    const mapSlot=id=>{id=String(id);if(current.has(id)&&!used.has(id)){used.add(id);return id}while(ni<newcomers.length&&used.has(newcomers[ni]))ni++;if(ni<newcomers.length){const n=newcomers[ni++];used.add(n);return n}return null};
    let starters=ids(prev.starters).map(mapSlot).filter(Boolean),bench=ids(prev.bench).map(mapSlot).filter(Boolean);for(const id of locked)if(!used.has(id)){if(starters.length<11)starters.push(id);else if(bench.length<4)bench.push(id);used.add(id)}starters=starters.slice(0,11);bench=bench.filter(x=>!starters.includes(x)).slice(0,4);for(const id of locked)if(!starters.includes(id)&&!bench.includes(id)&&bench.length<4)bench.push(id);
    const out={squad:locked,starters,bench,captain:prev.captain&&current.has(String(prev.captain))?String(prev.captain):null,vice:prev.vice&&current.has(String(prev.vice))?String(prev.vice):null,bank:Number(state.lockedBank??state.bank??0)};return validSnap(out)?out:null;
  }
  function recovery(){if(typeof state==='undefined')return null;return validSnap(state.fmDraftBackup)?copy(state.fmDraftBackup):rebuildFromLocked();}
  function restoreTeam(button){const r=recovery();if(!validSnap(r))return false;state.squad=ids(r.squad);state.starters=ids(r.starters);state.bench=ids(r.bench);state.captain=r.captain?String(r.captain):null;state.vice=r.vice?String(r.vice):null;if(Number.isFinite(Number(r.bank)))state.bank=Number(r.bank);state.fmDraftBackup=copy(r);try{if(typeof save==='function')save()}catch(_e){}try{window.FMCloud?.queueManagerSave?.(state)}catch(_e){}try{if(typeof renderAll==='function')renderAll()}catch(_e){}if(button){const t=button.textContent;button.textContent='Restored ✓';setTimeout(()=>button.textContent=t,900)}return true;}
  function label(el){return String(el?.textContent||'').replace(/\s+/g,' ').trim().toLowerCase()}
  document.addEventListener('click',e=>{const b=e.target?.closest?.('button,[role="button"],a');if(!b)return;const t=label(b);if(t==='clear draft'){snapshotCurrent();return}if(t==='restore team'&&typeof state!=='undefined'&&state?.teamConfirmed&&!validSnap(state)){if(restoreTeam(b)){e.preventDefault();e.stopImmediatePropagation()}}},true);
  window.fmRestoreClearedDraft=()=>restoreTeam(document.querySelector('button'));
})();