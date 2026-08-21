(()=>{
'use strict';
const VERSION='news-diff-bridge-v4-public-readonly-rpc';
const arr=v=>Array.isArray(v)?v:[];
const cfg=window.FM_FANTASY_CONFIG||{};
let client=null,fallback=[],loading=false,lastKey='',lastError='',lastLoadedAt='';
function payload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function world(){try{return window.FMCloud?.getWorld?.()||null}catch(_e){return null}}
function canonical(){return arr(payload()?.meta?.transfer_news_guard?.events)}
function getClient(){if(client)return client;if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return null;client=window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});return client}
async function load(force=false){
 if(loading)return fallback;if(canonical().length){fallback=[];lastError='';return fallback}
 const w=world();if(!w?.id)return fallback;const key=`${w.id}|${String(w.updated_at||'')}|${Number(w.payload_version||0)}`;if(!force&&key===lastKey&&fallback.length)return fallback;
 const c=getClient();if(!c){lastError='Public read-only Supabase client unavailable';return fallback}loading=true;
 try{const{data,error}=await c.rpc('fmfantasy_last_import_news_diff_public',{p_world_id:w.id});if(error)throw error;fallback=arr(data?.events);lastKey=key;lastError='';lastLoadedAt=new Date().toISOString();window.dispatchEvent(new CustomEvent('fmnewsdiffloaded',{detail:{count:fallback.length,version:VERSION}}));try{window.FMRegistrationNewsGuard?.refresh?.()}catch(_e){}return fallback}
 catch(e){lastError=String(e?.message||e);console.warn('[FM News diff v4] public read-only fallback unavailable',e);window.dispatchEvent(new CustomEvent('fmnewsdiffloaded',{detail:{count:0,error:lastError,version:VERSION}}));return fallback}
 finally{loading=false}
}
function events(){return fallback}
function schedule(force=false){setTimeout(()=>load(force),80);setTimeout(()=>load(force),500)}
window.FMNewsDiffBridge={version:VERSION,load,events,status:()=>({version:VERSION,count:fallback.length,lastKey,lastError,lastLoadedAt})};
window.addEventListener('fmcloudready',()=>schedule(true));window.addEventListener('fmworldloaded',()=>schedule(true));window.addEventListener('fmcanonicalpublished',()=>{fallback=[];lastKey='';schedule(true)});window.addEventListener('focus',()=>load(true));
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=String(b.textContent||b.dataset?.nav||b.getAttribute('data-page')||'').toLowerCase();if(s.includes('news')){setTimeout(async()=>{await load(true);window.FMRegistrationNewsGuard?.refresh?.()},20);setTimeout(()=>window.FMRegistrationNewsGuard?.refresh?.(),300)}},true);
let tries=0;const timer=setInterval(()=>{tries++;if(window.FMCloud?.ready?.()){load(tries<6);if(tries>40)clearInterval(timer)}else if(tries>100)clearInterval(timer)},250);
})();
