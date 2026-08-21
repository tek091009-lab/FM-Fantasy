(()=>{
'use strict';
const VERSION='transfer-integrity-guard-v1-locked-squad-authority';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
function stateRef(){try{return typeof state!=='undefined'?state:null}catch(_e){return null}}
function source(){
 const st=stateRef(),cloud=window.FMCloud?.managerState;
 if(arr(st?.lockedSquad).length===15)return st;
 if(arr(cloud?.lockedSquad).length===15)return cloud;
 if(st?.teamConfirmed&&arr(st?.squad).length===15)return st;
 if(cloud?.teamConfirmed&&arr(cloud?.squad).length===15)return cloud;
 return null;
}
function repairBaseline(){
 const st=stateRef(),src=source();if(!st||!src||!st.teamConfirmed)return false;
 let changed=false;
 if(arr(st.lockedSquad).length!==15&&arr(src.lockedSquad).length===15){st.lockedSquad=clone(src.lockedSquad);changed=true}
 if((st.lockedBank===undefined||st.lockedBank===null)&&src.lockedBank!==undefined){st.lockedBank=Number(src.lockedBank||0);changed=true}
 return changed;
}
function canonicalBase(nativeBase){
 repairBaseline();const st=stateRef(),src=source();if(!st||!src||!st.teamConfirmed)return nativeBase;
 const locked=arr(src.lockedSquad).length===15?src.lockedSquad:src.squad;
 if(arr(locked).length!==15)return nativeBase;
 return Object.assign({},nativeBase||{},
  {squad:clone(locked),bank:Number(src.lockedBank??src.bank??0),starters:clone(nativeBase?.starters??st.starters??[]),bench:clone(nativeBase?.bench??st.bench??[]),captain:nativeBase?.captain??st.captain??null,vice:nativeBase?.vice??st.vice??null});
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
window.FMTransferIntegrityGuard={version:VERSION,install,repairBaseline,canonicalBase,refresh,status:()=>({version:VERSION,installed:!!window.transferSessionBase?.__fmIntegrityGuard,locked:arr(stateRef()?.lockedSquad).length})};
[0,100,350,900,2000].forEach(ms=>setTimeout(install,ms));
window.addEventListener('fmcloudready',()=>setTimeout(refresh,120));
window.addEventListener('fmcanonicalpublished',()=>setTimeout(refresh,120));
window.addEventListener('fmworldmanagersscored',()=>setTimeout(refresh,120));
document.addEventListener('click',e=>{const el=e.target?.closest?.('button,[data-page],[data-nav]');const text=String(el?.textContent||'').trim().toLowerCase();const key=String(el?.dataset?.page||el?.dataset?.nav||'').toLowerCase();if(text==='transfers'||key==='transfers')refresh()},true);
})();
