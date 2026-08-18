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
    const c=p.price_context||{},role=norm(c.role),attackingRole=role.includes('attacking full-back')||role.includes('wing-back')||role.includes('wide def/mid hybrid');
    if(!attackingRole)continue;
    const obs=Math.max(0,num(c.observed_matches)),team=clamp(c.team_strength),q=clamp(c.quality),attack=clamp(c.attack_profile),share=clamp(c.minutes_share),starts=clamp(c.start_share),nailed=clamp(c.nailedness),mins=Math.max(0,num(p.minutes));
    if(obs<3||team<.88||q<.60||share<.68||starts<.75||mins<=0||c.current_unavailable)continue;
    // Premium defender value is role + security + team clean-sheet expectation first.
    // Recent assists/goals are an additional ceiling lever, not a prerequisite: otherwise
    // a nailed LWB at a title favourite is priced like a centre-back until his first return.
    const ga90=num(c.ga_per90)||(mins?90*(num(p.goals)+num(p.assists))/mins:0);
    let target=6.0;
    if((attack>=.55||ga90>=.25)&&(q>=.68||nailed>=.85))target=6.5;
    if(attack>=.70&&ga90>=.35&&q>=.78&&nailed>=.90)target=7.0;
    const before=num(p.price);target=roundHalf(Math.max(before,target));if(target<=before)continue;
    p.price=target;p.model_price=target;p.launch_price=target;p.dynamic_price=target;
    c.price=target;c.premium_defender_tier=true;c.pricing_model_version=VERSION;c.premium_defender_evidence={role:c.role||null,team_strength:Number(team.toFixed(3)),quality:Number(q.toFixed(3)),attack_profile:Number(attack.toFixed(3)),minute_share:Number(share.toFixed(3)),start_share:Number(starts.toFixed(3)),nailedness:Number(nailed.toFixed(3)),ga_per90:Number(ga90.toFixed(3))};
    c.summary=`${c.role||'Attacking defender'} · premium attacking-defender tier · minutes ${Math.round(share*100)}% · starts ${Math.round(starts*100)}% · team strength ${Math.round(team*100)}/100 · attack ${Math.round(attack*100)}/100 · quality ${Math.round(q*100)}/100`;
    changes.push({pid:String(p.pid??p.id??''),club:p.club,before,after:target});
  }
  payload.meta=payload.meta||{};payload.meta.premium_defender_pricing_model=VERSION;payload.meta.premium_defender_pricing_policy='nailed attacking full-backs/wing-backs at elite teams receive a premium before actual G/A; returns raise the ceiling';payload.meta.premium_defender_price_changes=changes.length;payload.meta.premium_defender_price_change_details=changes;return payload;
}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}if(typeof original!=='function'||original.__fmPremiumDefV1)return false;const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','Premium attacking-defender pricing finaliser applied.',{changes:payload?.meta?.premium_defender_price_changes||0})}catch(_e){}return out};wrapped.__fmPremiumDefV1=true;wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
window.FMPremiumDefenderPricingV1={version:VERSION,transform,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>120)clearInterval(timer)},50);install();
})();
