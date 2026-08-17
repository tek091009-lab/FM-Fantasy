(()=>{
'use strict';
const VERSION='world-update-guard-v1';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const num=v=>Number(v||0)||0;
const clone=v=>{try{return structuredClone(v)}catch(_){return JSON.parse(JSON.stringify(v))}};
const playerId=p=>String(p?.pid??p?.id??'');
const available=p=>p?.available!==false&&String(p?.available??'true')!=='false';
const fixtureGw=f=>num(f?.gameweek??f?.gw??f?.round_gameweek);
const fixturePlayed=f=>String(f?.status||'').toLowerCase()==='played'||(f?.home_score!==null&&f?.home_score!==undefined&&f?.away_score!==null&&f?.away_score!==undefined);
function resolveCompleted(payload){
 const m=payload?.meta||{};let done=num(m.completed_gameweek),latest=Math.max(done,num(m.latest_gameweek_with_result));
 for(let gw=done+1;gw<=latest;gw++){
  const rows=(payload.fixtures||[]).filter(f=>fixtureGw(f)===gw);
  if(!rows.length||rows.every(fixturePlayed)){done=gw;continue}break;
 }
 return done;
}
function normaliseProgress(payload){
 if(!payload?.meta)return;const done=resolveCompleted(payload);if(!done)return;
 payload.meta.completed_gameweek=done;payload.meta.current_gameweek=done+1;payload.meta.next_gameweek=done+1;
 payload.meta.progress_source='fixture_completion_with_blank_gameweeks';
}
function validate(payload,oldPayload){
 const errors=[],warnings=[];const players=Array.isArray(payload?.players)?payload.players:[],clubs=Array.isArray(payload?.clubs)?payload.clubs:[];
 if(players.length<20)errors.push(`player population collapsed to ${players.length}`);
 if(clubs.length<2)errors.push(`club population collapsed to ${clubs.length}`);
 const ids=new Set();let missingIds=0,duplicates=0;
 for(const p of players){const id=playerId(p);if(!id){missingIds++;continue}if(ids.has(id))duplicates++;ids.add(id)}
 if(missingIds)errors.push(`${missingIds} player records have no stable ID`);if(duplicates)errors.push(`${duplicates} duplicate player IDs`);
 const clubMap=new Map();for(const c of clubs){const names=[c?.short_name,c?.name].filter(Boolean);for(const n of names)clubMap.set(norm(n),c)}
 let unknownClub=0,eidMismatch=0;
 for(const p of players){if(!available(p))continue;const c=clubMap.get(norm(p.club));if(!c){unknownClub++;continue}if(p.club_eid!==null&&p.club_eid!==undefined&&String(p.club_eid)!==''&&c.eid!==null&&c.eid!==undefined&&String(p.club_eid)!==String(c.eid))eidMismatch++}
 if(unknownClub)errors.push(`${unknownClub} available players map to no current club`);if(eidMismatch)errors.push(`${eidMismatch} available players have a club-name/club-ID mismatch`);
 const old=oldPayload&&Array.isArray(oldPayload.players)?oldPayload:null;
 const sameFingerprint=!!old&&String(old.meta?.fingerprint||'')!==''&&String(old.meta?.fingerprint||'')===String(payload.meta?.fingerprint||'');
 if(sameFingerprint){
  const oldLatest=num(old.meta?.latest_gameweek_with_result),newLatest=num(payload.meta?.latest_gameweek_with_result);if(newLatest<oldLatest)errors.push(`latest result Gameweek regressed ${oldLatest} → ${newLatest}`);
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
  if(typeof state!=='undefined'&&Array.isArray(state?.squad)&&state.squad.length){const all=new Set(players.map(playerId));const missing=state.squad.filter(id=>!all.has(String(id)));if(missing.length)errors.push(`current manager squad has ${missing.length} player IDs missing from the new world`)}
 }catch(_e){}
 return {ok:!errors.length,version:VERSION,errors,warnings,summary:{players:players.length,clubs:clubs.length,completed_gameweek:num(payload?.meta?.completed_gameweek),current_gameweek:num(payload?.meta?.current_gameweek),latest_result_gameweek:num(payload?.meta?.latest_gameweek_with_result)}};
}
async function restoreLocal(payload){
 if(!payload)return;try{const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('FMFantasyStandalone',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('imports'))r.result.createObjectStore('imports')};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});await new Promise((resolve,reject)=>{const t=db.transaction('imports','readwrite');t.objectStore('imports').put(payload,'championship');t.oncomplete=resolve;t.onerror=()=>reject(t.error)})}catch(e){console.warn('Could not restore previous local FM world after blocked update',e)}
}
function install(){
 const c=window.FMCloud;if(!c||c.__worldUpdateGuardV1||typeof c.publishWorld!=='function')return false;c.__worldUpdateGuardV1=true;
 const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload==null)return original(payload,...args);
  const world=c.getWorld?.(),old=world?.payload||null;normaliseProgress(payload);const result=validate(payload,old);payload.meta=payload.meta||{};payload.meta.update_validation=result;
  if(!result.ok){await restoreLocal(old);try{if(old&&typeof applyImportedPayload==='function')applyImportedPayload(old,'load')}catch(_e){};throw new Error(`FM update blocked before publish: ${result.errors.join(' · ')}`)}
  return original(payload,...args);
 };
 window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};return true;
}
window.FMWorldUpdateGuard={validate,normaliseProgress,version:VERSION};window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>30)clearInterval(timer)},250);
})();
