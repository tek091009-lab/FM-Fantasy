(()=>{
'use strict';
const VERSION='news-transfer-stability-v41-content-signature-authority';
let busy=false,queued=false;
const arr=v=>Array.isArray(v)?v:[];
function payload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function transferEvents(){const canonical=arr(payload()?.meta?.transfer_news_guard?.events);return canonical.length?canonical:arr(window.FMNewsDiffBridge?.events?.())}
function registrationEvents(){return arr(payload()?.meta?.registration_news?.events)}
function transferSig(events=transferEvents()){return JSON.stringify(events.map(e=>[e?.id,e?.old_club,e?.new_club,e?.date]))}
function registrationSig(events=registrationEvents()){return JSON.stringify(events.map(e=>[e?.id,e?.club,e?.kind,e?.date]))}
function hideLegacyTransferRows(card){
 const host=card?.querySelector?.('.fmCanonicalTransferRows');
 for(const row of card?.querySelectorAll?.('[data-news-text],.transfer')||[]){if(!host||!host.contains(row))row.style.display='none'}
}
function transferNeedsRepair(card){
 if(!card)return false;
 const host=card.querySelector('.fmCanonicalTransferRows'),events=transferEvents(),sig=transferSig(events);
 if(!host)return true;
 if(String(host.dataset?.fmSig||'')!==sig)return true;
 if(events.length)return host.querySelectorAll('.fmNewsTransferRow').length!==events.length;
 return !host.querySelector('.fmNewsCanonicalEmpty');
}
function registrationNeedsRepair(card){
 if(!card)return false;
 const rows=card.querySelector('.newsRegRows'),events=registrationEvents(),sig=registrationSig(events);
 if(!rows)return true;
 if(String(rows.dataset?.fmSig||'')!==sig)return true;
 if(events.length)return rows.querySelectorAll('.newsRegRow').length!==events.length;
 return !rows.querySelector('.fmNewsCanonicalEmpty');
}
function stabilise(){
 if(busy)return false;busy=true;
 try{
  const guard=window.FMRegistrationNewsGuard;if(!guard)return false;
  let transfer=document.getElementById('newsTransfers');
  if(transfer&&transferNeedsRepair(transfer)){
   const host=transfer.querySelector('.fmCanonicalTransferRows');if(host?.dataset)delete host.dataset.fmSig;
   guard.renderTransfers?.(document);transfer=document.getElementById('newsTransfers');
  }
  hideLegacyTransferRows(transfer);
  let registrations=document.getElementById('newsRegistrations');
  if(registrations&&registrationNeedsRepair(registrations)){
   const rows=registrations.querySelector('.newsRegRows');if(rows?.dataset)delete rows.dataset.fmSig;
   guard.renderRegistrations?.(document);registrations=document.getElementById('newsRegistrations');
  }
  try{window.FMNewsAestheticV34?.apply?.()}catch(_e){}
  return true;
 }finally{busy=false}
}
function schedule(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;stabilise()})}
function relevantMutation(m){
 const target=m?.target?.nodeType===1?m.target:m?.target?.parentElement;
 if(target?.closest?.('#newsTransfers,#newsRegistrations'))return true;
 for(const n of [...(m?.addedNodes||[]),...(m?.removedNodes||[])]){
  if(n?.nodeType!==1)continue;
  if(n.id==='newsTransfers'||n.id==='newsRegistrations'||n.querySelector?.('#newsTransfers,#newsRegistrations'))return true;
 }
 return false;
}
new MutationObserver(muts=>{if(!busy&&muts.some(relevantMutation))stabilise()}).observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','style','data-fm-sig']});
for(const ev of ['fmcloudready','fmworldloaded','fmcanonicalpublished','fmnewsdiffloaded'])window.addEventListener(ev,schedule);
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const s=String(b.textContent||b.dataset?.nav||b.getAttribute?.('data-page')||'').toLowerCase();if(s.includes('news'))schedule()},true);
setTimeout(stabilise,0);setTimeout(stabilise,120);setTimeout(stabilise,500);setTimeout(stabilise,1200);
window.FMNewsTransferStabilityV40={version:VERSION,stabilise,transferNeedsRepair,registrationNeedsRepair,hideLegacyTransferRows,transferSig,registrationSig};
})();
