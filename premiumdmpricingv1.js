(()=>{
'use strict';
const VERSION='premium-defensive-midfielder-pricing-v1';
const num=v=>Number(v||0)||0;
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,num(v)));
const norm=v=>String(v??'').trim().toLowerCase();
function defconPer90(p){
  const mins=Math.max(0,num(p?.minutes));if(!mins)return 0;
  const total=(Array.isArray(p?.history)?p.history:[]).reduce((s,h)=>s+Math.max(0,num(h?.defcon_actions)),0);
  return total*90/mins;
}
function transform(payload){
  if(!payload||!Array.isArray(payload.players))return payload;
  let mode='';try{mode=norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){}
  if(mode!=='season')return payload;
  const changes=[];
  for(const p of payload.players){
    if(p?.pos!=='MID'||p?.available===false||p?.visible===false)continue;
    const c=p.price_context||{},role=norm(c.role);
    if(!role.includes('defensive midfielder'))continue;
    const obs=Math.max(0,num(c.observed_matches)),share=clamp(c.minutes_share),starts=clamp(c.start_share),q=clamp(c.quality),team=clamp(c.team_strength),mins=Math.max(0,num(p.minutes));
    const currentStarter=starts>=.60||share>=.68;
    if(obs<3||!currentStarter||q<.55||team<.75||mins<=0||c.current_unavailable)continue;
    const d90=defconPer90(p);
    // Defensive midfielders should not be priced like generic low-upside bench mids when
    // they actually own a shirt for a strong side. Their fantasy value is appearance
    // security + elite-team environment + recovery/DEFCON output, with G/A treated as
    // upside rather than the only route to a meaningful price.
    if(d90<9)continue;
    let target=6.0;
    if(team>=.90&&q>=.65&&d90>=10)target=6.5;
    else if(team>=.82&&q>=.65&&d90>=15)target=6.5;
    const before=num(p.price);if(target<=before)continue;
    p.price=target;p.model_price=target;p.launch_price=target;p.dynamic_price=target;
    c.price=target;c.usage_role='premium_defensive_midfielder';c.usage_role_floor=6;c.usage_role_cap=6.5;c.availability_signal='Nailed strong-team defensive midfielder with DEFCON value';c.pricing_model_version=VERSION;
    c.premium_dm_evidence={minute_share:Number(share.toFixed(3)),start_share:Number(starts.toFixed(3)),quality:Number(q.toFixed(3)),team_strength:Number(team.toFixed(3)),defcon_per90:Number(d90.toFixed(2))};
    c.summary=`${c.role||'Defensive midfielder'} · premium defensive-mid tier · minutes ${Math.round(share*100)}% · starts ${Math.round(starts*100)}% · DEFCON ${d90.toFixed(1)}/90 · team strength ${Math.round(team*100)}/100 · quality ${Math.round(q*100)}/100`;
    changes.push({pid:String(p.pid??p.id??''),club:p.club,before,after:target,defcon_per90:Number(d90.toFixed(2))});
  }
  payload.meta=payload.meta||{};payload.meta.premium_dm_pricing_model=VERSION;payload.meta.premium_dm_pricing_policy='nailed defensive midfielders at strong clubs with proven DEFCON output receive a 6.0-6.5 premium tier despite low attacking profiles';payload.meta.premium_dm_price_changes=changes.length;payload.meta.premium_dm_price_change_details=changes;return payload;
}
function install(){let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}if(typeof original!=='function'||original.__fmPremiumDMV1)return false;const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','Premium defensive-midfielder pricing finaliser applied.',{changes:payload?.meta?.premium_dm_price_changes||0})}catch(_e){}return out};wrapped.__fmPremiumDMV1=true;wrapped.__fmPremiumDefV1=true;wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true}
window.FMPremiumDMPricingV1={version:VERSION,transform,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>140)clearInterval(timer)},50);install();
})();
