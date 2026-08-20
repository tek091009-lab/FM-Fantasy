(()=>{
'use strict';
const VERSION='squad-eligibility-v5-club-matched-senior-evidence';
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const sid=p=>String(p?.eid??p?.pid??p?.player_id??p?.id??'');
function blockedIds(meta){
 const out=new Set(arr(meta?.unresolved_squad_eids).map(String));
 for(const row of arr(meta?.ambiguous_memberships))if(row?.player_eid!==undefined&&row?.player_eid!==null)out.add(String(row.player_eid));
 return out;
}
function currentLeagueClubs(payload){const s=new Set();for(const f of arr(payload?.fixtures))for(const c of [f?.home,f?.away])if(c)s.add(norm(c));return s}
function seniorEvidence(p){
 const club=norm(p?.club||p?.club_full||p?.team||'');let total=0,matching=0;
 for(const h of arr(p?.history)){
   if(!h||h.gameweek===undefined||h.gameweek===null||String(h?.date||'').length<8)continue;
   total++;
   const rowClub=norm(h?.player_club||h?.club||''),home=norm(h?.home||''),away=norm(h?.away||'');
   if((rowClub&&rowClub===club)||home===club||away===club)matching++;
 }
 return {eligible:matching>0,total,matching,mismatched:Math.max(0,total-matching)};
}
function originalCohortEligibility(p){
 const e=p?.registration_evidence||{};
 if(typeof e.cohort_eligible==='boolean')return e.cohort_eligible;
 return p?.competition_eligible===true||String(p?.registration_status||'')==='competition_eligible'||e.eligible===true;
}
function fix(payload){
 if(!payload||!Array.isArray(payload.players))return payload;
 const meta=payload.meta||(payload.meta={}),clubs=currentLeagueClubs(payload),blocked=blockedIds(meta);
 let registered=0,matchdayAdded=0,hiddenReserve=0,blockedCount=0,outside=0,mismatchHidden=0;const addedExamples=[],clubCounts={};
 for(const p of payload.players){
   const id=sid(p),clubRaw=p?.club||p?.club_full||p?.team||'',club=norm(clubRaw);
   const cohortEligible=originalCohortEligibility(p),evidence=seniorEvidence(p),matchday=evidence.eligible;
   p.registration_evidence={...(p.registration_evidence||{}),cohort_eligible:cohortEligible,senior_championship_matchday_evidence:matchday,senior_evidence_matching_rows:evidence.matching,senior_evidence_mismatched_rows:evidence.mismatched};
   if(!club||!clubs.has(club)){outside++;continue}
   if(p?.unresolved===true||blocked.has(id)){
     p.visible=false;p.competition_eligible=false;p.available=false;p.registration_status='quarantined_current_squad_identity';blockedCount++;continue;
   }
   if(cohortEligible){
     p.visible=true;p.competition_eligible=true;p.available=true;p.registration_status='competition_eligible';registered++;
   }else if(matchday){
     p.visible=true;p.competition_eligible=true;p.available=true;p.registration_status='senior_matchday_exception';
     p.registration_evidence={...(p.registration_evidence||{}),eligible:true,override:VERSION,reason:'Not found in registration cohort, but club-matched selected-league senior matchday evidence makes the player Fantasy-eligible. Player-pool visibility is independent of injury/suspension status.'};
     matchdayAdded++;if(addedExamples.length<40)addedExamples.push({id,name:p.name??p.display_name??null,club:clubRaw,pos:p.pos??null,history_rows:arr(p.history).length,matching_rows:evidence.matching});
   }else{
     p.visible=false;p.competition_eligible=false;p.available=false;
     const mismatchOnly=evidence.total>0&&evidence.matching===0;
     p.registration_status=mismatchOnly?'history_club_mismatch_no_valid_senior_evidence':'reserve_or_u21_no_senior_evidence';
     if(mismatchOnly)mismatchHidden++;else hiddenReserve++;
     p.registration_evidence={...(p.registration_evidence||{}),eligible:false,override:VERSION,reason:mismatchOnly?'Decoded match-history rows belong to other clubs, so they cannot promote this player into the current club Fantasy pool.':'Not in registered cohort and no club-matched selected-league senior matchday evidence yet.'};
   }
   if(p.visible!==false){const label=String(clubRaw);clubCounts[label]=(clubCounts[label]||0)+1}
 }
 meta.competition_eligibility_policy=VERSION;
 meta.fantasy_player_pool_policy='registered Championship squad OR club-matched selected-league senior matchday evidence; U21/reserve-only players remain hidden until valid senior evidence; history from another club cannot promote a player; injury/suspension never removes an eligible player from the Fantasy pool';
 meta.squad_eligibility_v5={version:VERSION,registered_players:registered,senior_matchday_additions:matchdayAdded,reserve_or_u21_hidden:hiddenReserve,history_club_mismatch_hidden:mismatchHidden,identity_quarantined:blockedCount,outside_selected_league:outside,visible_club_counts:clubCounts,added_examples:addedExamples,eligible_available_normalised:true};
 if(meta.competition_eligibility_diagnostics&&typeof meta.competition_eligibility_diagnostics==='object'){
   meta.competition_eligibility_diagnostics.previous_policy=meta.competition_eligibility_diagnostics.version||'current-competition-cohort-v86';
   meta.competition_eligibility_diagnostics.cohort_role='registered_senior_base_not_hard_exclusion';
   meta.competition_eligibility_diagnostics.senior_matchday_additions=matchdayAdded;
   meta.competition_eligibility_diagnostics.history_club_mismatch_hidden=mismatchHidden;
   meta.competition_eligibility_diagnostics.eligible_availability_normalised=true;
 }
 return payload;
}
function install(){
 let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
 if(typeof original!=='function'||original.__fmSquadEligibilityV5)return false;
 const wrapped=function(payload,...args){const out=original(payload,...args);fix(payload);try{if(typeof fmDebugAdd==='function')fmDebugAdd('info','Registered-or-club-matched-senior eligibility applied.',{version:VERSION,registered:payload?.meta?.squad_eligibility_v5?.registered_players||0,matchday_additions:payload?.meta?.squad_eligibility_v5?.senior_matchday_additions||0,mismatch_hidden:payload?.meta?.squad_eligibility_v5?.history_club_mismatch_hidden||0})}catch(_e){}return out};
 wrapped.__fmSquadEligibilityV5=true;wrapped.__fmSquadEligibilityOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true;
}
window.FMSquadEligibilityFix={version:VERSION,fix,install,seniorEvidence};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>60)clearInterval(timer)},100);window.addEventListener('fmcloudready',install);
})();