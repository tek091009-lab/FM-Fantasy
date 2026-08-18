(()=>{
'use strict';
const VERSION='import-compat-v84-season-plus-36-row';
let runtimeInstalled=false,modeInstalled=false;
function installRuntime(){
  try{
    if(typeof FM_RUNTIME==='undefined'||!FM_RUNTIME||typeof FM_RUNTIME.richStatCount!=='function')return false;
    if(FM_RUNTIME.__retainedMemberThresholdV84){runtimeInstalled=true;return true}
    const original=FM_RUNTIME.richStatCount.bind(FM_RUNTIME);
    FM_RUNTIME.richStatCount=function(buf,limit=40){
      const requested=Number(limit)||40;
      if(requested>=40){
        const actual36=original(buf,36);
        return actual36>=36?40:actual36;
      }
      return original(buf,requested);
    };
    FM_RUNTIME.__retainedMemberThresholdV84=true;
    runtimeInstalled=true;return true;
  }catch(e){console.warn('FM 36-row retained-member compatibility install failed',e);return false}
}
function installMode(){
  try{
    if(typeof sendFMImport!=='function')return false;
    if(sendFMImport.__fmSeasonModeCompatV84){modeInstalled=true;return true}
    const original=sendFMImport;
    const wrapped=async function(file,mode,...args){
      const previous=window.__FM_IMPORT_MODE_ACTIVE;
      const current=String(mode||'').trim().toLowerCase();
      window.__FM_IMPORT_MODE_ACTIVE=current;
      try{return await original.call(this,file,mode,...args)}
      finally{
        if(previous===undefined)delete window.__FM_IMPORT_MODE_ACTIVE;
        else window.__FM_IMPORT_MODE_ACTIVE=previous;
      }
    };
    wrapped.__fmSeasonModeCompatV84=true;
    wrapped.__fmSeasonModeCompatOriginal=original;
    sendFMImport=wrapped;
    modeInstalled=true;return true;
  }catch(e){console.warn('FM import-mode compatibility install failed',e);return false}
}
function expose(){window.FMImporterCompat={version:VERSION,minimum_unlabelled_stat_records:36,runtimeInstalled,modeInstalled,installed:runtimeInstalled&&modeInstalled}}
function install(){installRuntime();installMode();expose();return runtimeInstalled&&modeInstalled}
expose();
if(!install()){
  let tries=0;
  const timer=setInterval(()=>{tries++;if(install()||tries>100)clearInterval(timer)},100);
}
})();
