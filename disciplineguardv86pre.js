(()=>{
'use strict';
const VERSION='discipline-guard-v86-pre';
const KEYS=['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail','suspension_evidence','suspension_evidence_structural'];
const STATE=globalThis.__FM_DISCIPLINE_V86||(globalThis.__FM_DISCIPLINE_V86={snapshots:new WeakMap(),captured:0,restored:0,quarantined:0});
const clone=v=>{try{return structuredClone(v)}catch(_){try{return JSON.parse(JSON.stringify(v))}catch(_e){return v}}};
function capture(payload){if(!payload||!Array.isArray(payload.players))return;for(const p of payload.players){const raw={};let seen=false;for(const k of KEYS){if(p?.[k]!==undefined){raw[k]=clone(p[k]);seen=true}}if(seen){STATE.snapshots.set(p,raw);STATE.captured++}}payload.meta=payload.meta||{};payload.meta.discipline_v86_pre={version:VERSION,captured_player_records:STATE.captured}}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_){return false}if(typeof original!=='function')return false;if(original.__fmV86Pre)return true;const wrapped=function(payload,...args){capture(payload);return original(payload,...args)};wrapped.__fmV86Pre=true;wrapped.__fmV86PreOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>100)clearInterval(timer)},20);install();
window.FMDisciplineGuardV86Pre={version:VERSION,capture,install,state:STATE};
})();
