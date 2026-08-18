(()=>{
'use strict';
const VERSION='world-update-guard-v7-explicit-season-partial';
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
function selectedCurrentCandidate(meta){
 const targetShift=num(meta?.fixture_to_club_shift),targetComp=num(meta?.competition_fixture_id);
 const candidates=arr(meta?.current_season_candidates).filter(c=>c&&typeof c==='object'&&!c.error);
 return candidates.find(c=>num(c.shift)===targetShift&&(!targetComp||!num(c.competition_id)||num(c.competition_id)===targetComp))
   || candidates.find(c=>num(c.shift)===targetShift)
   || candidates.find(c=>num(c.expected_name_overlap)===arr(c.mapped_clubs).length&&arr(c.mapped_clubs).length>0)
   || null;
}
function sameClubSet(proofNames,clubs){
 const clubNames=new Set(clubs.map(c=>norm(c?.short_name||c?.name)).filter(Boolean));
 return proofNames.size===clubNames.size&&[...clubNames].every(x=>proofNames.has(x));
}
function validateFixtureClubProof(meta,clubs,errors,warnings){
 let ev=meta?.fixture_club_mapping_evidence||null;
 let source='root';
 if(!ev||typeof ev!=='object'){
  const c=selectedCurrentCandidate(meta);
  if(c){ev=c;source='selected-current-season-candidate'}
 }
 if(!ev||typeof ev!=='object'){errors.push('current-squad fixture→club mapping evidence is missing');return}
 if(num(ev.team_count)!==clubs.length||num(ev.safe_squad_clubs)!==clubs.length){
  errors.push(`fixture→club proof covers ${num(ev.safe_squad_clubs)}/${clubs.length} safe current squads`);return;
 }
 const proofNames=new Set(arr(ev.mapped_clubs).map(norm).filter(Boolean));
 if(!sameClubSet(proofNames,clubs)){errors.push('fixture→club proof does not match the published club set');return}
 if(arr(ev.unsafe_squad_names).length){errors.push(`fixture→club proof still contains unsafe squads: ${arr(ev.unsafe_squad_names).join(', ')}`);return}
 const acceptedPolicy=meta?.fixture_club_mapping_policy==='current-squad-validated-shift-v73'
  || String(ev?.mapping_proof||'').includes('current-db-roster-proof-v79')
  || String(ev?.mapping_proof||'').includes('current-squad');
 if(!acceptedPolicy)warnings.push('fixture→club proof passed structurally but has no canonical policy marker');
 if(source!=='root')warnings.push('fixture→club proof recovered from the selected current-season candidate diagnostics');
}
function activeImportMode(meta){
 const explicit=norm(meta?.import_mode||meta?.importMode||'');
 if(explicit)return explicit;
 try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){return ''}
}
function validate(payload,oldPayload){
 const errors=[],warnings=[];const players=arr(payload?.players),clubs=arr(payload?.clubs),matches=arr(payload?.matches),fixtures=arr(payload?.fixtures),meta=payload?.meta||{};
 const importMode=activeImportMode(meta);
 const candidate=selectedCurrentCandidate(meta);
 const squadPolicyOk=meta.current_squad_identity_policy==='strict-db-membership-only-no-history-mutation-v68'
   || candidate?.squad_policy==='strict_current_db_membership_only_v68'
   || String(candidate?.squad_resolution_policy||'').includes('no-history');
 if(!squadPolicyOk)errors.push('strict current-squad identity proof is missing');
 const sizePolicyOk=meta.current_squad_size_policy==='strict-current-db-extended-12-60-v79'
   || candidate?.current_squad_size_policy==='strict-current-db-extended-12-60-v79';
 if(!sizePolicyOk)warnings.push('v79 squad-size policy marker is absent; structural squad-size validation will be authoritative');
 if(meta.rich_match_validation_policy!=='official-score-plus-strict-current-cohort-v69'){
  warnings.push('v69 rich-match policy marker is absent; guard is validating every retained match structurally');
 }
 validateFixtureClubProof(meta,clubs,errors,warnings);
 if(players.length<20)errors.push(`player population collapsed to ${players.length}`);
 if(clubs.length<2)errors.push(`club population collapsed to ${clubs.length}`);
 const ids=new Set();let missingIds=0,duplicates=0;
 for(const p of players){const id=playerId(p);if(!id){missingIds++;continue}if(ids.has(id))duplicates++;ids.add(id)}
 if(missingIds)errors.push(`${missingIds} player records have no stable ID`);if(duplicates)errors.push(`${duplicates} duplicate player IDs`);
 const clubMap=new Map();for(const c of clubs){for(const n of [c?.short_name,c?.name].filter(Boolean))clubMap.set(norm(n),c)}
 let unknownClub=0,eidMismatch=0;const currentClubCounts=new Map();
 for(const p of players){if(!available(p))continue;const nk=norm(p.club),c=clubMap.get(nk);currentClubCounts.set(nk,(currentClubCounts.get(nk)||0)+1);if(!c){unknownClub++;continue}if(p.club_eid!==null&&p.club_eid!==undefined&&String(p.club_eid)!==''&&c.eid!==null&&c.eid!==undefined&&String(p.club_eid)!==String(c.eid))eidMismatch++}
 if(unknownClub)errors.push(`${unknownClub} available players map to no current club`);if(eidMismatch)errors.push(`${eidMismatch} available players have a club-name/club-ID mismatch`);
 for(const c of clubs){const names=[c?.short_name,c?.name].map(norm).filter(Boolean),n=Math.max(...names.map(x=>currentClubCounts.get(x)||0),0);if(n<12||n>60)errors.push(`${c?.short_name||c?.name||'club'} has an unsafe current squad size of ${n}`)}
 let badMatchIdentity=0,badMatchScore=0;const matchFixtureIds=new Set(),duplicateMatchFixtures=[];
 for(const m of matches){
  const fid=fixtureId(m);if(fid){if(matchFixtureIds.has(fid))duplicateMatchFixtures.push(fid);matchFixtureIds.add(fid)}
  const h=arr(m?.home_players),a=arr(m?.away_players);
  if(h.length<11||h.length>25||a.length<11||a.length>25)badMatchIdentity++;
  else {
   const hi=h.map(r=>String(r?.player_id??'')),ai=a.map(r=>String(r?.player_id??'')),hs=new Set(hi);
   if(hi.some(x=>!x)||ai.some(x=>!x)||new Set(hi).size!==hi.length||new Set(ai).size!==ai.length||ai.some(x=>hs.has(x)))badMatchIdentity++;
  }
  if(!matchScoreValid(m))badMatchScore++;
 }
 if(badMatchIdentity)errors.push(`${badMatchIdentity} retained matches have impossible player-side identity`);
 if(badMatchScore)errors.push(`${badMatchScore} retained matches do not reproduce the official score from player goals`);
 if(duplicateMatchFixtures.length)errors.push(`${duplicateMatchFixtures.length} duplicate retained match-detail rows target an already-used fixture`);
 const old=oldPayload&&Array.isArray(oldPayload.players)?oldPayload:null;
 const sameWorld=!!old&&competitionKey(old)!==''&&competitionKey(old)===competitionKey(payload);
 const oldDone=sameWorld?num(old?.meta?.completed_gameweek):0,newDone=num(meta.completed_gameweek);
 const newCompletedPlayed=fixtures.filter(f=>fixturePlayed(f)&&fixtureGw(f)>oldDone&&fixtureGw(f)<=newDone);
 const missingDetail=newCompletedPlayed.filter(f=>!matchFixtureIds.has(fixtureId(f)));
 if(missingDetail.length){
  const catchupImport=!sameWorld||oldDone===0;
  const explicitSeason=importMode==='season';
  const declaredPartial=norm(meta.history_coverage_status)==='partial'
    || num(meta.rich_matches_missing)>0
    || (num(meta.played_results)>matches.length&&matches.length>0);
  if((catchupImport||explicitSeason)&&declaredPartial&&matches.length){
   warnings.push(`${missingDetail.length} historical fixtures still lack player-level detail; ${explicitSeason?'season':'catch-up'} import may publish partial history while recovered matches remain usable`);
  }else{
   errors.push(`${missingDetail.length} newly completed fixtures have no validated player-level match detail`);
  }
 }
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
 return {ok:!errors.length,version:VERSION,errors,warnings,summary:{players:players.length,clubs:clubs.length,matches:matches.length,completed_gameweek:newDone,current_gameweek:num(meta.current_gameweek),latest_result_gameweek:num(meta.latest_gameweek_with_result),history_status:meta.history_coverage_status||null,rich_matches_missing:num(meta.rich_matches_missing),import_mode:importMode||null}};
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
 const c=window.FMCloud;if(!c||c.__worldUpdateGuardV7||typeof c.publishWorld!=='function')return false;c.__worldUpdateGuardV7=true;
 const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload==null)return original(payload,...args);
  const world=c.getWorld?.(),old=world?.payload||null;normaliseProgress(payload);const result=validate(payload,old);payload.meta=payload.meta||{};payload.meta.update_validation=result;
  if(!result.ok){await restoreLocal(old);throw new Error(`FM update blocked before publish: ${result.errors.join(' · ')}`)}
  if(result.warnings.length)console.warn('FM update published with validation warnings:',result.warnings);
  try{return await original(payload,...args)}catch(e){await restoreLocal(old);throw e}
 };
 window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};return true;
}
window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>30)clearInterval(timer)},250);
})();
