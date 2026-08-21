(()=>{
'use strict';
const VERSION='session-rpc-bridge-v1-persisted-auth-jwt';
const cfg=window.FM_FANTASY_CONFIG||{};
let lastError='',lastFunction='',lastOkAt='';
function parse(v){try{return JSON.parse(v)}catch(_e){return null}}
function findToken(v,depth=0){
 if(depth>8||v==null)return '';
 if(typeof v==='string'){
   const s=v.trim();if(/^eyJ[A-Za-z0-9_-]+\./.test(s))return s;
   const p=parse(s);return p?findToken(p,depth+1):'';
 }
 if(Array.isArray(v)){for(const x of v){const t=findToken(x,depth+1);if(t)return t}return ''}
 if(typeof v==='object'){
   for(const k of ['access_token','accessToken','token']){const t=v?.[k];if(typeof t==='string'&&/^eyJ[A-Za-z0-9_-]+\./.test(t.trim()))return t.trim()}
   for(const x of Object.values(v)){const t=findToken(x,depth+1);if(t)return t}
 }
 return '';
}
function storageToken(store){
 if(!store)return '';
 const preferred=[];const other=[];
 try{for(let i=0;i<store.length;i++){const k=store.key(i)||'';if(!k)continue;(k.includes('-auth-token')||k.includes('supabase.auth')?preferred:other).push(k)}}catch(_e){return ''}
 for(const k of [...preferred,...other]){try{const t=findToken(store.getItem(k));if(t)return t}catch(_e){}}
 return '';
}
function accessToken(){return storageToken(window.localStorage)||storageToken(window.sessionStorage)||''}
async function call(fn,args={}){
 lastFunction=String(fn||'');lastError='';
 if(!cfg.supabaseUrl||!cfg.supabaseAnonKey)throw new Error('Supabase configuration unavailable');
 const token=accessToken();if(!token){lastError='Authenticated session token not found';throw new Error(lastError)}
 const url=`${String(cfg.supabaseUrl).replace(/\/$/,'')}/rest/v1/rpc/${encodeURIComponent(lastFunction)}`;
 let r;try{r=await fetch(url,{method:'POST',headers:{apikey:cfg.supabaseAnonKey,Authorization:`Bearer ${token}`,'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(args||{})})}catch(e){lastError=String(e?.message||e);throw e}
 const text=await r.text();let data=null;if(text){try{data=JSON.parse(text)}catch(_e){data=text}}
 if(!r.ok){lastError=String(data?.message||data?.error||data||`RPC ${r.status}`);throw new Error(lastError)}
 lastOkAt=new Date().toISOString();return data;
}
window.FMSessionRPC={version:VERSION,call,accessToken:()=>!!accessToken(),status:()=>({version:VERSION,hasToken:!!accessToken(),lastFunction,lastError,lastOkAt})};
})();
