(()=>{
  const VERSION='identity-guard-v1';
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
  const histKey=h=>`${h?.date||''}|${h?.home||''}|${h?.away||''}|${h?.opponent||''}|${h?.venue||''}`;
  const clubObj=(clubs,name)=>{
    const n=norm(name);if(!n)return null;
    return (clubs||[]).find(c=>norm(c?.name)===n||norm(c?.short_name)===n)||null;
  };
  const recalc=(p,removed)=>{
    const h=Array.isArray(p.history)?p.history:[];
    const num=(r,k)=>Number(r?.[k]||0);
    p.apps=h.filter(r=>num(r,'minutes')>0).length;
    p.minutes=h.reduce((a,r)=>a+num(r,'minutes'),0);
    p.goals=h.reduce((a,r)=>a+num(r,'goals'),0);
    p.assists=h.reduce((a,r)=>a+num(r,'assists'),0);
    p.saves=h.reduce((a,r)=>a+num(r,'saves'),0);
    p.yc=h.reduce((a,r)=>a+num(r,'yc'),0);
    p.rc=h.reduce((a,r)=>a+num(r,'rc'),0);
    p.gc=h.reduce((a,r)=>a+num(r,'gc'),0);
    p.fantasy_points=h.reduce((a,r)=>a+num(r,'fpl_points'),0);
    p.points=p.fantasy_points;
    if(Number.isFinite(Number(p.starts))&&removed>0)p.starts=Math.max(0,Number(p.starts)-removed);
    const weekly={};
    for(const r of h){const gw=Number(r?.gameweek||0);if(gw>0)weekly[gw]=(weekly[gw]||0)+num(r,'fpl_points')}
    p.weekly_points=weekly;
    const rated=h.filter(r=>Number(r?.rating||0)>0);
    if(rated.length)p.avg_rating=Math.round((rated.reduce((a,r)=>a+Number(r.rating||0),0)/rated.length)*100)/100;
    if(p.price_tracker&&Array.isArray(p.price_tracker.processedHistoryKeys))p.price_tracker.processedHistoryKeys=[...new Set(h.map(histKey))].slice(-80);
    if(p.retained_history_evidence){
      const dated=h.filter(r=>r?.date).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
      p.retained_history_evidence.decoded_rows=h.length;
      p.retained_history_evidence.decoded_gameweeks=[...new Set(h.map(r=>Number(r?.gameweek||0)).filter(Boolean))].sort((a,b)=>a-b);
      p.retained_history_evidence.first_decoded_date=dated[0]?.date||null;
      p.retained_history_evidence.last_decoded_date=dated.at(-1)?.date||null;
    }
  };
  function sanitizePlayer(p,clubs){
    if(!p||!Array.isArray(p.history)||p.history.length<2)return false;
    const original=p.history;
    const byDate=new Map();
    original.forEach((r,i)=>{const d=String(r?.date||'');const c=representedClub(r);if(!d||!c)return;const a=byDate.get(d)||[];a.push({r,i,c});byDate.set(d,a)});
    let keep=new Set(original.map((_,i)=>i)),conflict=false;
    for(const [date,rows] of byDate){
      const clubsHere=[...new Set(rows.map(x=>norm(x.c)))];
      if(clubsHere.length<2)continue;
      conflict=true;
      const outside=original.map((r,i)=>({r,i,c:representedClub(r)})).filter(x=>keep.has(x.i)&&String(x.r?.date||'')!==date&&x.c);
      const before=outside.filter(x=>String(x.r.date)<date).sort((a,b)=>String(b.r.date).localeCompare(String(a.r.date)))[0];
      const after=outside.filter(x=>String(x.r.date)>date).sort((a,b)=>String(a.r.date).localeCompare(String(b.r.date)))[0];
      const counts=new Map();outside.forEach(x=>counts.set(norm(x.c),(counts.get(norm(x.c))||0)+1));
      let winner=null,best=-1e9;
      for(const x of rows){const n=norm(x.c);let score=(counts.get(n)||0);if(before&&norm(before.c)===n)score+=4;if(after&&norm(after.c)===n)score+=4;if(score>best){best=score;winner=n}}
      for(const x of rows)if(norm(x.c)!==winner)keep.delete(x.i);
    }
    if(!conflict)return false;
    const cleaned=original.filter((_,i)=>keep.has(i));
    const removed=original.length-cleaned.length;
    if(!removed)return false;
    p.history=cleaned;
    const dated=cleaned.filter(r=>r?.date&&representedClub(r)).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
    const latestClub=dated.length?representedClub(dated.at(-1)):null;
    const oldClub=p.club;
    if(latestClub&&norm(latestClub)!==norm(oldClub)){
      const c=clubObj(clubs,latestClub);
      p.club=c?.short_name||latestClub;
      p.club_full=c?.name||latestClub;
      if(c?.eid!=null)p.club_eid=c.eid;
      if(c?.uid!=null)p.club_uid=c.uid;
    }
    recalc(p,removed);
    p.club_identity_evidence={source:VERSION,corrected:true,previous_club:oldClub,current_club:p.club,removed_cross_club_rows:removed,reason:'impossible same-date appearances for multiple clubs'};
    return true;
  }
  function sanitizePayload(payload){
    if(!payload||!Array.isArray(payload.players))return payload;
    let changed=0;for(const p of payload.players)if(sanitizePlayer(p,payload.clubs||[]))changed++;
    payload.meta=payload.meta||{};
    if(changed)payload.meta.player_identity_guard={version:VERSION,corrected_players:changed};
    return payload;
  }
  function runtimePass(){
    try{
      if(typeof PLAYERS==='undefined'||!Array.isArray(PLAYERS))return;
      let clubs=[];try{if(typeof CLUBS!=='undefined'&&Array.isArray(CLUBS))clubs=CLUBS}catch(_e){}
      let changed=0;for(const p of PLAYERS)if(sanitizePlayer(p,clubs))changed++;
      if(!changed)return;
      try{typeof refreshClubFilters==='function'&&refreshClubFilters()}catch(_e){}
      for(const fn of ['renderTeam','renderTransferPitch','renderMarket','renderStats'])try{typeof globalThis[fn]==='function'&&globalThis[fn]()}catch(_e){}
    }catch(e){console.warn('FM identity guard runtime pass failed',e)}
  }
  function wrapCloud(){
    try{
      const c=window.FMCloud;if(!c||c.__identityGuardV1)return false;c.__identityGuardV1=true;
      if(typeof c.loadWorld==='function'){const f=c.loadWorld.bind(c);c.loadWorld=async(...a)=>sanitizePayload(await f(...a))}
      if(typeof c.publishWorld==='function'){const f=c.publishWorld.bind(c);c.publishWorld=async(payload,...a)=>f(sanitizePayload(payload),...a)}
      return true;
    }catch(e){console.warn('FM identity guard cloud wrap failed',e);return false}
  }
  window.FMIdentityGuard={sanitizePayload,runtimePass,version:VERSION};
  window.addEventListener('fmcloudready',()=>{wrapCloud();runtimePass()});
  let tries=0;const t=setInterval(()=>{tries++;wrapCloud();runtimePass();if(tries>=30)clearInterval(t)},500);
})();
