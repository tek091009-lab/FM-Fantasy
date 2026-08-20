(()=>{
'use strict';
const VERSION='squad-eligibility-v1-current-squad-authority';
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const sid=p=>String(p?.eid??p?.pid??p?.player_id??p?.id??'');
function blockedIds(meta){
 const out=new Set(arr(meta?.unresolved_squad_eids).map(String));
 for(const row of arr(meta?.ambiguous_memberships)){
   if(row?.player_eid!==undefined&&row?.player_eid!==null)out.add(String(row.player_eid));
 }
 return out;
}
function currentLeagueClubs(payload){
 const s=new Set();for(const f of arr(payload?.fixtures)){for(const c of [f?.home,f?.away])if(c)s.add(norm(c))}return s;
}
function fix(payload){
 if(!payload||!Array.isArray(payload.players))return payload;
 const meta=payload.meta||(payload.meta={}),clubs=currentLeagueClubs(payload),blocked=blockedIds(meta);
 let rescued=0,already=0,blockedCount=0,outside=0;const examples=[];
 for(const p of payload.players){
   const id=sid(p),club=norm(p?.club||p?.club_full||p?.team||'');
   if(!club||!clubs.has(club)){outside++;continue}
   if(p?.unresolved===true||blocked.has(id)){blockedCount++;p.visible=false;p.competition_eligible=false;p.registration_status='quarantined_current_squad_identity';continue}
   if(p.visible!==false&&p.competition_eligible!==false){already++;continue}
   p.visible=true;p.competition_eligible=true;p.registration_status='current_squad_authoritative';
   p.registration_evidence={...(p.registration_evidence||{}),eligible:true,override:VERSION,reason:'Resolved current FM squad membership is authoritative. Competition cohort membership is supporting evidence only.'};
   rescued++;if(examples.length<30)examples.push({id,name:p.name??p.display_name??null,club:p.club??p.club_full??null,pos:p.pos??null,history_rows:arr(p.history).length});
 }
 meta.competition_eligibility_policy=VERSION;
 meta.current_squad_authority={version:VERSION,rescued_players:rescued,already_eligible:already,identity_quarantined:blockedCount,outside_selected_league:outside,competition_cohort_role:'supporting_only_not_hard_exclusion',examples};
 if(meta.competition_eligibility_diagnostics&&typeof meta.competition_eligibility_diagnostics==='object'){
   meta.competition_eligibility_diagnostics.previous_policy=meta.competition_eligibility_diagnostics.version||'current-competition-cohort-v86';
   meta.competition_eligibility_diagnostics.hard_exclusion_disabled=true;
   meta.competition_eligibility_diagnostics.rescued_by_current_squad_authority=rescued;
 }
 return payload;
}
function install(){
 let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
 if(typeof original!=='function'||original.__fmSquadEligibilityV1)return false;
 const wrapped=function(payload,...args){const out=original(payload,...args);fix(payload);try{if(typeof fmDebugAdd==='function')fmDebugAdd('info','Current squad eligibility authority applied.',{version:VERSION,rescued:payload?.meta?.current_squad_authority?.rescued_players||0,quarantined:payload?.meta?.current_squad_authority?.identity_quarantined||0})}catch(_e){}return out};
 wrapped.__fmSquadEligibilityV1=true;wrapped.__fmSquadEligibilityOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true;
}
window.FMSquadEligibilityFix={version:VERSION,fix,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>60)clearInterval(timer)},100);window.addEventListener('fmcloudready',install);
})();