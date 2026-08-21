(()=>{
'use strict';
const VERSION='manager-score-bridge-v1-valid-lineup-authority';
const arr=v=>Array.isArray(v)?v:[];
const id=v=>String(v??'');
function validSubmittedLineup(st){
 if(!st||typeof st!=='object')return false;
 const squad=arr(st.squad).map(id).filter(Boolean),starters=arr(st.starters).map(id).filter(Boolean),bench=arr(st.bench).map(id).filter(Boolean);
 if(squad.length!==15||starters.length!==11||bench.length!==4)return false;
 if(new Set(squad).size!==15||new Set(starters).size!==11||new Set(bench).size!==4)return false;
 const sq=new Set(squad),ss=new Set(starters);if(starters.some(x=>!sq.has(x))||bench.some(x=>!sq.has(x)||ss.has(x)))return false;
 const cap=id(st.captain),vice=id(st.vice);if(!cap||!vice||cap===vice||!ss.has(cap)||!ss.has(vice))return false;
 return true;
}
function repairRows(rows){return arr(rows).map(row=>{const st=row?.state;if(!st||st.teamConfirmed===true||!validSubmittedLineup(st))return row;return {...row,state:{...st,teamConfirmed:true,team_confirmation_source:'valid-submitted-lineup-v1'}}})}
function installRpc(){const c=window.FMCloud;if(!c||c.__managerScoreRpcBridgeV1||typeof c.rpc!=='function')return false;c.__managerScoreRpcBridgeV1=true;const original=c.rpc.bind(c);c.rpc=async(name,args)=>{const result=await original(name,args);return name==='fmfantasy_creator_list_manager_states'?repairRows(result):result};return true}
async function finaliseAfterPublish(){for(let i=0;i<8;i++){try{const fn=globalThis.fmCreatorFinaliseWorldManagers;if(typeof fn==='function'){await fn(true);return true}}catch(e){console.warn('[FM manager score bridge] creator finalise retry',e)}await new Promise(r=>setTimeout(r,250))}return false}
function installPublish(){const c=window.FMCloud;if(!c||c.__managerScorePublishBridgeV1||typeof c.publishWorld!=='function')return false;c.__managerScorePublishBridgeV1=true;const original=c.publishWorld.bind(c);c.publishWorld=async(payload,...args)=>{const result=await original(payload,...args);if(payload!=null){const ok=await finaliseAfterPublish();if(!ok)console.warn('[FM manager score bridge] successful world publish completed but manager scoring will retry from the normal scorer loop')}return result};return true}
function install(){installRpc();return installPublish()}
window.FMManagerScoreBridge={version:VERSION,validSubmittedLineup,repairRows,install,finaliseAfterPublish};window.addEventListener('fmcloudready',()=>setTimeout(install,0));let tries=0;const timer=setInterval(()=>{tries++;installRpc();if(installPublish()||tries>120)clearInterval(timer)},100);
})();