(()=>{
'use strict';
const VERSION='impact-rotation-pricing-v1';
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
    if(p?.pos!=='MID'||p?.available===false||p?.visible===false)continue;
    const c=p.price_context||{},obs=Math.max(0,num(c.observed_matches)),share=clamp(c.minutes_share),starts=clamp(c.start_share),q=clamp(c.quality),team=clamp(c.team_strength),attack=clamp(c.attack_profile),mins=Math.max(0,num(p.minutes));
    if(obs<3||share<.20||share>=.35||starts>=.30||q<.60||team<.75||attack<.70||mins<=0||c.current_unavailable)continue;
    const hist=Array.isArray(p.history)?p.history:[],apps=hist.filter(h=>num(h?.minutes)>0).length,appearanceRate=obs?clamp(apps/obs):0;
    const ga90=num(c.ga_per90)||(mins?90*(num(p.goals)+num(p.assists))/mins:0);
    if(appearanceRate<.75||ga90<.75)continue;
    // A regularly-used attacking substitute for a strong team is not equivalent to a
    // low-usage bench filler.  Reconstruct the attacking-MID value before the old blanket
    // <35% minutes cap, then constrain it to a rotation band whose ceiling rises with
    // team strength, quality and attacking upside. This preserves the starter discount
    // without creating £5m bargains one injury away from a premium role.
    const nailed=clamp(c.nailedness),uncapped=4.10+.72*q+1.18*nailed+1.70*attack+.82*team+4.15*(q**4)*(.30+.70*nailed)*(.40+.60*attack);
    const rotationCeiling=5.0+.65*team+.35*q+.35*attack;
    const target=roundHalf(Math.max(5.5,Math.min(uncapped,rotationCeiling,6.5)));
    const before=num(p.price);if(target<=before)continue;
    p.price=target;p.model_price=target;p.launch_price=target;p.dynamic_price=target;
    c.price=target;c.usage_role='high_impact_rotation';c.usage_role_floor=5.5;c.usage_role_cap=Number(rotationCeiling.toFixed(2));c.availability_signal='High-impact attacking rotation';c.pricing_model_version=VERSION;c.high_impact_rotation_evidence={appearance_rate:Number(appearanceRate.toFixed(3)),minute_share:Number(share.toFixed(3)),start_share:Number(starts.toFixed(3)),ga_per90:Number(ga90.toFixed(3)),quality:Number(q.toFixed(3)),attack_profile:Number(attack.toFixed(3)),team_strength:Number(team.toFixed(3))};
    c.summary=`${c.role||'Attacking midfielder / winger'} · high-impact rotation · minutes ${Math.round(share*100)}% · appearances ${Math.round(appearanceRate*100)}% · attack ${Math.round(attack*100)}/100 · team strength ${Math.round(team*100)}/100 · quality ${Math.round(q*100)}/100`;
    changes.push({pid:String(p.pid??p.id??''),club:p.club,before,after:target});
  }
  payload.meta=payload.meta||{};payload.meta.impact_rotation_pricing_model=VERSION;payload.meta.impact_rotation_pricing_policy='regular high-impact attacking substitutes at strong clubs are priced above generic bench filler while retaining a starter discount';payload.meta.impact_rotation_price_changes=changes.length;payload.meta.impact_rotation_price_change_details=changes;return payload;
}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}if(typeof original!=='function'||original.__fmImpactRotationV1)return false;const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','High-impact rotation pricing finaliser applied.',{changes:payload?.meta?.impact_rotation_price_changes||0})}catch(_e){}return out};wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
window.FMImpactRotationPricingV1={version:VERSION,transform,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>120)clearInterval(timer)},50);install();
})();
