(()=>{
 'use strict';
 const VERSION='availability-truth-v5';
 // Only presentation/current-state aliases are cleared. Decoder evidence is preserved so
 // later universal fallbacks and Export Debug can still inspect rejected/stale schemas.
 const keysInjuryDisplay=['injured','injury_status','injury','injury_name','injury_type','injury_return_date','expected_return_date','injury_expected_back','injury_end_date','return_date','injured_until','injury_days_remaining'];
 const keysSuspDisplay=['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail'];
 const clean=v=>String(v??'').trim();
 const num=v=>Number(v||0)||0;
 const metaFor=payload=>payload?.meta||(()=>{try{return typeof META!=='undefined'?META:{}}catch(_){return{}}})();
 const truthy=v=>v===true||String(v).toLowerCase()==='true';
 const refDate=payload=>clean(metaFor(payload)?.availability_reference_date||metaFor(payload)?.availability_save_date);
 const stale=payload=>truthy(metaFor(payload)?.availability_data_stale);
 const returnDate=p=>clean(p?.injury_return_date??p?.expected_return_date??p?.injury_expected_back??p?.injury_end_date??p?.injury_evidence?.expected_return);
 const suspensionUntil=p=>clean(p?.suspension_evidence_structural?.expiry??p?.banned_until??p?.suspension_until);
 function injuryReason(p,payload){
   if(stale(payload))return 'snapshot_stale';
   const src=clean(p?.injury_evidence?.source),rd=refDate(payload),ret=returnDate(p),days=num(p?.injury_evidence?.days_remaining);
   if(!src.startsWith('injury_manager.dat/current-window'))return src?'untrusted_injury_source':'no_trusted_injury_source';
   if(ret&&rd&&ret<=rd)return 'injury_return_date_expired';
   if(!ret&&days<=0)return 'no_positive_current_injury_duration';
   return null;
 }
 function suspensionReason(p,payload){
   if(stale(payload))return 'snapshot_stale';
   const ev=p?.suspension_evidence_structural||{},src=clean(ev?.source),rd=refDate(payload),until=suspensionUntil(p);
   const remaining=Math.max(num(p?.suspension_remaining),num(p?.suspension_games_remaining),num(p?.ban_games_remaining),num(ev?.games_remaining));
   if(src!=='discipline.dat/active-ban-v1')return src?'untrusted_suspension_source':'no_trusted_suspension_source';
   if(remaining<=0)return 'no_positive_games_remaining';
   // FM schemas do not all store a calendar expiry for match-count bans. A trusted
   // active-ban record with positive games remaining is sufficient current-state evidence.
   // If an expiry exists, it is an additional stale-data guard rather than a required field.
   if(until&&rd&&until<=rd)return 'ban_expired';
   return null;
 }
 const injuryValid=(p,payload)=>injuryReason(p,payload)===null;
 const suspensionValid=(p,payload)=>suspensionReason(p,payload)===null;
 function snapshotPresent(p,keys){const out={};for(const k of keys){if(p&&p[k]!==undefined&&p[k]!==null&&p[k]!=='')out[k]=p[k]}return out}
 function clearKeys(p,keys){for(const k of keys)try{delete p[k]}catch(_){}}
 function preserveRejected(p,kind,reason,raw){
   p.availability_rejected_evidence=p.availability_rejected_evidence||{};
   p.availability_rejected_evidence[kind]={reason,raw,observed_at_runtime:VERSION};
 }
 function sanitizePayload(payload){
   if(!payload||!Array.isArray(payload.players))return payload;
   let injuries=0,suspensions=0,suspensionsWithoutExpiry=0,suppressedInjuries=0,suppressedSuspensions=0,preservedRejectedInjuries=0,preservedRejectedSuspensions=0;
   for(const p of payload.players){
     const ir=injuryReason(p,payload);
     if(ir===null){injuries++;p.injured=true;p.injury_status='Injured'}
     else {
       const raw=snapshotPresent(p,keysInjuryDisplay),hasEvidence=!!(p?.injury_evidence||Object.keys(raw).length);
       if(hasEvidence){suppressedInjuries++;preserveRejected(p,'injury',ir,{...raw,injury_evidence:p.injury_evidence??null});preservedRejectedInjuries++}
       clearKeys(p,keysInjuryDisplay);
     }
     const sr=suspensionReason(p,payload);
     if(sr===null){suspensions++;if(!suspensionUntil(p))suspensionsWithoutExpiry++;p.suspended=true;p.suspension_status='Suspended'}
     else {
       const raw=snapshotPresent(p,keysSuspDisplay),hasEvidence=!!(p?.suspension_evidence||p?.suspension_evidence_structural||Object.keys(raw).length);
       if(hasEvidence){suppressedSuspensions++;preserveRejected(p,'suspension',sr,{...raw,suspension_evidence:p.suspension_evidence??null,suspension_evidence_structural:p.suspension_evidence_structural??null});preservedRejectedSuspensions++}
       clearKeys(p,keysSuspDisplay);
     }
   }
   payload.meta=payload.meta||{};
   payload.meta.injured_players=injuries;payload.meta.suspended_players=suspensions;
   payload.meta.availability_truth_policy='current UI state requires trusted current-save injury evidence or discipline.dat active-ban evidence; trusted positive match-count bans do not require an absolute expiry; rejected/stale decoder evidence is preserved separately for universal reverse-engineering';
   payload.meta.availability_truth_runtime={version:VERSION,reference_date:refDate(payload)||null,data_stale:stale(payload),injuries,suspensions,suspensions_without_expiry:suspensionsWithoutExpiry,suppressed_injuries:suppressedInjuries,suppressed_suspensions:suppressedSuspensions,preserved_rejected_injury_evidence:preservedRejectedInjuries,preserved_rejected_suspension_evidence:preservedRejectedSuspensions};
   return payload;
 }
 function fmt(v){if(!v)return'';try{const d=new Date(String(v).length<=10?String(v)+'T12:00:00':v);return Number.isNaN(d.getTime())?String(v):d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}catch(_){return String(v)}}
 function activeInjuries(payload){sanitizePayload(payload);const out=[];for(const p of payload?.players||[]){if(!injuryValid(p,payload))continue;const ret=returnDate(p);out.push({pid:String(p.pid),name:(typeof playerName==='function'?playerName(p):p.name),club:p.club,pos:p.pos,detail:`Injured${ret?` · expected back ${fmt(ret)}`:''}`})}return out}
 function activeSuspensions(payload){sanitizePayload(payload);const out=[];for(const p of payload?.players||[]){if(!suspensionValid(p,payload))continue;const remaining=Math.max(num(p?.suspension_remaining),num(p?.suspension_games_remaining),num(p?.ban_games_remaining),num(p?.suspension_evidence_structural?.games_remaining)),until=suspensionUntil(p);out.push({pid:String(p.pid),name:(typeof playerName==='function'?playerName(p):p.name),club:p.club,pos:p.pos,detail:`Suspended · ${remaining} match${remaining===1?'':'es'} remaining${until?` · until ${fmt(until)}`:''}`})}return out}
 function install(){
   try{globalThis.fmInferActiveInjuries=activeInjuries;globalThis.fmInferActiveSuspensions=activeSuspensions}catch(_){ }
   const payload=window.FMCloud?.getWorld?.()?.payload||null;if(payload)sanitizePayload(payload);
   try{if(typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS))sanitizePayload({players:PLAYERS,meta:metaFor(payload)})}catch(_){ }
   try{if(typeof renderAll==='function')renderAll();else if(typeof renderNews==='function')renderNews()}catch(_){ }
 }
 window.FMAvailabilityTruth={version:VERSION,sanitizePayload,injuryValid,suspensionValid,injuryReason,suspensionReason,activeInjuries,activeSuspensions};
 window.addEventListener('fmcloudready',()=>setTimeout(install,0));
 window.addEventListener('focus',()=>setTimeout(install,0));
 setTimeout(install,1000);
})();