(()=>{
'use strict';
const VERSION='world-update-guard-v8-history-aware';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const num=v=>Number(v||0)||0;
const arr=v=>Array.isArray(v)?v:[];
const fixtureGw=f=>num(f?.gameweek??f?.gw??f?.round_gameweek);
const fixturePlayed=f=>String(f?.status||'').toLowerCase()==='played'||(f?.home_score!==null&&f?.home_score!==undefined&&f?.away_score!==null&&f?.away_score!==undefined);
const fixtureId=f=>String(f?.fixture_id??f?.id??'');
const competitionKey=p=>norm(p?.meta?.competition_code||p?.meta?.competition||'');
const dateKey=x=>String(x?.date||'').slice(0,10);
function teamName(x,side){return norm(x?.[side]??x?.[side+'_team']??x?.[side+'_name']??x?.[side+'_club']??'')}
function stableFixtureKey(x){const h=teamName(x,'home'),a=teamName(x,'away');if(!h||!a)return '';return `${h}|${a}|${dateKey(x)}|${num(x?.home_score)}-${num(x?.away_score)}`}
function matchScoreValid(m){const h=arr(m?.home_players),a=arr(m?.away_players),hg=h.reduce((z,r)=>z+num(r?.goals),0)+a.reduce((z,r)=>z+num(r?.own_goals),0),ag=a.reduce((z,r)=>z+num(r?.goals),0)+h.reduce((z,r)=>z+num(r?.own_goals),0);return hg===num(m?.home_score)&&ag===num(m?.away_score)}
function matchIdentityValid(m){const h=arr(m?.home_players),a=arr(m?.away_players);if(h.length<11||h.length>25||a.length<11||a.length>25)return false;const hi=h.map(r=>String(r?.player_id??'')),ai=a.map(r=>String(r?.player_id??'')),hs=new Set(hi);return !(hi.some(x=>!x)||ai.some(x=>!x)||new Set(hi).size!==hi.length||new Set(ai).size!==ai.length||ai.some(x=>hs.has(x)))}
function contentKey(m){const side=s=>arr(s).map(r=>String(r?.player_id??'')).sort().join(',');return `${fixtureId(m)}|${stableFixtureKey(m)}|${side(m?.home_players)}|${side(m?.away_players)}`}
function resolveCompleted(payload){const meta=payload?.meta||{};let done=num(meta.completed_gameweek),latest=Math.max(done,num(meta.latest_gameweek_with_result));for(let gw=done+1;gw<=latest;gw++){const rows=arr(payload?.fixtures).filter(f=>fixtureGw(f)===gw);if(!rows.length||rows.every(fixturePlayed)){done=gw;continue}break}return done}
function normaliseProgress(payload){if(!payload?.meta)return;const done=resolveCompleted(payload);if(!done)return;payload.meta.completed_gameweek=done;payload.meta.current_gameweek=done+1;payload.meta.next_gameweek=done+1;payload.meta.progress_source='fixture_completion_with_blank_gameweeks'}
function validate(payload,oldPayload){
 const errors=[],warnings=[],matches=arr(payload?.matches),fixtures=arr(payload?.fixtures),meta=payload?.meta||{};
 const old=oldPayload&&Array.isArray(oldPayload.players)?oldPayload:null;
 const sameWorld=!!old&&competitionKey(old)!==''&&competitionKey(old)===competitionKey(payload);
 const oldDone=sameWorld?num(old?.meta?.completed_gameweek):0,newDone=num(meta.completed_gameweek);
 const oldById=new Map(),oldByStable=new Map();
 for(const m of arr(old?.matches)){const id=fixtureId(m),sk=stableFixtureKey(m);if(id)oldById.set(id,m);if(sk)oldByStable.set(sk,m)}
 const ids=new Set(),stable=new Set();let newOrChanged=0,badIdentity=0,badScore=0,dupes=0,trusted=0;
 for(const m of matches){
   const id=fixtureId(m),sk=stableFixtureKey(m);if(id){if(ids.has(id))dupes++;ids.add(id)}if(sk)stable.add(sk);
   const prev=(id&&oldById.get(id))||(sk&&oldByStable.get(sk))||null;
   if(sameWorld&&prev&&contentKey(prev)===contentKey(m)){trusted++;continue}
   newOrChanged++;if(!matchIdentityValid(m))badIdentity++;if(!matchScoreValid(m))badScore++;
 }
 if(badIdentity)errors.push(`${badIdentity} new/changed matches have impossible player-side identity`);
 if(badScore)errors.push(`${badScore} new/changed matches do not reproduce the official score from player goals`);
 if(dupes)errors.push(`${dupes} duplicate match-detail rows target the same raw fixture ID`);
 const hasDetail=f=>{const id=fixtureId(f),sk=stableFixtureKey(f);return !!((id&&ids.has(id))||(sk&&stable.has(sk)))};
 const newlyCompleted=fixtures.filter(f=>fixturePlayed(f)&&fixtureGw(f)>oldDone&&fixtureGw(f)<=newDone);
 const missing=newlyCompleted.filter(f=>!hasDetail(f));
 if(missing.length)errors.push(`${missing.length} newly completed fixtures have no validated player-level match detail`);
 if(sameWorld){const oldLatest=num(old?.meta?.latest_gameweek_with_result),newLatest=num(meta.latest_gameweek_with_result);if(newDone<oldDone)errors.push(`completed Gameweek regressed ${oldDone} → ${newDone}`);if(newLatest<oldLatest&&newDone<=oldDone)errors.push(`latest result Gameweek regressed ${oldLatest} → ${newLatest}`)}
 if(trusted)warnings.push(`${trusted} unchanged previously-published match-detail rows trusted without revalidation`);
 return {ok:!errors.length,version:VERSION,errors,warnings,summary:{matches:matches.length,trusted_historical_matches:trusted,new_or_changed_matches:newOrChanged,newly_completed_fixtures:newlyCompleted.length,missing_new_detail:missing.length,completed_gameweek:newDone,current_gameweek:num(meta.current_gameweek),latest_result_gameweek:num(meta.latest_gameweek_with_result),history_status:meta.history_coverage_status||null,rich_matches_missing:num(meta.rich_matches_missing)}};
}
async function restoreCanonical(){try{if(window.FMAtomicImportRollback?.restoreCanonical)return await window.FMAtomicImportRollback.restoreCanonical();if(typeof window.FMCloud?.loadWorld==='function'){const p=await window.FMCloud.loadWorld(true);if(p&&typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(p);if(p&&typeof applyImportedPayload==='function')applyImportedPayload(p,'load');return p}}catch(e){console.warn('Could not restore canonical world after blocked update',e)}return null}
function install(){const cloud=window.FMCloud;if(!cloud||cloud.__worldUpdateGuardV8||typeof cloud.publishWorld!=='function')return false;cloud.__worldUpdateGuardV8=true;const original=cloud.publishWorld.bind(cloud);cloud.publishWorld=async(payload,...args)=>{if(payload==null)return original(payload,...args);const old=JSON.parse(JSON.stringify(cloud.getWorld?.()?.payload||null));normaliseProgress(payload);const result=validate(payload,old);payload.meta=payload.meta||{};payload.meta.update_validation=result;if(!result.ok){await restoreCanonical();throw new Error(`FM update blocked before publish: ${result.errors.join(' · ')}`)}if(result.warnings.length)console.warn('FM update validation warnings:',result.warnings);try{return await original(payload,...args)}catch(e){await restoreCanonical();throw e}};window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};return true}
window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();