(()=>{
'use strict';
const VERSION='server-manager-score-client-v1-authoritative-rpc';
let busy=false,lastRun={version:VERSION,ok:false,error:'not run'};
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
async function finalise(force=true){
 if(busy||!window.FMCloud?.ready?.()||!window.FMCloud?.isCreator?.())return false;
 const call=window.FMSessionRPC?.call,world=window.FMCloud?.getWorld?.();if(typeof call!=='function'||!world?.id){lastRun={version:VERSION,ok:false,error:'authenticated RPC/world unavailable'};return false}
 busy=true;
 try{
  const data=await call('fmfantasy_creator_score_world_managers',{p_world_id:world.id,p_apply:true});
  lastRun={version:VERSION,...clone(data||{}),at:new Date().toISOString()};
  if(data?.ok){
   const managers=Array.isArray(data?.managers)?data.managers:[];
   window.dispatchEvent(new CustomEvent('fmworldmanagersscored',{detail:{gameweek:Number(data?.target||0),managers:managers.length,scored:managers,source:VERSION}}));
   setTimeout(async()=>{try{await window.FMManagerStateAuthority?.refreshOwnFromServer?.();if(typeof renderAll==='function')renderAll();if(typeof renderLeagues==='function')renderLeagues();window.FMCaptainPointsDisplay?.patch?.()}catch(_e){}},140);
   console.info('[FM server manager scorer]',lastRun);return true;
  }
  return false;
 }catch(e){lastRun={version:VERSION,ok:false,error:String(e?.message||e),at:new Date().toISOString()};console.warn('[FM server manager scorer] failed',e);return false}finally{busy=false}
}
window.FMServerManagerScorer={version:VERSION,finalise,status:()=>clone(lastRun)};
window.fmCreatorFinaliseWorldManagers=()=>finalise(true);
const kick=()=>setTimeout(()=>finalise(true),300);
window.addEventListener('fmcloudready',kick);window.addEventListener('fmcanonicalpublished',kick);window.addEventListener('focus',kick);document.addEventListener('visibilitychange',()=>{if(!document.hidden)kick()});
})();
