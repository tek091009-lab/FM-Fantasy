(()=>{
'use strict';
const VERSION='discipline-guard-v86-post';
const STATUS_KEYS=['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail','suspension_evidence','suspension_evidence_structural'];
const STATE=globalThis.__FM_DISCIPLINE_V86||(globalThis.__FM_DISCIPLINE_V86={snapshots:new WeakMap(),captured:0,restored:0,quarantined:0});
const clone=v=>{try{return structuredClone(v)}catch(_){try{return JSON.parse(JSON.stringify(v))}catch(_e){return v}}};
const clear=p=>{for(const k of STATUS_KEYS)try{delete p[k]}catch(_){}};
function reconcile(payload){if(!payload||!Array.isArray(payload.players))return payload;let restored=0,quarantined=0;for(const p of payload.players){const prior=STATE.snapshots.get(p);if(prior){clear(p);for(const [k,v] of Object.entries(prior))p[k]=clone(v);restored++;continue}const ev=p?.suspension_evidence_structural;if(String(ev?.source||'')==='selected_competition_history_v85'){p.discipline_derived_evidence=p.discipline_derived_evidence||{};p.discipline_derived_evidence.history_threshold_candidate={...clone(ev),policy:'diagnostic_only_not_current_state_v86'};clear(p);quarantined++}}
 STATE.restored+=restored;STATE.quarantined+=quarantined;payload.meta=payload.meta||{};payload.meta.discipline_current_state_policy='preserve explicit current-state decoder evidence; card-history thresholds diagnostic only v86';payload.meta.discipline_v86={version:VERSION,captured_player_records:STATE.captured,restored_current_evidence:restored,history_derived_candidates_quarantined:quarantined,total_restored:STATE.restored,total_quarantined:STATE.quarantined};if(payload.meta.suspension_decoder?.source==='selected_competition_history_v85')payload.meta.suspension_decoder={...payload.meta.suspension_decoder,authoritative_current_state:false,policy:'diagnostic_only_not_current_state_v86'};return payload}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_){return false}if(typeof original!=='function'||!original.__fmV85Wrapped)return false;if(original.__fmV86Post)return true;const wrapped=function(payload,...args){const out=original(payload,...args);reconcile(payload);return out};wrapped.__fmV86Post=true;wrapped.__fmV86PostOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>150)clearInterval(timer)},20);install();
window.FMDisciplineGuardV86Post={version:VERSION,reconcile,install,state:STATE};
})();
