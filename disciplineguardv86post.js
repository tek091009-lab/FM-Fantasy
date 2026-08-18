(()=>{
'use strict';
const VERSION='discipline-guard-v87-selected-league-authority';
const STATUS_KEYS=['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail','suspension_evidence','suspension_evidence_structural'];
const STATE=globalThis.__FM_DISCIPLINE_V86||(globalThis.__FM_DISCIPLINE_V86={snapshots:new WeakMap(),captured:0,restored:0,quarantined:0});
const clone=v=>{try{return structuredClone(v)}catch(_){try{return JSON.parse(JSON.stringify(v))}catch(_e){return v}}};
const clear=p=>{for(const k of STATUS_KEYS)try{delete p[k]}catch(_){}};
function reconcile(payload){
 if(!payload||!Array.isArray(payload.players))return payload;
 let leagueAuthoritative=0,rawQuarantined=0;
 for(const p of payload.players){
   const prior=STATE.snapshots.get(p);const ev=p?.suspension_evidence_structural;
   // v85 has already scoped these triggers to the selected competition's player history
   // and checked that no later selected-league fixture has served the ban.  This is the
   // authoritative fantasy suspension source.  Never overwrite it with a raw FM ban that
   // may belong to a cup competition.
   if(String(ev?.source||'')==='selected_competition_history_v85'){
     p.suspended=true;p.suspension_status='Suspended';leagueAuthoritative++;
     if(prior){p.discipline_derived_evidence=p.discipline_derived_evidence||{};p.discipline_derived_evidence.raw_current_ban_candidate={...clone(prior),policy:'diagnostic_only_unscoped_competition_v87'}}
     continue;
   }
   // Raw discipline.dat proves a current ban exists somewhere, but unless the parser can
   // prove its competition it must not create a Championship fantasy suspension.  Preserve
   // it only as diagnostic evidence so cup reds cannot leak into league availability.
   if(prior){p.discipline_derived_evidence=p.discipline_derived_evidence||{};p.discipline_derived_evidence.raw_current_ban_candidate={...clone(prior),policy:'diagnostic_only_unscoped_competition_v87'};clear(p);rawQuarantined++}
 }
 STATE.quarantined+=rawQuarantined;payload.meta=payload.meta||{};
 payload.meta.discipline_current_state_policy='selected-competition history is authoritative for league bans; unscoped discipline.dat bans are diagnostic only v87';
 payload.meta.discipline_v86={version:VERSION,captured_player_records:STATE.captured,selected_league_authoritative:leagueAuthoritative,raw_unscoped_bans_quarantined:rawQuarantined,total_quarantined:STATE.quarantined};
 if(payload.meta.suspension_decoder?.source==='selected_competition_history_v85')payload.meta.suspension_decoder={...payload.meta.suspension_decoder,authoritative_current_state:true,policy:'selected_league_authoritative_v87'};
 try{if(window.FMAvailabilityTruth?.sanitizePayload)window.FMAvailabilityTruth.sanitizePayload(payload)}catch(_){delete payload.meta.suspended_players;payload.meta.suspended_players_current_state_pending_truth=true}
 return payload
}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_){return false}if(typeof original!=='function'||!original.__fmV85Wrapped)return false;if(original.__fmV86Post)return true;const wrapped=function(payload,...args){const out=original(payload,...args);reconcile(payload);return out};wrapped.__fmV86Post=true;wrapped.__fmV86PostOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>150)clearInterval(timer)},20);install();
window.FMDisciplineGuardV86Post={version:VERSION,reconcile,install,state:STATE};
})();
