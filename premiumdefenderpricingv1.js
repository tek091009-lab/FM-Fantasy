(()=>{
'use strict';
const VERSION='premium-attacking-defender-pricing-v1';
const num=v=>Number(v||0)||0;
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,num(v)));
const roundHalf=v=>Math.round(num(v)*2)/2;
const norm=v=>String(v??'').trim().toLowerCase();
function transform(payload){
  if(!payload||!Array.isArray(payload.players))return payload;
  let mode='';try{mode=norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){}
  if(mode!=='season')return payload;
  const changes=[];
  for(const p of payload.players){
    if(p?.pos!=='DEF'||p?.available===false||p?.visible===false)continue;
    const c=p.price_context||{},role=norm(c.role),obs=Math.max(0,num(c.observed_matches)),share=clamp(c.minutes_share),starts=clamp(c.start_share),q=clamp(c.quality),team=clamp(c.team_strength),attack=clamp(c.attack_profile),nailed=clamp(c.nailedness),mins=Math.max(0,num(p.minutes));
    // Only promote proven, current selected-league attacking defenders. This prevents
    // unused wing-backs at strong clubs inheriting a premium price merely from reputation.
    const attackingRole=role.includes('wing-back')||role.includes('attacking full-back');
    const currentStarter=starts>=.60||share>=.70;
    if(!attackingRole||obs<3||!currentStarter||share<.55||q<.55||team<.75||attack<.34||mins<=0||c.current_unavailable)continue;
    const ga90=Math.max(0,num(c.ga_per90)||(mins?90*(num(p.goals)+num(p.assists))/mins:0));
    // Premium DEF value comes from clean-sheet environment + current shirt ownership +
    // genuine advanced role. Returns add upside, but a wing-back does not need to have
    // already banked an assist in a four-match sample to be priced above a centre-back.
    let target=4.5+.60*team+.40*q+.50*attack+.40*nailed+.50*clamp(ga90/.5);
    if(team>=.90&&share>=.70&&starts>=.75)target+=.10;
    target=roundHalf(Math.max(5.5,Math.min(7.0,target)));
    const before=num(p.price);if(target<=before)continue;
    p.price=target;p.model_price=target;p.launch_price=target;p.dynamic_price=target;
    c.price=target;c.usage_role='premium_attacking_defender';c.usage_role_floor=5.5;c.usage_role_cap=7;c.availability_signal='Current starting attacking defender';c.pricing_model_version=VERSION;
    c.premium_defender_evidence={role:c.role||null,minute_share:Number(share.toFixed(3)),start_share:Number(starts.toFixed(3)),quality:Number(q.toFixed(3)),attack_profile:Number(attack.toFixed(3)),team_strength:Number(team.toFixed(3)),nailedness:Number(nailed.toFixed(3)),ga_per90:Number(ga90.toFixed(3))};
    c.summary=`${c.role||'Attacking defender'} · premium attacking DEF · minutes ${Math.round(share*100)}% · starts ${Math.round(starts*100)}% · attack ${Math.round(attack*100)}/100 · team strength ${Math.round(team*100)}/100 · quality ${Math.round(q*100)}/100`;
    changes.push({pid:String(p.pid??p.id??''),club:p.club,before,after:target});
  }
  payload.meta=payload.meta||{};payload.meta.premium_defender_pricing_model=VERSION;payload.meta.premium_defender_pricing_policy='proven selected-league starting wing-backs/attacking full-backs at strong clubs receive a premium over generic defenders; unused backups do not';payload.meta.premium_defender_price_changes=changes.length;payload.meta.premium_defender_price_change_details=changes;return payload;
}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}if(typeof original!=='function'||original.__fmPremiumDefenderV1)return false;const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','Premium attacking defender pricing finaliser applied.',{changes:payload?.meta?.premium_defender_price_changes||0})}catch(_e){}return out};wrapped.__fmPremiumDefenderV1=true;wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
window.FMPremiumDefenderPricingV1={version:VERSION,transform,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>140)clearInterval(timer)},50);install();
})();
