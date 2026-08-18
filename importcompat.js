(()=>{
'use strict';
const VERSION='retained-member-threshold-v81';
function install(){
  try{
    if(typeof FM_RUNTIME==='undefined'||!FM_RUNTIME||FM_RUNTIME.__retainedMemberThresholdV81||typeof FM_RUNTIME.richStatCount!=='function')return false;
    FM_RUNTIME.__retainedMemberThresholdV81=true;
    const original=FM_RUNTIME.richStatCount.bind(FM_RUNTIME);
    FM_RUNTIME.richStatCount=function(buf,limit=40){
      const requested=Number(limit)||40;
      if(requested>=40){
        const actual36=original(buf,36);
        return actual36>=36?40:actual36;
      }
      return original(buf,requested);
    };
    window.FMImporterCompat={version:VERSION,minimum_unlabelled_stat_records:36,installed:true};
    return true;
  }catch(e){console.warn('FM importer compatibility install failed',e);return false}
}
window.FMImporterCompat={version:VERSION,minimum_unlabelled_stat_records:36,installed:false};
if(!install()){
  let tries=0;
  const timer=setInterval(()=>{tries++;if(install()||tries>50)clearInterval(timer)},100);
}
})();
