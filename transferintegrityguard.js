(()=>{
'use strict';
const VERSION='transfer-integrity-guard-v2-locked-squad-authority';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
function stateRef(){try{return typeof state!=='undefined'?state:null}catch(_e){return null}}
function cloudRef(){return window.FMCloud?.managerState||null}
function validSquad(v){return arr(v).length===15}
function validStarters(v){return arr(v).length===11}
function validBench(v){return arr(v).length===4}
function source(){
 const st=stateRef(),cloud=cloudRef();
 if(validSquad(st?.lockedSquad))return st;
 if(validSquad(cloud?.lockedSquad))return cloud;
 if(st?.teamConfirmed&&validSquad(st?.squad))return st;
 if(cloud?.teamConfirmed&&validSquad(cloud?.squad))return cloud;
 return null;
}
function repairBaseline(){
 const st=stateRef();if(!st||!st.teamConfirmed)return false;
 const cloud=cloudRef();let changed=false;
 if(!validSquad(st.lockedSquad)){
  if(validSquad(cloud?.lockedSquad)){
   st.lockedSquad=clone(cloud.lockedSquad);
   st.lockedBank=Number(cloud.lockedBank??cloud.bank??st.bank??0);
   if(cloud.lockedCaptain!==undefined)st.lockedCaptain=cloud.lockedCaptain;
   if(cloud.lockedVice!==undefined)st.lockedVice=cloud.lockedVice;
   changed=true;
  }else if(validSquad(st.squad)){
   // A confirmed team with no baseline is the exact first-load corruption that
   // previously appeared as 15 pending transfers / £100m bank. Seed once only.
   st.lockedSquad=clone(st.squad);
   st.lockedBank=Number(st.bank??0);
   st.lockedCaptain=st.captain??null;
   st.lockedVice=st.vice??null;
   changed=true;
  }
 }
 if(validSquad(st.lockedSquad)&&(st.lockedBank===undefined||st.lockedBank===null||!Number.isFinite(Number(st.lockedBank)))){
  st.lockedBank=Number(cloud?.lockedBank??st.bank??0);changed=true;
 }
 return changed;
}
function canonicalBase(nativeBase){
 repairBaseline();const st=stateRef(),src=source();if(!st||!src||!st.teamConfirmed)return nativeBase;
 const locked=validSquad(st.lockedSquad)?st.lockedSquad:(validSquad(src.lockedSquad)?src.lockedSquad:src.squad);
 if(!validSquad(locked))return nativeBase;
 const bank=validSquad(st.lockedSquad)?Number(st.lockedBank??st.bank??0):Number(src.bank??0);
 const starters=validStarters(nativeBase?.starters)?nativeBase.starters:(validStarters(st.starters)?st.starters:[]);
 const bench=validBench(nativeBase?.bench)?nativeBase.bench:(validBench(st.bench)?st.bench:[]);
 const captain=nativeBase?.captain??st.lockedCaptain??st.captain??null;
 const vice=nativeBase?.vice??st.lockedVice??st.vice??null;
 return Object.assign({},nativeBase||{},{squad:clone(locked),bank,starters:clone(starters),bench:clone(bench),captain,vice});
}
let nativeBase=null,nativeSummary=null,nativePitch=null;
function install(){
 if(typeof window.transferSessionBase==='function'&&!window.transferSessionBase.__fmIntegrityGuard){
  nativeBase=window.transferSessionBase;
  const wrapped=function(...args){return canonicalBase(nativeBase.apply(this,args))};
  wrapped.__fmIntegrityGuard=true;wrapped.__fmOriginal=nativeBase;window.transferSessionBase=wrapped;
 }
 if(typeof window.renderTransferSummary==='function'&&!window.renderTransferSummary.__fmIntegrityGuard){
  nativeSummary=window.renderTransferSummary;
  const wrapped=function(...args){repairBaseline();return nativeSummary.apply(this,args)};
  wrapped.__fmIntegrityGuard=true;wrapped.__fmOriginal=nativeSummary;window.renderTransferSummary=wrapped;
 }
 if(typeof window.renderTransferPitch==='function'&&!window.renderTransferPitch.__fmIntegrityGuard){
  nativePitch=window.renderTransferPitch;
  const wrapped=function(...args){repairBaseline();return nativePitch.apply(this,args)};
  wrapped.__fmIntegrityGuard=true;wrapped.__fmOriginal=nativePitch;window.renderTransferPitch=wrapped;
 }
 return !!window.transferSessionBase;
}
function refresh(){repairBaseline();install();try{if(typeof renderTransferSummary==='function')renderTransferSummary();if(typeof renderTransferPitch==='function')renderTransferPitch()}catch(_e){}}
window.FMTransferIntegrityGuard={version:VERSION,install,repairBaseline,canonicalBase,refresh,status:()=>({version:VERSION,installed:!!window.transferSessionBase?.__fmIntegrityGuard,locked:arr(stateRef()?.lockedSquad).length,bank:stateRef()?.lockedBank})};
[0,100,350,900,2000].forEach(ms=>setTimeout(install,ms));
window.addEventListener('fmcloudready',()=>setTimeout(refresh,120));
window.addEventListener('fmcanonicalpublished',()=>setTimeout(refresh,120));
window.addEventListener('fmworldmanagersscored',()=>setTimeout(refresh,120));
document.addEventListener('click',e=>{const el=e.target?.closest?.('button,[data-page],[data-nav]');const text=String(el?.textContent||'').trim().toLowerCase();const key=String(el?.dataset?.page||el?.dataset?.nav||'').toLowerCase();if(text==='transfers'||key==='transfers')refresh()},true);
})();
