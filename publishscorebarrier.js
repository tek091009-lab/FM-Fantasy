(()=>{
'use strict';
const VERSION='publish-score-barrier-v1-score-before-import-completes';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let installed=false,last={version:VERSION,ok:false,error:'not run'};
async function score(worldId){
 const call=window.FMSessionRPC?.call;if(typeof call!=='function')throw new Error('Authenticated RPC unavailable');
 let err=null;
 for(const wait of [0,180,500,1000]){
  if(wait)await sleep(wait);
  try{
   const data=await call('fmfantasy_creator_score_world_managers',{p_world_id:worldId,p_apply:true});
   if(data?.ok){
    last={version:VERSION,ok:true,data,at:new Date().toISOString()};
    try{window.dispatchEvent(new CustomEvent('fmworldmanagersscored',{detail:{gameweek:Number(data?.target||0),managers:Array.isArray(data?.managers)?data.managers.length:0,scored:data?.managers||[],source:VERSION}}))}catch(_e){}
    try{await window.FMManagerStateAuthority?.refreshOwnFromServer?.()}catch(_e){}
    return data;
   }
   err=new Error(String(data?.error||'manager scoring did not return ok'));
  }catch(e){err=e}
 }
 throw err||new Error('Manager scoring failed');
}
async function rollback(worldId){
 try{return await window.FMSessionRPC?.call?.('fmfantasy_undo_last_import',{p_world_id:worldId})}catch(e){console.error('[FM publish score barrier] rollback failed',e);return null}
}
function install(){
 const cloud=window.FMCloud;if(!cloud||typeof cloud.publishWorld!=='function'||cloud.publishWorld.__fmScoreBarrier)return false;
 const original=cloud.publishWorld.bind(cloud);
 const wrapped=async function(payload){
  const canonical=await original(payload);
  if(payload==null||!cloud.isCreator?.())return canonical;
  const world=cloud.getWorld?.();if(!world?.id)return canonical;
  try{await score(world.id);return canonical}
  catch(e){
   last={version:VERSION,ok:false,error:String(e?.message||e),at:new Date().toISOString()};
   const undone=await rollback(world.id);
   if(undone?.ok===false)console.error('[FM publish score barrier] undo returned failure',undone);
   throw new Error(`Weekly import manager scoring failed${undone?' and the world was rolled back':''}: ${String(e?.message||e)}`);
  }
 };
 wrapped.__fmScoreBarrier=true;wrapped.__fmOriginal=original;cloud.publishWorld=wrapped;installed=true;return true;
}
window.FMPublishScoreBarrier={version:VERSION,install,score,status:()=>Object.assign({installed},last)};
let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>60)clearInterval(timer)},100);
window.addEventListener('fmcloudready',()=>setTimeout(install,0));
})();
