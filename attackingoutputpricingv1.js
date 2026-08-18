(()=>{
'use strict';
const VERSION='proven-attacking-output-pricing-v2-sample-confidence';
const num=v=>Number(v||0)||0;
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,num(v)));
const norm=v=>String(v??'').trim().toLowerCase();
const roundHalf=v=>Math.round(num(v)*2)/2;
function transform(payload){
  if(!payload||!Array.isArray(payload.players))return payload;
  let mode='';try{mode=norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){}
  if(mode!=='season')return payload;
  const changes=[];
  for(const p of payload.players){
    if(!['MID','FWD'].includes(p?.pos)||p?.available===false||p?.visible===false)continue;
    const c=p.price_context||{},attack=clamp(c.attack_profile),q=clamp(c.quality),team=clamp(c.team_strength),share=clamp(c.minutes_share),starts=clamp(c.start_share),obs=Math.max(0,num(c.observed_matches)),mins=Math.max(0,num(p.minutes)),decoded=Math.max(0,num(c.decoded_selected_competition_rows)||((Array.isArray(p.history)&&p.history.length)||0));
    if(obs<2||mins<150||attack<.70||c.current_unavailable)continue;
    const ga=Math.max(0,num(p.goals)+num(p.assists)),ga90=mins?90*ga/mins:0;
    if(share<.55&&starts<.50)continue;
    let floor=0;
    if(p.pos==='MID'){
      if(share>=.65&&ga90>=.75)floor=6.5;
      if(share>=.75&&q>=.48&&ga90>=1.25)floor=7.0;
      if(share>=.80&&q>=.50&&ga90>=1.75)floor=7.5;
    }else{
      // A nailed striker with several real league goals should not remain trapped by a
      // blanket weak-team cap. This is evidence from production, not reputation alone.
      if(share>=.75&&ga>=3&&ga90>=.75)floor=7.0;
      if(share>=.80&&ga90>=1.10&&(q>=.55||team>=.58))floor=7.5;
    }
    let target=Math.max(num(p.price),floor);
    // Recent-arrival pricing needs confidence as well as hot output. Two retained matches
    // can justify a meaningful premium, but not an unlimited one. Lower-quality attackers
    // at mid/weak teams with only a short current sample likewise stay one step below the
    // established premium band until more league evidence arrives.
    let confidenceCap=Infinity;
    if(c.late_arrival===true||String(c.late_arrival).toLowerCase()==='true'){
      if(decoded<=2)confidenceCap=7.5;
      else if(p.pos==='MID'&&decoded<=4&&q<.45&&team<.60)confidenceCap=6.5;
    }
    target=roundHalf(Math.max(4.5,Math.min(target,confidenceCap)));
    const before=num(p.price);if(target===before)continue;
    p.price=target;p.model_price=target;p.launch_price=target;p.dynamic_price=target;
    c.price=target;c.proven_attacking_output_floor=floor||null;c.proven_attacking_output_confidence_cap=Number.isFinite(confidenceCap)?confidenceCap:null;c.pricing_model_version=VERSION;c.proven_attacking_output_evidence={minutes:mins,minute_share:Number(share.toFixed(3)),start_share:Number(starts.toFixed(3)),decoded_rows:decoded,late_arrival:!!c.late_arrival,goals:num(p.goals),assists:num(p.assists),ga_per90:Number(ga90.toFixed(3)),quality:Number(q.toFixed(3)),team_strength:Number(team.toFixed(3)),attack_profile:Number(attack.toFixed(3))};
    c.summary=`${c.role||p.pos} · proven attacking output · minutes ${Math.round(share*100)}% · starts ${Math.round(starts*100)}% · G+A/90 ${ga90.toFixed(2)} · attack ${Math.round(attack*100)}/100 · quality ${Math.round(q*100)}/100${Number.isFinite(confidenceCap)?` · sample-confidence cap ${confidenceCap.toFixed(1)}`:''}`;
    changes.push({pid:String(p.pid??p.id??''),club:p.club,before,after:target,ga90:Number(ga90.toFixed(3)),confidence_cap:Number.isFinite(confidenceCap)?confidenceCap:null});
  }
  payload.meta=payload.meta||{};payload.meta.proven_attacking_output_pricing_model=VERSION;payload.meta.proven_attacking_output_pricing_policy='real selected-league attacking output can lift established mids/forwards above generic caps, while recent-arrival short samples retain confidence ceilings';payload.meta.proven_attacking_output_price_changes=changes.length;payload.meta.proven_attacking_output_price_change_details=changes;return payload;
}
function install(){
  let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
  if(typeof original!=='function'||original.__fmAttackingOutputV1||!original.__fmPremiumDMV1||!original.__fmV85Wrapped||!original.__fmV86Post||!original.__fmV86Wrapped)return false;
  const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','Proven attacking-output pricing finaliser applied.',{changes:payload?.meta?.proven_attacking_output_price_changes||0})}catch(_e){}return out};
  wrapped.__fmAttackingOutputV1=true;wrapped.__fmPremiumDMV1=true;wrapped.__fmPremiumDefV1=true;wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true
}
window.FMAttackingOutputPricingV1={version:VERSION,transform,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>240)clearInterval(timer)},50);install();
})();
