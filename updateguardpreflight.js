(()=>{
'use strict';
const VERSION='world-update-preflight-v1-strict-fixture-state';
const FUTURE=new Set(['future','upcoming','scheduled','postponed','cancelled','canceled','tbd']);
const norm=v=>String(v??'').trim().toLowerCase();
const arr=v=>Array.isArray(v)?v:[];
function hasScore(v){return v!==null&&v!==undefined&&String(v).trim()!==''&&Number.isFinite(Number(v));}
function strictPlayed(f){
 const s=norm(f?.status);
 if(FUTURE.has(s))return false;
 if(s==='played'||s==='completed'||s==='complete'||s==='finished')return true;
 return hasScore(f?.home_score)&&hasScore(f?.away_score);
}
function normalize(payload){
 if(!payload||typeof payload!=='object')return {future_rows_sanitized:0,false_positive_risk:0,strict_played:0};
 const fixtures=arr(payload.fixtures);let sanitized=0,risk=0,played=0;
 for(const f of fixtures){
  if(!f||typeof f!=='object')continue;
  const s=norm(f.status),explicitFuture=FUTURE.has(s);
  const loosePlayed=(f.home_score!==null&&f.home_score!==undefined&&f.away_score!==null&&f.away_score!==undefined);
  if(explicitFuture&&loosePlayed)risk++;
  if(explicitFuture&&(f.home_score!==null||f.away_score!==null)){
   // Future placeholders are not results. Clearing them prevents downstream guards
   // from treating schema-specific 0/0 or blank placeholders as played matches.
   f.home_score=null;f.away_score=null;sanitized++;
  }
  if(strictPlayed(f))played++;
 }
 payload.meta=payload.meta||{};
 payload.meta.update_guard_fixture_evidence={
  version:VERSION,
  policy:'explicit-future-state-wins-over-score-placeholders',
  future_rows_sanitized:sanitized,
  blank_or_placeholder_false_positive_risk:risk,
  strict_played_fixtures:played
 };
 return payload.meta.update_guard_fixture_evidence;
}
function install(){
 const c=window.FMCloud;
 if(!c||c.__updateGuardPreflightV1||typeof c.publishWorld!=='function')return false;
 c.__updateGuardPreflightV1=true;
 const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload)normalize(payload);
  return original(payload,...args);
 };
 return true;
}
window.FMWorldUpdatePreflight={version:VERSION,normalize,strictPlayed};
window.addEventListener('fmcloudready',install);
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();
