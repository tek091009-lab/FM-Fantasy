(()=>{
'use strict';
const VERSION='world-update-preflight-v2-strict-state-structural-fixture-id';
const FUTURE=new Set(['future','upcoming','scheduled','postponed','cancelled','canceled','tbd']);
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const arr=v=>Array.isArray(v)?v:[];
function hasScore(v){return v!==null&&v!==undefined&&String(v).trim()!==''&&Number.isFinite(Number(v));}
function strictPlayed(f){
 const s=norm(f?.status);
 if(FUTURE.has(s))return false;
 if(s==='played'||s==='completed'||s==='complete'||s==='finished')return true;
 return hasScore(f?.home_score)&&hasScore(f?.away_score);
}
function team(v){return norm(v?.short_name||v?.name||v||'');}
function dateKey(v){return String(v??'').trim().slice(0,10);}
function gw(v){const n=Number(v??0);return Number.isFinite(n)?n:0;}
function score(v){return hasScore(v)?Number(v):null;}
function structuralKey(o){
 const home=team(o?.home??o?.home_team??o?.home_name),away=team(o?.away??o?.away_team??o?.away_name);
 const hs=score(o?.home_score),as=score(o?.away_score),d=dateKey(o?.date??o?.match_date??o?.kickoff),g=gw(o?.gameweek??o?.gw??o?.round_gameweek);
 if(!home||!away||hs===null||as===null||(!d&&!g))return '';
 return `${home}|${away}|${d}|gw${g}|${hs}-${as}`;
}
function normalize(payload){
 if(!payload||typeof payload!=='object')return {future_rows_sanitized:0,false_positive_risk:0,strict_played:0,structural_fixture_ids_assigned:0,structural_match_ids_assigned:0};
 const fixtures=arr(payload.fixtures),matches=arr(payload.matches);let sanitized=0,risk=0,played=0,fixtureAssigned=0,matchAssigned=0,ambiguousKeys=0;
 for(const f of fixtures){
  if(!f||typeof f!=='object')continue;
  const s=norm(f.status),explicitFuture=FUTURE.has(s);
  const loosePlayed=(f.home_score!==null&&f.home_score!==undefined&&f.away_score!==null&&f.away_score!==undefined);
  if(explicitFuture&&loosePlayed)risk++;
  if(explicitFuture&&(f.home_score!==null||f.away_score!==null)){
   f.home_score=null;f.away_score=null;sanitized++;
  }
  if(strictPlayed(f))played++;
 }
 // Only create structural IDs for uniquely-identifiable played fixtures. This lets
 // the existing strict update guard join rich match detail on schemas where FM does
 // not expose a stable fixture_id, without weakening fixture uniqueness.
 const byKey=new Map();
 for(const f of fixtures){
  if(!strictPlayed(f))continue;
  const raw=String(f?.fixture_id??f?.id??'').trim();if(raw)continue;
  const k=structuralKey(f);if(!k)continue;
  if(!byKey.has(k))byKey.set(k,[]);byKey.get(k).push(f);
 }
 for(const [k,rows] of byKey){
  if(rows.length!==1){ambiguousKeys++;continue}
  const id=`struct:${k}`;rows[0].fixture_id=id;fixtureAssigned++;
 }
 const fixtureIds=new Map();
 for(const f of fixtures){const id=String(f?.fixture_id??f?.id??'').trim(),k=structuralKey(f);if(id&&k&&!fixtureIds.has(k))fixtureIds.set(k,id);}
 for(const m of matches){
  if(!m||typeof m!=='object')continue;
  const raw=String(m?.fixture_id??'').trim();if(raw)continue;
  const k=structuralKey(m),id=k?fixtureIds.get(k):'';
  if(id){m.fixture_id=id;matchAssigned++;}
 }
 payload.meta=payload.meta||{};
 payload.meta.update_guard_fixture_evidence={
  version:VERSION,
  policy:'explicit-future-state-wins-plus-unique-structural-fixture-identity',
  future_rows_sanitized:sanitized,
  blank_or_placeholder_false_positive_risk:risk,
  strict_played_fixtures:played,
  structural_fixture_ids_assigned:fixtureAssigned,
  structural_match_ids_assigned:matchAssigned,
  ambiguous_structural_keys_rejected:ambiguousKeys
 };
 return payload.meta.update_guard_fixture_evidence;
}
function install(){
 const c=window.FMCloud;
 if(!c||c.__updateGuardPreflightV2||typeof c.publishWorld!=='function')return false;
 c.__updateGuardPreflightV2=true;
 const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload)normalize(payload);
  return original(payload,...args);
 };
 return true;
}
window.FMWorldUpdatePreflight={version:VERSION,normalize,strictPlayed,structuralKey};
window.addEventListener('fmcloudready',install);
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();
