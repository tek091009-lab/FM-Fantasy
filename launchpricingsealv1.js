(()=>{
'use strict';
const VERSION='launch-pricing-seal-v1';
const norm=v=>String(v??'').trim().toLowerCase();
function seasonMode(){try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')==='season'}catch(_e){return false}}
function apply(payload){
  if(!seasonMode()||!payload||!Array.isArray(payload.players))return payload;
  // Final launch-pricing seal. These corrections intentionally run AFTER the core V85
  // repricer and immediately before storage/publish so a later V85 pass cannot undo them.
  const chain=[
    window.FMImportModelV86?.transform,
    window.FMImpactRotationPricingV1?.transform,
    window.FMPremiumDefenderPricingV1?.transform,
    window.FMPremiumDMPricingV1?.transform,
    window.FMAttackingOutputPricingV1?.transform
  ];
  for(const fn of chain){if(typeof fn==='function')fn(payload)}
  payload.meta=payload.meta||{};
  payload.meta.launch_pricing_seal=VERSION;
  payload.meta.launch_pricing_seal_policy='season-only final launch corrections run immediately before publish; weekly market history remains untouched';
  try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload.meta;if(typeof fmDebugAdd==='function')fmDebugAdd('info','Final launch-pricing seal applied.',{version:VERSION,gk:payload.meta.gk_current_shirt_price_changes||0,rotation:payload.meta.impact_rotation_price_changes||0,def:payload.meta.premium_defender_price_changes||0,dm:payload.meta.premium_dm_price_changes||0,attack:payload.meta.proven_attacking_output_price_changes||0})}catch(_e){}
  return payload;
}
function install(){
  let original;try{original=globalThis.fmStoredSet}catch(_e){return false}
  if(typeof original!=='function'||original.__fmLaunchPricingSealV1)return false;
  const wrapped=async function(payload,...args){apply(payload);return original(payload,...args)};
  wrapped.__fmLaunchPricingSealV1=true;
  wrapped.__fmLaunchPricingSealOriginal=original;
  globalThis.fmStoredSet=wrapped;
  return true;
}
window.FMLaunchPricingSealV1={version:VERSION,apply,install};
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>120)clearInterval(timer)},100);
window.addEventListener('fmcloudready',()=>setTimeout(install,0));install();
})();
