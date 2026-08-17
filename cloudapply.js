(()=>{
 let done=false,timer=null,tries=0;
 const CLEAR_KEY='fmFantasyCloudDatabaseCleared';
 const wasCleared=()=>{try{return localStorage.getItem(CLEAR_KEY)==='1'||sessionStorage.getItem(CLEAR_KEY)==='1'}catch(_){return false}};
 async function applyCloudWorld(){
   if(done||wasCleared()||!window.FMCloud?.ready?.())return;
   try{
     const payload=await window.FMCloud.loadWorld();
     if(!payload)return;
     if(typeof window.fmStoredSetLocalOnly==='function')await window.fmStoredSetLocalOnly(payload);
     if(typeof window.applyImportedPayload==='function')window.applyImportedPayload(payload,'cloud');
     else if(typeof window.loadServerImportState==='function')await window.loadServerImportState();
     if(window.FMCloud.managerState&&typeof window.state==='object'){
       try{Object.assign(window.state,window.FMCloud.managerState)}catch(_e){}
     }
     if(typeof window.renderAll==='function')window.renderAll();
     done=true;
     if(timer)clearInterval(timer);
     console.info('FM Fantasy shared world applied',{players:payload.players?.length||0,fixtures:payload.fixtures?.length||0});
   }catch(e){console.error('FM Fantasy shared world apply failed',e)}
 }
 window.addEventListener('fmcloudready',()=>{if(!wasCleared())setTimeout(applyCloudWorld,0)});
 timer=setInterval(()=>{tries++;if(!wasCleared())applyCloudWorld();if(done||tries>40||wasCleared())clearInterval(timer)},500);
 if(!wasCleared())setTimeout(applyCloudWorld,50);
})();
