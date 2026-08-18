(()=>{
'use strict';
const VERSION='import-core-guard-v91-deterministic-v85-first';
function ensure(){
  try{
    const model=window.FMImportModelV85;
    if(!model||typeof model.install!=='function')return false;
    model.install();
    const fn=globalThis.fmApplyPostPayloadPricingCorrections;
    return !!(fn&&fn.__fmV85Wrapped);
  }catch(_e){return false}
}
let tries=0;const timer=setInterval(()=>{tries++;if(ensure()||tries>200)clearInterval(timer)},20);
ensure();
window.FMImportCoreGuardV91={version:VERSION,ensure};
})();
