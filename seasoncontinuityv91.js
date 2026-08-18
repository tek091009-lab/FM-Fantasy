(()=>{
'use strict';
const VERSION='season-continuity-v91-canonical-start';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const clean=v=>String(v??'').trim();
const validYear=y=>Number.isInteger(y)&&y>=1900&&y<=2200;
function yearFrom(v){
 if(v===null||v===undefined||v==='')return null;
 if(typeof v==='number'&&validYear(Math.trunc(v)))return Math.trunc(v);
 const s=clean(v);
 const m=s.match(/(?:^|\D)(19\d{2}|20\d{2}|21\d{2}|2200)(?:\D|$)/);
 return m&&validYear(Number(m[1]))?Number(m[1]):null;
}
function competition(p){return norm(p?.meta?.competition_code||p?.meta?.competition||'');}
function seasonEvidence(p){
 const m=p?.meta||{};
 const ordered=[
  ['season_start',m.season_start],
  ['season_year',m.season_year],
  ['season_name',m.season_name],
  ['season',m.season]
 ];
 for(const [field,value] of ordered){
  const y=yearFrom(value);
  if(y!==null)return {canonical_start_year:y,source_field:field,source_value:clean(value),confidence:'year_anchor'};
 }
 // season_id is often an opaque FM entity ID. Only accept it when it is itself a
 // plausible four-digit year; otherwise retain it as raw evidence, never chronology.
 const idYear=yearFrom(m.season_id);
 if(idYear!==null&&/^\d{4}$/.test(clean(m.season_id)))return {canonical_start_year:idYear,source_field:'season_id',source_value:clean(m.season_id),confidence:'year_like_season_id'};
 return {canonical_start_year:null,source_field:null,source_value:null,confidence:'unknown',raw_season_id:clean(m.season_id)||null};
}
function relation(next,old){
 const nc=competition(next),oc=competition(old),ne=seasonEvidence(next),oe=seasonEvidence(old);
 const sameCompetition=!!nc&&!!oc&&nc===oc;
 const bothCanonical=ne.canonical_start_year!==null&&oe.canonical_start_year!==null;
 const sameSeason=bothCanonical&&ne.canonical_start_year===oe.canonical_start_year;
 const crossSeason=sameCompetition&&bothCanonical&&!sameSeason;
 return {
  same_competition:sameCompetition,
  season_known:bothCanonical,
  same_season:sameSeason,
  cross_season:crossSeason,
  next_competition:nc||null,
  old_competition:oc||null,
  next_season_start:ne.canonical_start_year,
  old_season_start:oe.canonical_start_year,
  next_season_evidence:ne,
  old_season_evidence:oe,
  policy:'cross-season only when both payloads expose disagreeing canonical start-year evidence; raw formatting and opaque season IDs cannot trigger a rollover'
 };
}
function install(){
 const c=window.FMCloud;
 if(!c||c.__seasonContinuityV91||typeof c.publishWorld!=='function'||typeof c.getWorld!=='function')return false;
 c.__seasonContinuityV91=true;
 const original=c.publishWorld.bind(c),originalGetWorld=c.getWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  const current=originalGetWorld?.(),old=current?.payload||null,r=relation(payload,old);
  if(payload&&typeof payload==='object'){
   payload.meta=payload.meta||{};
   payload.meta.season_continuity_v91={version:VERSION,...r};
  }
  if(!r.cross_season)return original(payload,...args);
  // Confirmed same-competition/new-season boundary. Hide the prior payload from the
  // inner weekly-update/migration guards for this publish only; never mutate storage.
  c.getWorld=()=>current&&typeof current==='object'?{...current,payload:null}:current;
  try{return await original(payload,...args)}finally{c.getWorld=originalGetWorld;}
 };
 window.FMSeasonContinuityV91={version:VERSION,relation,seasonEvidence,yearFrom};
 return true;
}
window.FMSeasonContinuityV91={version:VERSION,relation,seasonEvidence,yearFrom};
window.addEventListener('fmcloudready',install);
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();
