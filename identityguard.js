(()=>{
  'use strict';
  const VERSION='identity-guard-v3-diagnostic-only';
  const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
  const representedClub=h=>{
    const v=String(h?.venue||'').toUpperCase();
    if(v==='H')return h?.home||null;
    if(v==='A')return h?.away||null;
    const opp=norm(h?.opponent);
    if(opp&&norm(h?.home)===opp)return h?.away||null;
    if(opp&&norm(h?.away)===opp)return h?.home||null;
    return null;
  };
  function inspectPlayer(p){
    const history=Array.isArray(p?.history)?p.history:[];
    const byDate=new Map();
    for(const r of history){
      const date=String(r?.date||''),club=representedClub(r);
      if(!date||!club)continue;
      const set=byDate.get(date)||new Set();set.add(norm(club));byDate.set(date,set);
    }
    let conflicts=0;for(const set of byDate.values())if(set.size>1)conflicts++;
    return conflicts;
  }
  function audit(payload){
    const players=Array.isArray(payload?.players)?payload.players:[];
    let playersWithConflicts=0,sameDateCrossClubConflicts=0;
    for(const p of players){const n=inspectPlayer(p);if(n){playersWithConflicts++;sameDateCrossClubConflicts+=n}}
    return {
      version:VERSION,
      policy:'Diagnostic only. Browser-side identity evidence must never mutate current club, history, weekly points, aggregates, price or availability. Current squad identity comes only from the importer/current save snapshot.',
      players_with_history_conflicts:playersWithConflicts,
      same_date_cross_club_conflicts:sameDateCrossClubConflicts,
      current_club_rewrites:0,
      history_rows_deleted:0,
      aggregate_recalculations:0
    };
  }
  function sanitizePayload(payload){
    // Compatibility API only: deliberately return the exact payload untouched.
    try{window.FM_IDENTITY_AUDIT=audit(payload)}catch(_e){}
    return payload;
  }
  function runtimePass(){
    try{
      let players=[];try{if(typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS))players=PLAYERS}catch(_e){}
      const result=audit({players});window.FM_IDENTITY_AUDIT=result;
      try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG)FM_DEBUG.identityGuardV3=result}catch(_e){}
      return result;
    }catch(e){console.warn('FM identity audit failed',e);return null}
  }
  window.FMIdentityGuard={sanitizePayload,audit,runtimePass,version:VERSION};
  window.addEventListener('fmcloudready',()=>setTimeout(runtimePass,0),{once:true});
  setTimeout(runtimePass,1200);
})();
