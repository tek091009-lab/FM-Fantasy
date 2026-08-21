(()=>{
'use strict';
const VERSION='session-rpc-bridge-v2-authenticated-supabase-client';
const cfg=window.FM_FANTASY_CONFIG||{};
let client=null,lastError='',lastFunction='',lastOkAt='',hasSession=false;
function getClient(){
 if(client)return client;
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return null;
 client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:false,detectSessionInUrl:false}});
 return client;
}
async function call(fn,args={}){
 lastFunction=String(fn||'');lastError='';
 const c=getClient();if(!c){lastError='Supabase configuration unavailable';throw new Error(lastError)}
 const sess=(await c.auth.getSession()).data.session;hasSession=!!sess;
 if(!sess){lastError='Authenticated session unavailable';throw new Error(lastError)}
 const{data,error}=await c.rpc(lastFunction,args||{});
 if(error){lastError=String(error?.message||error);throw new Error(lastError)}
 lastOkAt=new Date().toISOString();return data;
}
window.FMSessionRPC={version:VERSION,call,accessToken:()=>hasSession,status:()=>({version:VERSION,hasSession,lastFunction,lastError,lastOkAt})};
})();
