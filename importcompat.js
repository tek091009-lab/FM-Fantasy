(()=>{
'use strict';
const VERSION='import-mode-v83-season-publish';
let installed=false;
function expose(){window.FMImporterCompat={version:VERSION,modeInstalled:installed,installed}}
function install(){
  try{
    if(typeof sendFMImport!=='function')return false;
    if(sendFMImport.__fmSeasonModeCompatV83){installed=true;expose();return true}
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
    wrapped.__fmSeasonModeCompatV83=true;
    wrapped.__fmSeasonModeCompatOriginal=original;
    sendFMImport=wrapped;
    installed=true;expose();return true;
  }catch(e){console.warn('FM import-mode compatibility install failed',e);return false}
}
expose();
if(!install()){
  let tries=0;
  const timer=setInterval(()=>{tries++;if(install()||tries>100)clearInterval(timer)},100);
}
})();
