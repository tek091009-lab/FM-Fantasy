(()=>{
'use strict';
const VERSION='import-chain-assert-v91';
const norm=v=>String(v??'').trim().toLowerCase();
function seasonMode(){try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')==='season'}catch(_e){return false}}
function validate(payload){
  if(!seasonMode()||!payload)return payload;
  const meta=payload.meta||{},expected=window.FMImportModelV85?.version||'import-model-v85-partial-history-pricing-league-discipline';
  const failures=[];
  if(meta.import_model_finalizer!==expected)failures.push(`core finalizer ${meta.import_model_finalizer||'missing'}`);
  if(meta.pricing_model!=='fpl-shaped-v85-partial-history-role-confidence')failures.push(`pricing model ${meta.pricing_model||'missing'}`);
  if(meta.suspension_decoder?.source!=='selected_competition_history_v85')failures.push(`league suspension decoder ${meta.suspension_decoder?.source||'missing'}`);
  if(failures.length){
    meta.import_chain_integrity={version:VERSION,ok:false,failures};
    try{if(typeof fmDebugAdd==='function')fmDebugAdd('error','Season import blocked because the core V85 importer chain did not run.',{failures})}catch(_e){}
    throw new Error('FM Fantasy season import pipeline integrity failure: '+failures.join('; '));
  }
  meta.import_chain_integrity={version:VERSION,ok:true,core_finalizer:expected,pricing_model:meta.pricing_model,suspension_source:meta.suspension_decoder.source};
  return payload;
}
function install(){
  let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
  if(typeof original!=='function'||original.__fmImportChainAssertV91||!original.__fmAttackingOutputV1)return false;
  const wrapped=function(payload,...args){const out=original(payload,...args);validate(payload);return out};
  wrapped.__fmImportChainAssertV91=true;wrapped.__fmAttackingOutputV1=true;wrapped.__fmPremiumDMV1=true;wrapped.__fmPremiumDefV1=true;wrapped.__fmImpactRotationV1=true;wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true
}
window.FMImportChainAssertV91={version:VERSION,validate,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>300)clearInterval(timer)},40);install();
})();
