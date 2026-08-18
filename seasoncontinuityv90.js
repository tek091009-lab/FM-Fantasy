(()=>{
'use strict';
const VERSION='season-continuity-v90-world-boundary';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const clean=v=>String(v??'').trim();
function competition(p){return norm(p?.meta?.competition_code||p?.meta?.competition||'');}
function season(p){return clean(p?.meta?.season_start??p?.meta?.season??p?.meta?.season_id??'');}
function relation(next,old){
 const nc=competition(next),oc=competition(old),ns=season(next),os=season(old);
 const sameCompetition=!!nc&&!!oc&&nc===oc;
 const seasonKnown=!!ns&&!!os;
 const sameSeason=seasonKnown&&ns===os;
 return {same_competition:sameCompetition,season_known:seasonKnown,same_season:sameSeason,cross_season:sameCompetition&&seasonKnown&&!sameSeason,next_competition:nc||null,old_competition:oc||null,next_season:ns||null,old_season:os||null};
}
function install(){
 const c=window.FMCloud;
 if(!c||c.__seasonContinuityV90||typeof c.publishWorld!=='function'||typeof c.getWorld!=='function')return false;
 c.__seasonContinuityV90=true;
 const original=c.publishWorld.bind(c),originalGetWorld=c.getWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  const current=originalGetWorld?.(),old=current?.payload||null,r=relation(payload,old);
  if(payload&&typeof payload==='object'){
   payload.meta=payload.meta||{};
   payload.meta.season_continuity_v90={version:VERSION,policy:'competition+season boundary; cross-season imports must not inherit prior-season update/migration guards',...r};
  }
  if(!r.cross_season)return original(payload,...args);
  // Inner update/migration wrappers read FMCloud.getWorld() to obtain the previous
  // payload. For a confirmed same-competition/new-season boundary, expose no old
  // payload during this publish only, so prior-season GW/player/fixture checks cannot
  // be applied to the new season. The real world object is never mutated.
  c.getWorld=()=>current&&typeof current==='object'?{...current,payload:null}:current;
  try{return await original(payload,...args)}finally{c.getWorld=originalGetWorld;}
 };
 window.FMSeasonContinuityV90={version:VERSION,relation};
 return true;
}
window.FMSeasonContinuityV90={version:VERSION,relation};
window.addEventListener('fmcloudready',install);
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();
