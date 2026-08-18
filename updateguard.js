(()=>{
'use strict';
const VERSION='world-update-guard-v4-fixture-club-proof';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const num=v=>Number(v||0)||0;
const playerId=p=>String(p?.pid??p?.id??'');
const available=p=>p?.available!==false&&String(p?.available??'true')!=='false'&&String(p?.historical_only??'false')!=='true';
const fixtureGw=f=>num(f?.gameweek??f?.gw??f?.round_gameweek);
const fixturePlayed=f=>String(f?.status||'').toLowerCase()==='played'||(f?.home_score!==null&&f?.home_score!==undefined&&f?.away_score!==null&&f?.away_score!==undefined);
const fixtureId=f=>String(f?.fixture_id??f?.id??'');
const competitionKey=p=>norm(p?.meta?.competition_code||p?.meta?.competition||'');
const arr=v=>Array.isArray(v)?v:[];
function resolveCompleted(payload){
 const m=payload?.meta||{};let done=num(m.completed_gameweek),latest=Math.max(done,num(m.latest_gameweek_with_result));
 for(let gw=done+1;gw<=latest;gw++){
  const rows=arr(payload?.fixtures).filter(f=>fixtureGw(f)===gw);
  if(!rows.length||rows.every(fixturePlayed)){done=gw;continue}break;
 }
 return done;
}
function normaliseProgress(payload){
 if(!payload?.meta)return;const done=resolveCompleted(payload);if(!done)return;
 payload.meta.completed_gameweek=done;payload.meta.current_gameweek=done+1;payload.meta.next_gameweek=done+1;
 payload.meta.progress_source='fixture_completion_with_blank_gameweeks';
}
function matchScoreValid(m){
 const h=arr(m?.home_players),a=arr(m?.away_players);
 const hg=h.reduce((n,r)=>n+num(r?.goals),0)+a.reduce((n,r)=>n+num(r?.own_goals),0);
 const ag=a.reduce((n,r)=>n+num(r?.goals),0)+h.reduce((n,r)=>n+num(r?.own_goals),0);
 return hg===num(m?.home_score)&&ag===num(m?.away_score);
}
function matchIdentityValid(m){
 const h=arr(m?.home_players),a=arr(m?.away_players);
 if(h.length<11||h.length>25||a.length<11||a.length>25)return false;
 const hi=h.map(r=>String(r?.player_id??'')),ai=a.map(r=>String(r?.player_id??''));
 if(hi.some(x=>!x)||ai.some(x=>!x))return false;
 if(new Set(hi).size!==hi.length||new Set(ai).size!==ai.length)return false;
 const hs=new Set(hi);if(ai.some(x=>hs.has(x)))return false;
 return matchScoreValid(m);
}
function validateFixtureClubProof(meta,clubs,errors){
 if(meta.fixture_club_mapping_policy!=='current-squad-validated-shift-v73'){
  errors.push('v73 current-squad fixture→club mapping proof is missing');return;
 }
 const ev=meta.fixture_club_mapping_evidence;
 if(!ev||typeof ev!=='object'){errors.push('v73 fixture→club mapping evidence is missing');return}
 if(num(ev.team_count)!==clubs.length||num(ev.safe_squad_clubs)!==clubs.length){errors.push(`v73 fixture→club proof covers ${num(ev.safe_squad_clubs)}/${clubs.length} safe current squads`);return}
 const proofNames=new Set(arr(ev.mapped_clubs).map(norm).filter(Boolean));
 const clubNames=new Set(clubs.map(c=>norm(c?.short_name||c?.name)).filter(Boolean));
 if(proofNames.size!==clubNames.size||[...clubNames].some(x=>!proofNames.has(x)))errors.push('v73 fixture→club proof does not match the published club set');
 if(arr(ev.unsafe_squad_names).length)errors.push(`v73 fixture→club proof still contains unsafe squads: ${arr(ev.unsafe_squad_names).join(', ')}`);
}
function validate(payload,oldPayload){
 const errors=[],warnings=[];const players=arr(payload?.players),clubs=arr(payload?.clubs),matches=arr(payload?.matches),fixtures=arr(payload?.fixtures),meta=payload?.meta||{};
 if(meta.current_squad_identity_policy!=='strict-db-membership-only-no-history-mutation-v68')errors.push('legacy current-squad identity decoder detected');
 if(meta.rich_match_validation_policy!=='official-score-plus-strict-current-cohort-v69')errors.push('v69 retained-match validation is missing');
 validateFixtureClubProof(meta,clubs,errors);
 if(players.length<20)errors.push(`player population collapsed to ${players.length}`);
 if(clubs.length<2)errors.push(`club population collapsed to ${clubs.length}`);
 const ids=new Set();let missingIds=0,duplicates=0;
 for(const p of players){const id=playerId(p);if(!id){missingIds++;continue}if(ids.has(id))duplicates++;ids.add(id)}
 if(missingIds)errors.push(`${missingIds} player records have no stable ID`);if(duplicates)errors.push(`${duplicates} duplicate player IDs`);
 const clubMap=new Map();for(const c of clubs){for(const n of [c?.short_name,c?.name].filter(Boolean))clubMap.set(norm(n),c)}
 let unknownClub=0,eidMismatch=0;const currentClubCounts=new Map();
 for(const p of players){if(!available(p))continue;const nk=norm(p.club),c=clubMap.get(nk);currentClubCounts.set(nk,(currentClubCounts.get(nk)||0)+1);if(!c){unknownClub++;continue}if(p.club_eid!==null&&p.club_eid!==undefined&&String(p.club_eid)!==''&&c.eid!==null&&c.eid!==undefined&&String(p.club_eid)!==String(c.eid))eidMismatch++}
 if(unknownClub)errors.push(`${unknownClub} available players map to no current club`);if(eidMismatch)errors.push(`${eidMismatch} available players have a club-name/club-ID mismatch`);
 for(const c of clubs){const names=[c?.short_name,c?.name].map(norm).filter(Boolean),n=Math.max(...names.map(x=>currentClubCounts.get(x)||0),0);if(n<12||n>45)errors.push(`${c?.short_name||c?.name||'club'} has an unsafe current squad size of ${n}`)}
 let badMatchIdentity=0,badMatchScore=0;const matchFixtureIds=new Set(),duplicateMatchFixtures=[];
 for(const m of matches){const fid=fixtureId(m);if(fid){if(matchFixtureIds.has(fid))duplicateMatchFixtures.push(fid);matchFixtureIds.add(fid)}const h=arr(m?.home_players),a=arr(m?.away_players);if(h.length<11||h.length>25||a.length<11||a.length>25)badMatchIdentity++;else {const hi=h.map(r=>String(r?.player_id??'')),ai=a.map(r=>String(r?.player_id??'')),hs=new Set(hi);if(hi.some(x=>!x)||ai.some(x=>!x)||new Set(hi).size!==hi.length||new Set(ai).size!==ai.length||ai.some(x=>hs.has(x)))badMatchIdentity++}if(!matchScoreValid(m))badMatchScore++}
 if(badMatchIdentity)errors.push(`${badMatchIdentity} retained matches have impossible player-side identity`);
 if(badMatchScore)errors.push(`${badMatchScore} retained matches do not reproduce the official score from player goals`);
 if(duplicateMatchFixtures.length)errors.push(`${duplicateMatchFixtures.length} duplicate retained match-detail rows target an already-used fixture`);
 const old=oldPayload&&Array.isArray(oldPayload.players)?oldPayload:null;
 const sameWorld=!!old&&competitionKey(old)!==''&&competitionKey(old)===competitionKey(payload);
 const oldDone=sameWorld?num(old?.meta?.completed_gameweek):0,newDone=num(meta.completed_gameweek);
 const newCompletedPlayed=fixtures.filter(f=>fixturePlayed(f)&&fixtureGw(f)>oldDone&&fixtureGw(f)<=newDone);
 const missingDetail=newCompletedPlayed.filter(f=>!matchFixtureIds.has(fixtureId(f)));
 if(missingDetail.length)errors.push(`${missingDetail.length} newly completed fixtures have no validated player-level match detail`);
 if(sameWorld){
  const oldLatest=num(old.meta?.latest_gameweek_with_result),newLatest=num(meta.latest_gameweek_with_result);if(newLatest<oldLatest&&newDone<=oldDone)errors.push(`latest result Gameweek regressed ${oldLatest} → ${newLatest}`);
  if(newDone<oldDone)errors.push(`completed Gameweek regressed ${oldDone} → ${newDone}`);
  const om=new Map(old.players.filter(available).map(p=>[playerId(p),p])),nm=new Map(players.filter(available).map(p=>[playerId(p),p]));
  if(nm.size<Math.floor(om.size*.75))errors.push(`available player population collapsed ${om.size} → ${nm.size}`);
  if(players.length<Math.floor(old.players.length*.75))errors.push(`total player population collapsed ${old.players.length} → ${players.length}`);
  let moved=0,posChanged=0;for(const [id,p] of nm){const o=om.get(id);if(!o)continue;if(norm(o.club)!==norm(p.club))moved++;if(String(o.pos||'')!==String(p.pos||''))posChanged++}
  const moveLimit=Math.max(30,Math.ceil(om.size*.05));if(moved>moveLimit)errors.push(`${moved} existing players changed current club in one update (limit ${moveLimit})`);
  const posLimit=Math.max(20,Math.ceil(om.size*.04));if(posChanged>posLimit)errors.push(`${posChanged} existing players changed fantasy position in one update (limit ${posLimit})`);
  const oldCounts=new Map(),newCounts=new Map();for(const p of om.values())oldCounts.set(norm(p.club),(oldCounts.get(norm(p.club))||0)+1);for(const p of nm.values())newCounts.set(norm(p.club),(newCounts.get(norm(p.club))||0)+1);
  for(const [club,n] of oldCounts){const now=newCounts.get(club)||0;if(n>=15&&now<Math.floor(n*.55))errors.push(`${club} available squad collapsed ${n} → ${now}`)}
 }
 try{
  if(typeof state!=='undefined'){
   const protectedIds=new Set([...(Array.isArray(state?.squad)?state.squad:[]),...(Array.isArray(state?.lockedSquad)?state.lockedSquad:[])].map(String));
   const all=new Set(players.map(playerId));const missing=[...protectedIds].filter(id=>!all.has(id));if(missing.length)errors.push(`current manager has ${missing.length} protected player IDs missing from the new world`)
  }
 }catch(_e){}
 return {ok:!errors.length,version:VERSION,errors,warnings,summary:{players:players.length,clubs:clubs.length,matches:matches.length,completed_gameweek:newDone,current_gameweek:num(meta.current_gameweek),latest_result_gameweek:num(meta.latest_gameweek_with_result)}};
}
async function restoreLocal(payload){
 if(!payload)return;
 try{
  const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('FMFantasyStandalone',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('imports'))r.result.createObjectStore('imports')};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
  await new Promise((resolve,reject)=>{const t=db.transaction('imports','readwrite');t.objectStore('imports').put(payload,'championship');t.oncomplete=resolve;t.onerror=()=>reject(t.error)});
 }catch(e){console.warn('Could not restore previous local FM world after blocked update',e)}
 try{const w=window.FMCloud?.getWorld?.();if(w)w.payload=payload}catch(_e){}
 try{if(typeof applyImportedPayload==='function')applyImportedPayload(payload,'load')}catch(_e){}
}
function install(){
 const c=window.FMCloud;if(!c||c.__worldUpdateGuardV4||typeof c.publishWorld!=='function')return false;c.__worldUpdateGuardV4=true;
 const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload==null)return original(payload,...args);
  const world=c.getWorld?.(),old=world?.payload||null;normaliseProgress(payload);const result=validate(payload,old);payload.meta=payload.meta||{};payload.meta.update_validation=result;
  if(!result.ok){await restoreLocal(old);throw new Error(`FM update blocked before publish: ${result.errors.join(' · ')}`)}
  try{return await original(payload,...args)}catch(e){await restoreLocal(old);throw e}
 };
 window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};return true;
}
window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>30)clearInterval(timer)},250);
})();
