(()=>{
 'use strict';
 const VERSION='availability-truth-v1';
 const keysInjury=['injured','injury_status','injury','injury_name','injury_return_date','expected_return_date','injury_expected_back','injury_end_date','return_date','injury_evidence'];
 const keysSusp=['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail','suspension_evidence'];
 const clean=v=>String(v??'').trim();
 const num=v=>Number(v||0)||0;
 const metaFor=payload=>payload?.meta||(()=>{try{return typeof META!=='undefined'?META:{}}catch(_){return{}}})();
 const saveDate=payload=>clean(metaFor(payload)?.availability_save_date);
 const returnDate=p=>clean(p?.injury_return_date??p?.expected_return_date??p?.injury_expected_back??p?.injury_end_date??p?.injury_evidence?.expected_return);
 const suspensionUntil=p=>clean(p?.banned_until??p?.suspension_until??p?.suspension_evidence?.until);
 function injuryValid(p,payload){
   const src=clean(p?.injury_evidence?.source),sd=saveDate(payload),ret=returnDate(p);
   if(!src.startsWith('injury_manager.dat/current-window'))return false;
   if(sd&&ret&&ret<sd)return false;
   if(num(p?.injury_evidence?.days_remaining)<0)return false;
   return true;
 }
 function suspensionValid(p,payload){
   const sd=saveDate(payload),until=suspensionUntil(p),src=clean(p?.suspension_evidence?.source).toLowerCase();
   const remaining=Math.max(num(p?.suspension_remaining),num(p?.suspension_games_remaining),num(p?.ban_games_remaining));
   if(remaining>0)return true;
   if(p?.suspended===true&&until&&(!sd||until>=sd))return true;
   if(src.includes('current')&&(!until||!sd||until>=sd))return true;
   return false;
 }
 function clearKeys(p,keys){for(const k of keys)try{delete p[k]}catch(_){}}
 function sanitizePayload(payload){
   if(!payload||!Array.isArray(payload.players))return payload;
   let injuries=0,suspensions=0,suppressedInjuries=0,suppressedSuspensions=0;
   for(const p of payload.players){
     if(injuryValid(p,payload)){injuries++;p.injured=true;p.injury_status='Injured'}
     else {if(p?.injured||p?.injury_status||p?.injury||p?.injury_name||p?.injury_evidence)suppressedInjuries++;clearKeys(p,keysInjury)}
     if(suspensionValid(p,payload)){suspensions++;p.suspended=true;p.suspension_status='Suspended'}
     else {if(p?.suspended||p?.suspension_status||p?.suspension_remaining||p?.suspension_evidence)suppressedSuspensions++;clearKeys(p,keysSusp)}
   }
   payload.meta=payload.meta||{};
   payload.meta.injured_players=injuries;payload.meta.suspended_players=suspensions;
   payload.meta.availability_truth_policy='current-save direct evidence only; expired and heuristic-only statuses suppressed';
   payload.meta.availability_truth_runtime={version:VERSION,injuries,suspensions,suppressed_injuries:suppressedInjuries,suppressed_suspensions:suppressedSuspensions};
   return payload;
 }
 function fmt(v){if(!v)return'';try{const d=new Date(String(v).length<=10?String(v)+'T12:00:00':v);return Number.isNaN(d.getTime())?String(v):d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}catch(_){return String(v)}}
 function activeInjuries(payload){sanitizePayload(payload);const out=[];for(const p of payload?.players||[]){if(!injuryValid(p,payload))continue;const ret=returnDate(p);out.push({pid:String(p.pid),name:(typeof playerName==='function'?playerName(p):p.name),club:p.club,pos:p.pos,detail:`Injured${ret?` · expected back ${fmt(ret)}`:''}`})}return out}
 function activeSuspensions(payload){sanitizePayload(payload);const out=[];for(const p of payload?.players||[]){if(!suspensionValid(p,payload))continue;const remaining=Math.max(num(p?.suspension_remaining),num(p?.suspension_games_remaining),num(p?.ban_games_remaining)),until=suspensionUntil(p);out.push({pid:String(p.pid),name:(typeof playerName==='function'?playerName(p):p.name),club:p.club,pos:p.pos,detail:`Suspended${remaining?` · ${remaining} match${remaining===1?'':'es'} remaining`:until?` · until ${fmt(until)}`:''}`})}return out}
 function install(){
   try{globalThis.fmInferActiveInjuries=activeInjuries;globalThis.fmInferActiveSuspensions=activeSuspensions}catch(_){ }
   let payload=window.FMCloud?.getWorld?.()?.payload||null;
   if(payload)sanitizePayload(payload);
   try{if(typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)){sanitizePayload({players:PLAYERS,meta:metaFor(payload)});}}
   catch(_){ }
   try{if(typeof renderAll==='function')renderAll();else if(typeof renderNews==='function')renderNews()}catch(_){ }
 }
 window.FMAvailabilityTruth={version:VERSION,sanitizePayload,injuryValid,suspensionValid,activeInjuries,activeSuspensions};
 window.addEventListener('fmcloudready',()=>setTimeout(install,0));
 window.addEventListener('focus',()=>setTimeout(install,0));
 setTimeout(install,1000);
})();