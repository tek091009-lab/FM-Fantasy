(()=>{
  const VERSION='identity-guard-v2';
  const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
  const same=(a,b)=>String(a??'')!==''&&String(b??'')!==''&&String(a)===String(b);
  const representedClub=h=>{
    const v=String(h?.venue||'').toUpperCase();
    if(v==='H')return h?.home||null;
    if(v==='A')return h?.away||null;
    const opp=norm(h?.opponent);
    if(opp&&norm(h?.home)===opp)return h?.away||null;
    if(opp&&norm(h?.away)===opp)return h?.home||null;
    return null;
  };
  const histKey=h=>`${h?.date||''}|${h?.home||''}|${h?.away||''}|${h?.opponent||''}|${h?.venue||''}`;
  const clubObj=(clubs,name)=>{const n=norm(name);if(!n)return null;return (clubs||[]).find(c=>norm(c?.name)===n||norm(c?.short_name)===n)||null};
  const globals=()=>{
    let matches=[],fixtures=[];
    try{if(typeof MATCHES!=='undefined'&&Array.isArray(MATCHES))matches=MATCHES}catch(_e){}
    try{if(typeof SEASON_FIXTURES!=='undefined'&&Array.isArray(SEASON_FIXTURES))fixtures=SEASON_FIXTURES}catch(_e){}
    return {matches,fixtures};
  };
  const rowHardLink=(r,c,env)=>{
    const matchId=r?.match_id??r?.matchId??null, fixtureId=r?.fixture_id??r?.fixtureId??null;
    if(matchId!=null&&String(matchId)!==''){
      const hits=env.matches.filter(m=>same(m?.id,matchId)||same(m?.match_id,matchId));
      if(hits.length===1){const m=hits[0],clubs=[m?.home,m?.away,m?.home_team,m?.away_team].map(norm).filter(Boolean);if(clubs.includes(norm(c)))return {kind:'match_id',value:String(matchId)}}
    }
    if(fixtureId!=null&&String(fixtureId)!==''){
      const hits=env.fixtures.filter(f=>same(f?.fixture_id,fixtureId)||same(f?.id,fixtureId));
      if(hits.length===1){const f=hits[0],clubs=[f?.home,f?.away,f?.home_team,f?.away_team].map(norm).filter(Boolean);if(clubs.includes(norm(c)))return {kind:'fixture_id',value:String(fixtureId)}}
    }
    return null;
  };
  const recalc=p=>{
    const h=Array.isArray(p.history)?p.history:[],num=(r,k)=>Number(r?.[k]||0);
    p.apps=h.filter(r=>num(r,'minutes')>0).length;p.minutes=h.reduce((a,r)=>a+num(r,'minutes'),0);p.goals=h.reduce((a,r)=>a+num(r,'goals'),0);p.assists=h.reduce((a,r)=>a+num(r,'assists'),0);p.saves=h.reduce((a,r)=>a+num(r,'saves'),0);p.yc=h.reduce((a,r)=>a+num(r,'yc'),0);p.rc=h.reduce((a,r)=>a+num(r,'rc'),0);p.gc=h.reduce((a,r)=>a+num(r,'gc'),0);p.fantasy_points=h.reduce((a,r)=>a+num(r,'fpl_points'),0);p.points=p.fantasy_points;
    const weekly={};for(const r of h){const gw=Number(r?.gameweek||0);if(gw>0)weekly[gw]=(weekly[gw]||0)+num(r,'fpl_points')}p.weekly_points=weekly;
    const rated=h.filter(r=>Number(r?.rating||0)>0);if(rated.length)p.avg_rating=Math.round((rated.reduce((a,r)=>a+Number(r.rating||0),0)/rated.length)*100)/100;
    if(p.price_tracker&&Array.isArray(p.price_tracker.processedHistoryKeys))p.price_tracker.processedHistoryKeys=[...new Set(h.map(histKey))].slice(-80);
    if(p.retained_history_evidence){const dated=h.filter(r=>r?.date).sort((a,b)=>String(a.date).localeCompare(String(b.date)));p.retained_history_evidence.decoded_rows=h.length;p.retained_history_evidence.decoded_gameweeks=[...new Set(h.map(r=>Number(r?.gameweek||0)).filter(Boolean))].sort((a,b)=>a-b);p.retained_history_evidence.first_decoded_date=dated[0]?.date||null;p.retained_history_evidence.last_decoded_date=dated.at(-1)?.date||null}
  };
  function sanitizePlayer(p,clubs,env){
    if(!p||!Array.isArray(p.history)||p.history.length<2)return {changed:false,conflicts:0,unresolved:0,hardResolved:0};
    const original=p.history,byDate=new Map();
    original.forEach((r,i)=>{const d=String(r?.date||''),c=representedClub(r);if(!d||!c)return;const a=byDate.get(d)||[];a.push({r,i,c});byDate.set(d,a)});
    const keep=new Set(original.map((_,i)=>i)),evidence=[];let conflicts=0,unresolved=0,hardResolved=0;
    for(const [date,rows] of byDate){
      const clubsHere=[...new Set(rows.map(x=>norm(x.c)))];if(clubsHere.length<2)continue;conflicts++;
      const linked=rows.map(x=>({...x,link:rowHardLink(x.r,x.c,env)})).filter(x=>x.link);
      const linkedClubs=[...new Set(linked.map(x=>norm(x.c)))];
      if(linked.length===1&&linkedClubs.length===1){
        const winner=norm(linked[0].c);for(const x of rows)if(norm(x.c)!==winner)keep.delete(x.i);hardResolved++;
        evidence.push({date,status:'hard_resolved',club:linked[0].c,link:linked[0].link,rejected:rows.filter(x=>norm(x.c)!==winner).map(x=>x.c)});
      }else{
        unresolved++;
        evidence.push({date,status:'unresolved_preserved',clubs:rows.map(x=>x.c),hard_links:linked.map(x=>({club:x.c,...x.link})),reason:linked.length>1?'conflicting hard links':'no unique exact match/fixture link'});
      }
    }
    if(!conflicts)return {changed:false,conflicts:0,unresolved:0,hardResolved:0};
    const removed=original.length-keep.size;
    p.history_identity_conflicts=evidence;
    p.history_identity_evidence={source:VERSION,policy:'Never delete same-date cross-club history from heuristic voting. Correct only when exactly one row has a unique exact match_id/fixture_id link; otherwise preserve all rows and mark aggregates untrusted.',conflicts,hard_resolved:hardResolved,unresolved_preserved:unresolved,removed_rows:removed};
    if(unresolved){p.history_aggregate_trust='conflict_unresolved';if(p.retained_history_evidence)p.retained_history_evidence.history_is_partial_or_unknown=true}
    if(!removed)return {changed:false,conflicts,unresolved,hardResolved};
    p.history=original.filter((_,i)=>keep.has(i));recalc(p);
    const dated=p.history.filter(r=>r?.date&&representedClub(r)).sort((a,b)=>String(a.date).localeCompare(String(b.date))),latestClub=dated.length?representedClub(dated.at(-1)):null,oldClub=p.club;
    if(latestClub&&norm(latestClub)!==norm(oldClub)){const c=clubObj(clubs,latestClub);p.club=c?.short_name||latestClub;p.club_full=c?.name||latestClub;if(c?.eid!=null)p.club_eid=c.eid;if(c?.uid!=null)p.club_uid=c.uid}
    p.club_identity_evidence={source:VERSION,corrected:true,previous_club:oldClub,current_club:p.club,removed_cross_club_rows:removed,reason:'unique exact retained match/fixture linkage only'};
    return {changed:true,conflicts,unresolved,hardResolved};
  }
  function sanitizePayload(payload){
    if(!payload||!Array.isArray(payload.players))return payload;const env=globals();let changed=0,conflicts=0,unresolved=0,hardResolved=0;
    for(const p of payload.players){const r=sanitizePlayer(p,payload.clubs||[],env);if(r.changed)changed++;conflicts+=r.conflicts;unresolved+=r.unresolved;hardResolved+=r.hardResolved}
    payload.meta=payload.meta||{};payload.meta.player_identity_guard={version:VERSION,corrected_players:changed,same_date_cross_club_conflicts:conflicts,hard_resolved_conflicts:hardResolved,unresolved_conflicts_preserved:unresolved,speculative_row_deletions:0};
    if(unresolved){const gaps=Array.isArray(payload.meta.unresolved_capabilities)?payload.meta.unresolved_capabilities:[];if(!gaps.includes('historical_player_club_identity_conflict'))gaps.push('historical_player_club_identity_conflict');payload.meta.unresolved_capabilities=gaps}
    return payload;
  }
  function runtimePass(){try{if(typeof PLAYERS==='undefined'||!Array.isArray(PLAYERS))return;let clubs=[];try{if(typeof CLUBS!=='undefined'&&Array.isArray(CLUBS))clubs=CLUBS}catch(_e){}const env=globals();let changed=0,unresolved=0;for(const p of PLAYERS){const r=sanitizePlayer(p,clubs,env);if(r.changed)changed++;unresolved+=r.unresolved}try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG)FM_DEBUG.identityGuardV2={changed_players:changed,unresolved_conflicts_preserved:unresolved,speculative_row_deletions:0}}catch(_e){}if(!changed)return;try{typeof refreshClubFilters==='function'&&refreshClubFilters()}catch(_e){}for(const fn of ['renderTeam','renderTransferPitch','renderMarket','renderStats'])try{typeof globalThis[fn]==='function'&&globalThis[fn]()}catch(_e){}}catch(e){console.warn('FM identity guard runtime pass failed',e)}}
  function wrapCloud(){try{const c=window.FMCloud;if(!c||c.__identityGuardV2)return false;c.__identityGuardV2=true;if(typeof c.loadWorld==='function'){const f=c.loadWorld.bind(c);c.loadWorld=async(...a)=>sanitizePayload(await f(...a))}if(typeof c.publishWorld==='function'){const f=c.publishWorld.bind(c);c.publishWorld=async(payload,...a)=>f(sanitizePayload(payload),...a)}return true}catch(e){console.warn('FM identity guard cloud wrap failed',e);return false}}
  window.FMIdentityGuard={sanitizePayload,runtimePass,version:VERSION};window.addEventListener('fmcloudready',()=>{wrapCloud();runtimePass()});let tries=0;const t=setInterval(()=>{tries++;wrapCloud();runtimePass();if(tries>=30)clearInterval(t)},500);
})();
