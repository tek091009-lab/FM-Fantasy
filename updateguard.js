(()=>{
'use strict';
const VERSION='world-update-guard-v11-club-matched-history-repair';
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const num=v=>Number(v||0)||0;
const arr=v=>Array.isArray(v)?v:[];
const fixtureGw=f=>num(f?.gameweek??f?.gw??f?.round_gameweek);
const fixturePlayed=f=>String(f?.status||'').toLowerCase()==='played'||(f?.home_score!==null&&f?.home_score!==undefined&&f?.away_score!==null&&f?.away_score!==undefined);
const fixtureId=f=>String(f?.fixture_id??f?.id??'');
const competitionKey=p=>norm(p?.meta?.competition_code||p?.meta?.competition||'');
const dateKey=x=>String(x?.date||'').slice(0,10);
const playerId=p=>String(p?.pid??p?.player_id??p?.person_id??p?.eid??p?.id??'');
function teamName(x,side){return norm(x?.[side]??x?.[side+'_team']??x?.[side+'_name']??x?.[side+'_club']??'')}
function stableFixtureKey(x){const h=teamName(x,'home'),a=teamName(x,'away');if(!h||!a)return '';return `${h}|${a}|${dateKey(x)}|${num(x?.home_score)}-${num(x?.away_score)}`}
function historyFixtureKey(x){const h=teamName(x,'home'),a=teamName(x,'away'),d=dateKey(x),gw=fixtureGw(x);if(!h||!a||!d)return '';return `${h}|${a}|${d}|${gw}`}
function matchScoreValid(m){const h=arr(m?.home_players),a=arr(m?.away_players),hg=h.reduce((z,r)=>z+num(r?.goals),0)+a.reduce((z,r)=>z+num(r?.own_goals),0),ag=a.reduce((z,r)=>z+num(r?.goals),0)+h.reduce((z,r)=>z+num(r?.own_goals),0);return hg===num(m?.home_score)&&ag===num(m?.away_score)}
function matchIdentityValid(m){const h=arr(m?.home_players),a=arr(m?.away_players);if(h.length<11||h.length>25||a.length<11||a.length>25)return false;const hi=h.map(r=>String(r?.player_id??'')),ai=a.map(r=>String(r?.player_id??'')),hs=new Set(hi);return !(hi.some(x=>!x)||ai.some(x=>!x)||new Set(hi).size!==hi.length||new Set(ai).size!==ai.length||ai.some(x=>hs.has(x)))}
function contentKey(m){const side=s=>arr(s).map(r=>String(r?.player_id??'')).sort().join(',');return `${fixtureId(m)}|${stableFixtureKey(m)}|${side(m?.home_players)}|${side(m?.away_players)}`}
function rowQuality(r){return num(r?.minutes)*100+(r?.rating!==null&&r?.rating!==undefined?50:0)+num(r?.goals)*20+num(r?.assists)*10+Object.keys(r||{}).length}
function dedupeRows(rows){const by=new Map();for(const r of rows){const id=String(r?.player_id??'');if(!id)continue;const prev=by.get(id);if(!prev||rowQuality(r)>rowQuality(prev))by.set(id,r)}return [...by.values()]}
function clubOf(p){return norm(p?.club||p?.club_full||p?.team||'')}
function buildHistoryBuckets(payload,oldPayload){
 const buckets=new Map(),oldById=new Map(arr(oldPayload?.players).map(p=>[playerId(p),p]).filter(([id])=>id));
 let considered=0,accepted=0,skippedClubMismatch=0,skippedVenueMismatch=0,skippedAmbiguousClub=0;
 for(const p of arr(payload?.players)){
   const pid=playerId(p);if(!pid)continue;
   const allowed=new Set([clubOf(p),clubOf(oldById.get(pid))].filter(Boolean));
   for(const h of arr(p?.history)){
     const key=historyFixtureKey(h);if(!key)continue;considered++;
     const home=teamName(h,'home'),away=teamName(h,'away');if(!home||!away)continue;
     const explicitClub=norm(h?.player_club||h?.club||'');let rowClub='';
     if(explicitClub){
       if(explicitClub!==home&&explicitClub!==away){skippedClubMismatch++;continue}
       if(allowed.size&&!allowed.has(explicitClub)){skippedClubMismatch++;continue}
       rowClub=explicitClub;
     }else{
       const candidates=[home,away].filter(c=>allowed.has(c));
       if(candidates.length!==1){if(candidates.length===0)skippedClubMismatch++;else skippedAmbiguousClub++;continue}
       rowClub=candidates[0];
     }
     const expectedSide=rowClub===home?'H':'A';let side=String(h?.venue||'').trim().toUpperCase();
     if(side==='H'||side==='A'){if(side!==expectedSide){skippedVenueMismatch++;continue}}else side=expectedSide;
     let b=buckets.get(key);if(!b){b={H:[],A:[]};buckets.set(key,b)}
     b[side].push({...h,player_id:pid,name:h?.name??p?.name??p?.display_name??null,club:rowClub});accepted++;
   }
 }
 for(const b of buckets.values()){b.H=dedupeRows(b.H);b.A=dedupeRows(b.A)}
 return {buckets,diagnostics:{considered,accepted,skipped_club_mismatch:skippedClubMismatch,skipped_venue_mismatch:skippedVenueMismatch,skipped_ambiguous_club:skippedAmbiguousClub}};
}
function candidateFromHistory(f,buckets){
 const b=buckets.get(historyFixtureKey(f));if(!b)return null;
 const m={id:f?.id??f?.fixture_id??null,fixture_id:f?.fixture_id??f?.id??null,match_id:f?.match_id??null,home:f?.home??f?.home_team??null,away:f?.away??f?.away_team??null,date:dateKey(f),gameweek:fixtureGw(f),status:'played',home_score:num(f?.home_score),away_score:num(f?.away_score),home_players:b.H,away_players:b.A,source:'player_history_repair_v11',identity_source:'club_matched_decoded_player_history_v11'};
 return matchIdentityValid(m)&&matchScoreValid(m)?m:null;
}
function repartitionExistingByClub(m,f,playerById){
 const rows=dedupeRows([...arr(m?.home_players),...arr(m?.away_players)]),home=norm(f?.home||f?.home_team),away=norm(f?.away||f?.away_team);if(!home||!away||!rows.length)return null;
 const hp=[],ap=[];for(const r of rows){const p=playerById.get(String(r?.player_id??'')),club=norm(p?.club||p?.club_full||r?.club||'');if(club===home)hp.push(r);else if(club===away)ap.push(r);else return null}
 const out={...m,fixture_id:f?.fixture_id??m?.fixture_id??f?.id,home:f?.home??m?.home,away:f?.away??m?.away,date:dateKey(f)||m?.date,gameweek:fixtureGw(f)||m?.gameweek,home_score:num(f?.home_score),away_score:num(f?.away_score),home_players:dedupeRows(hp),away_players:dedupeRows(ap),source:`${m?.source||'fm_rich_stats'}+club_side_repair_v11`,identity_source:'current_club_structural_side_repair_v11'};
 return matchIdentityValid(out)&&matchScoreValid(out)?out:null;
}
function repairWeeklyMatchDetail(payload,oldPayload){
 const meta=payload?.meta||{},mode=activeImportMode(meta),old=oldPayload&&Array.isArray(oldPayload.players)?oldPayload:null,sameWorld=!!old&&competitionKey(old)!==''&&competitionKey(old)===competitionKey(payload);if(mode!=='update'||!sameWorld)return {version:VERSION,attempted:0,repaired_invalid:0,added_missing:0,unrepaired_invalid:0,unrepaired_missing:0};
 const oldDone=num(old?.meta?.completed_gameweek),newDone=num(meta.completed_gameweek),fixtures=arr(payload?.fixtures).filter(f=>fixturePlayed(f)&&fixtureGw(f)>oldDone&&fixtureGw(f)<=newDone),matches=arr(payload?.matches),history=buildHistoryBuckets(payload,old),buckets=history.buckets,playerById=new Map(arr(payload?.players).map(p=>[playerId(p),p]).filter(([id])=>id));
 const byId=new Map(),byStable=new Map();for(let i=0;i<matches.length;i++){const id=fixtureId(matches[i]),sk=stableFixtureKey(matches[i]);if(id&&!byId.has(id))byId.set(id,i);if(sk&&!byStable.has(sk))byStable.set(sk,i)}
 let attempted=0,repairedInvalid=0,addedMissing=0,unrepairedInvalid=0,unrepairedMissing=0;const examples=[];
 for(const f of fixtures){attempted++;const id=fixtureId(f),sk=stableFixtureKey(f);let idx=(id&&byId.has(id)?byId.get(id):(sk&&byStable.has(sk)?byStable.get(sk):-1));const hist=candidateFromHistory(f,buckets);
   if(idx>=0){const current=matches[idx];if(matchIdentityValid(current)&&matchScoreValid(current))continue;const clubFix=repartitionExistingByClub(current,f,playerById),fixed=clubFix||hist;if(fixed){matches[idx]=fixed;repairedInvalid++;if(examples.length<20)examples.push({fixture_id:id,home:f?.home,away:f?.away,date:dateKey(f),action:clubFix?'repartitioned_existing_rich_rows':'rebuilt_from_club_matched_player_history'})}else unrepairedInvalid++;
   }else if(hist){matches.push(hist);idx=matches.length-1;if(id)byId.set(id,idx);if(sk)byStable.set(sk,idx);addedMissing++;if(examples.length<20)examples.push({fixture_id:id,home:f?.home,away:f?.away,date:dateKey(f),action:'added_from_club_matched_player_history'})}else unrepairedMissing++;
 }
 meta.weekly_match_detail_repair={version:VERSION,policy:'repair only from already-decoded player history whose club identity agrees with the fixture side, or current-club rich-row repartitioning; every repaired row must independently pass identity and exact official-score validation',old_completed_gameweek:oldDone,new_completed_gameweek:newDone,attempted,repaired_invalid:repairedInvalid,added_missing:addedMissing,unrepaired_invalid:unrepairedInvalid,unrepaired_missing:unrepairedMissing,history_identity:history.diagnostics,examples};
 meta.rich_matches=matches.length;if(num(meta.played_results)>0)meta.rich_matches_missing=Math.max(0,num(meta.played_results)-matches.length);
 return meta.weekly_match_detail_repair;
}
function resolveCompleted(payload){const meta=payload?.meta||{};let done=num(meta.completed_gameweek),latest=Math.max(done,num(meta.latest_gameweek_with_result));for(let gw=done+1;gw<=latest;gw++){const rows=arr(payload?.fixtures).filter(f=>fixtureGw(f)===gw);if(!rows.length||rows.every(fixturePlayed)){done=gw;continue}break}return done}
function normaliseProgress(payload){if(!payload?.meta)return;const done=resolveCompleted(payload);if(!done)return;payload.meta.completed_gameweek=done;payload.meta.current_gameweek=done+1;payload.meta.next_gameweek=done+1;payload.meta.progress_source='fixture_completion_with_blank_gameweeks'}
function activeImportMode(meta){const explicit=norm(meta?.import_mode||meta?.importMode||'');if(explicit)return explicit;try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){return ''}}
function validate(payload,oldPayload){
 const errors=[],warnings=[],matches=arr(payload?.matches),fixtures=arr(payload?.fixtures),meta=payload?.meta||{};
 const importMode=activeImportMode(meta);
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
 if(missing.length){
   const cleanCatchup=!sameWorld||oldDone===0;
   const declaredPartial=norm(meta.history_coverage_status)==='partial'||num(meta.rich_matches_missing)>0||(num(meta.played_results)>matches.length&&matches.length>0);
   if(cleanCatchup&&importMode==='season'&&declaredPartial&&matches.length){warnings.push(`${missing.length} historical fixtures still lack player-level detail; clean season import may publish partial history while recovered matches remain usable`)}else errors.push(`${missing.length} newly completed fixtures have no validated player-level match detail`);
 }
 if(sameWorld){const oldLatest=num(old?.meta?.latest_gameweek_with_result),newLatest=num(meta.latest_gameweek_with_result);if(newDone<oldDone)errors.push(`completed Gameweek regressed ${oldDone} → ${newDone}`);if(newLatest<oldLatest&&newDone<=oldDone)errors.push(`latest result Gameweek regressed ${oldLatest} → ${newLatest}`)}
 if(trusted)warnings.push(`${trusted} unchanged previously-published match-detail rows trusted without revalidation`);
 const repair=meta.weekly_match_detail_repair||null;if(repair&&(num(repair.repaired_invalid)||num(repair.added_missing)))warnings.push(`weekly match-detail repair recovered ${num(repair.repaired_invalid)} invalid and ${num(repair.added_missing)} missing match rows before validation`);
 return {ok:!errors.length,version:VERSION,errors,warnings,summary:{matches:matches.length,trusted_historical_matches:trusted,new_or_changed_matches:newOrChanged,newly_completed_fixtures:newlyCompleted.length,missing_new_detail:missing.length,completed_gameweek:newDone,current_gameweek:num(meta.current_gameweek),latest_result_gameweek:num(meta.latest_gameweek_with_result),history_status:meta.history_coverage_status||null,rich_matches_missing:num(meta.rich_matches_missing),import_mode:importMode||null,repair}};
}
async function restoreCanonical(){try{if(window.FMAtomicImportRollback?.restoreCanonical)return await window.FMAtomicImportRollback.restoreCanonical();if(typeof window.FMCloud?.loadWorld==='function'){const p=await window.FMCloud.loadWorld(true);if(p&&typeof fmStoredSetLocalOnly==='function')await fmStoredSetLocalOnly(p);if(p&&typeof applyImportedPayload==='function')applyImportedPayload(p,'load');return p}}catch(e){console.warn('Could not restore canonical world after blocked update',e)}return null}
function install(){const cloud=window.FMCloud;if(!cloud||cloud.__worldUpdateGuardV11||typeof cloud.publishWorld!=='function')return false;cloud.__worldUpdateGuardV11=true;const original=cloud.publishWorld.bind(cloud);cloud.publishWorld=async(payload,...args)=>{if(payload==null)return original(payload,...args);const old=JSON.parse(JSON.stringify(cloud.getWorld?.()?.payload||null));repairWeeklyMatchDetail(payload,old);normaliseProgress(payload);const result=validate(payload,old);payload.meta=payload.meta||{};payload.meta.update_validation=result;if(!result.ok){await restoreCanonical();throw new Error(`FM update blocked before publish: ${result.errors.join(' · ')}`)}if(result.warnings.length)console.warn('FM update validation warnings:',result.warnings);try{return await original(payload,...args)}catch(e){await restoreCanonical();throw e}};window.FMWorldUpdateGuard={validate,normaliseProgress,repairWeeklyMatchDetail,version:VERSION};return true}
window.FMWorldUpdateGuard={validate,normaliseProgress,repairWeeklyMatchDetail,version:VERSION};window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();