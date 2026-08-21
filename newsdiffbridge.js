(()=>{
'use strict';
const VERSION='news-diff-bridge-v1-read-only-backup-fallback';
const arr=v=>Array.isArray(v)?v:[];
let client=null,fallback=[],loading=false,lastKey='';
function payload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function world(){try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}}
function canonical(){return arr(payload()?.meta?.transfer_news_guard?.events)}
function getClient(){
 if(client)return client;
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return null;
 client=window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
 return client;
}
async function load(force=false){
 if(loading)return fallback;
 if(canonical().length){fallback=[];return fallback}
 const w=world();if(!w?.id)return fallback;
 const key=`${w.id}|${String(w.updated_at||'')}|${Number(w.payload_version||0)}`;
 if(!force&&key===lastKey&&fallback.length)return fallback;
 const c=getClient();if(!c)return fallback;
 loading=true;
 try{
   const {data,error}=await c.rpc('fmfantasy_last_import_news_diff',{p_world_id:w.id});
   if(error)throw error;
   fallback=arr(data?.events);lastKey=key;
   try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}
   return fallback;
 }catch(e){console.warn('[FM News diff] read-only fallback unavailable',e);return fallback}
 finally{loading=false}
}
function events(){return fallback}
function schedule(){setTimeout(()=>load(false),80);setTimeout(()=>load(false),500)}
window.FMNewsDiffBridge={version:VERSION,load,events};
window.addEventListener('fmcloudready',schedule);
window.addEventListener('fmworldloaded',schedule);
window.addEventListener('fmcanonicalpublished',()=>{fallback=[];lastKey='';schedule()});
window.addEventListener('focus',()=>load(false));
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=String(b.textContent||b.dataset?.nav||b.getAttribute('data-page')||'').toLowerCase();if(s.includes('news'))setTimeout(()=>load(false),30)},true);
let tries=0;const timer=setInterval(()=>{tries++;if(window.FMCloud?.ready?.()){load(false);if(tries>30)clearInterval(timer)}else if(tries>80)clearInterval(timer)},250);
})();
