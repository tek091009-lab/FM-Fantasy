(()=>{
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 const ids=a=>(Array.isArray(a)?a:[]).map(String);
 const sameSquad=(a,b)=>{const x=ids(a),y=ids(b);if(x.length!==15||y.length!==15)return false;const s=new Set(x);return y.every(id=>s.has(id));};
 function latestMatchingSnapshot(st){
   const gl=st?.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{};
   const keys=Object.keys(gl).map(Number).filter(Number.isFinite).sort((a,b)=>b-a);
   for(const gw of keys){const snap=gl[String(gw)]||gl[gw];if(!snap)continue;if(ids(snap.starters).length!==11||ids(snap.bench).length!==4)continue;if(!sameSquad(st.squad,snap.squad))continue;return clone(snap)}
   return null;
 }
 function repair(){
   try{
     if(typeof state==='undefined'||!state?.teamConfirmed)return false;
     if(ids(state.squad).length!==15)return false; // Clear Draft intentionally empties squad; never undo it.
     if(ids(state.starters).length===11&&ids(state.bench).length===4)return false;
     const snap=latestMatchingSnapshot(state);if(!snap)return false;
     const squadSet=new Set(ids(state.squad));
     state.starters=ids(snap.starters);state.bench=ids(snap.bench);
     if(!state.captain||!squadSet.has(String(state.captain)))state.captain=snap.captain||null;
     if(!state.vice||!squadSet.has(String(state.vice)))state.vice=snap.vice||null;
     if(window.FMCloud?.managerState){window.FMCloud.managerState.starters=[...state.starters];window.FMCloud.managerState.bench=[...state.bench];window.FMCloud.managerState.captain=state.captain;window.FMCloud.managerState.vice=state.vice}
     try{if(typeof save==='function')save();else window.FMCloud?.queueManagerSave?.(state)}catch(_e){}
     try{if(typeof renderAll==='function')renderAll();else if(typeof renderTeam==='function')renderTeam()}catch(_e){}
     window.dispatchEvent(new CustomEvent('fmteamstatehydrated',{detail:{source:'latest_matching_gameweek_lineup'}}));
     return true;
   }catch(e){console.warn('[FM team state guard]',e);return false}
 }
 window.fmRepairWorkingTeam=repair;
 window.addEventListener('fmcloudready',()=>setTimeout(repair,80));
 window.addEventListener('focus',()=>setTimeout(repair,80));
 setTimeout(repair,1200);
})();
