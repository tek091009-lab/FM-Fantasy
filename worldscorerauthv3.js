(()=>{
'use strict';
const VERSION='world-scorer-auth-v3-shared-session-rpc';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const num=v=>Number(v||0)||0;
const has=(o,k)=>Object.prototype.hasOwnProperty.call(o||{},String(k));
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const chip=v=>String(v||'').toLowerCase().replace(/[^a-z]/g,'');
let busy=false,lastSig='',lastRun={version:VERSION,ok:false,error:'not run'};
function rpc(){return window.FMSessionRPC?.call}
function playerMap(payload){const m=new Map();for(const p of arr(payload?.players)){for(const k of [p?.pid,p?.id,p?.player_id]){const id=String(k??'');if(id)m.set(id,p)}}return m}
function pts(map,id,gw){return num(map.get(String(id))?.weekly_points?.[String(gw)])}
function appeared(map,id,gw){const p=map.get(String(id));return !!p&&has(p?.weekly_points||{},gw)}
function pos(map,id){return String(map.get(String(id))?.pos||'')}
function formation(map,ids){const c={GK:0,DEF:0,MID:0,FWD:0};for(const id of ids){const p=pos(map,id);if(p in c)c[p]++}return c}
function validFormation(c){return c.GK===1&&c.DEF>=3&&c.DEF<=5&&c.MID>=2&&c.MID<=5&&c.FWD>=1&&c.FWD<=3}
function doneGw(st){const entry=Math.max(1,num(st?.entryGameweek)||1),h=arr(st?.pointsHistory);return h.length?Math.max(entry-1,...h.map(x=>num(x?.gw))):entry-1}
function validSubmitted(st){
 const squad=arr(st?.squad).map(String).filter(Boolean),starters=arr(st?.starters).map(String).filter(Boolean),bench=arr(st?.bench).map(String).filter(Boolean);
 if(squad.length!==15||starters.length!==11||bench.length!==4)return false;
 if(new Set(squad).size!==15||new Set(starters).size!==11||new Set(bench).size!==4)return false;
 const sq=new Set(squad),ss=new Set(starters);if(starters.some(x=>!sq.has(x))||bench.some(x=>!sq.has(x)||ss.has(x)))return false;
 const cap=String(st?.captain||''),vice=String(st?.vice||'');return !!cap&&!!vice&&cap!==vice&&ss.has(cap)&&ss.has(vice);
}
function previousLineup(st,gw){
 const gl=st?.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{};
 const keys=Object.keys(gl).map(Number).filter(n=>Number.isFinite(n)&&n<gw).sort((a,b)=>b-a);if(keys.length)return clone(gl[String(keys[0])]||gl[keys[0]]);
 const hist=arr(st?.pointsHistory).filter(x=>num(x?.gw)<gw&&arr(x?.starters).length===11).sort((a,b)=>num(b?.gw)-num(a?.gw));return hist.length?clone(hist[0]):null;
}
function recoverPrior(st,prior,map,gw){
 if(!prior)return null;prior.gw=Number(gw);
 const locked=arr(st?.lockedSquad).length===15?arr(st.lockedSquad):arr(st?.squad).length===15?arr(st.squad):null;
 if(locked&&arr(prior?.squad).length){
   const old=arr(prior.squad).map(String),now=locked.map(String),outs=old.filter(x=>!now.includes(x)),ins=now.filter(x=>!old.includes(x));
   if(outs.length===ins.length&&outs.length){const remaining=[...ins],pairs=[];for(const out of outs){let ix=remaining.findIndex(x=>pos(map,x)&&pos(map,x)===pos(map,out));if(ix<0)ix=0;const incoming=remaining.splice(ix,1)[0];if(incoming)pairs.push([out,incoming])}const swap=a=>arr(a).map(x=>pairs.find(([o])=>String(o)===String(x))?.[1]||String(x));prior.starters=swap(prior.starters);prior.bench=swap(prior.bench);prior.squad=now}else if(!outs.length&&!ins.length)prior.squad=now;
 }
 const set=new Set(arr(prior?.squad).map(String));if(st?.captain&&set.has(String(st.captain)))prior.captain=String(st.captain);if(st?.vice&&set.has(String(st.vice)))prior.vice=String(st.vice);prior.chip=st?.activeChip||prior.chip||null;prior.hit=num(st?.transferHitThisGW||prior.hit);return prior;
}
function lineupFor(st,gw,map){
 const gl=st?.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{},exact=gl[String(gw)]||gl[gw];if(exact&&arr(exact?.starters).length===11)return clone(exact);
 if(arr(st?.starters).length===11)return {gw:Number(gw),squad:[...(arr(st?.squad).length===15?st.squad:st.lockedSquad||[])],starters:[...st.starters],bench:[...(st.bench||[])],captain:st.captain||null,vice:st.vice||null,chip:st.activeChip||null,hit:num(st.transferHitThisGW)};
 return recoverPrior(st,previousLineup(st,gw),map,gw);
}
function applyAutosubs(map,lineup,gw){
 const start=arr(lineup?.starters).map(String),bench=arr(lineup?.bench).map(String),effective=start.filter(id=>appeared(map,id,gw)),missing=start.filter(id=>!appeared(map,id,gw)),autosubs=[];
 const gkOut=missing.find(id=>pos(map,id)==='GK');if(gkOut){const gkIn=bench.find(id=>pos(map,id)==='GK'&&appeared(map,id,gw));if(gkIn){effective.push(gkIn);autosubs.push({in:gkIn,out:gkOut,reason:'No appearance'});missing.splice(missing.indexOf(gkOut),1)}}
 for(const b of bench){if(pos(map,b)==='GK'||!appeared(map,b,gw)||autosubs.some(x=>x.in===b))continue;let picked=-1;for(let i=0;i<missing.length;i++){if(pos(map,missing[i])==='GK')continue;if(validFormation(formation(map,[...effective,b]))){picked=i;break}}if(picked>=0){const out=missing.splice(picked,1)[0];effective.push(b);autosubs.push({in:b,out,reason:'No appearance'})}}
 return {effective,autosubs};
}
function score(map,lineup,gw){
 const starters=arr(lineup?.starters).map(String),bench=arr(lineup?.bench).map(String),squad=arr(lineup?.squad).map(String);if(starters.length!==11)return null;
 const ch=chip(lineup?.chip),benchBoost=ch.includes('bench'),triple=ch.includes('triple');let effective,autosubs;if(benchBoost){effective=[...starters,...bench];autosubs=[]}else({effective,autosubs}=applyAutosubs(map,lineup,gw));
 let captainApplied=null,captainMultiplier=1;const cap=String(lineup?.captain||''),vice=String(lineup?.vice||'');if(cap&&appeared(map,cap,gw)){captainApplied=cap;captainMultiplier=triple?3:2}else if(vice&&appeared(map,vice,gw)){captainApplied=vice;captainMultiplier=triple?3:2}
 const contributions={};for(const id of new Set([...squad,...starters,...bench]))contributions[id]=0;let gross=0;for(const id of effective){const v=pts(map,id,gw);gross+=v;contributions[id]=(contributions[id]||0)+v}
 let captainRaw=0,captainBonus=0;if(captainApplied){captainRaw=pts(map,captainApplied,gw);captainBonus=captainRaw*(captainMultiplier-1);gross+=captainBonus;contributions[captainApplied]=(contributions[captainApplied]||0)+captainBonus}
 const hit=num(lineup?.hit),net=gross-hit;return {gw:Number(gw),hit,net,chip:lineup?.chip||null,vice:lineup?.vice||null,bench,squad,captain:lineup?.captain||null,starters,gross,autosubs,captainRaw,provisional:false,captainBonus,captainApplied,captainMultiplier,effectiveStarters:effective,playerContributions:contributions};
}
function chipKey(v){const c=chip(v);if(c.includes('triple'))return'triple';if(c.includes('bench'))return'bench';if(c.includes('wildcard'))return'wildcard';return null}
function chipHalf(gw,payload){const total=Math.max(2,num(payload?.meta?.total_gameweeks)||46);return Number(gw)<=Math.ceil(total/2)?'first':'second'}
function reconcileChips(st,payload){st.chips=st.chips||{};st.chips.first=Object.assign({wildcard:false,triple:false,bench:false},st.chips.first||{});st.chips.second=Object.assign({wildcard:false,triple:false,bench:false},st.chips.second||{});for(const row of arr(st?.pointsHistory)){const key=chipKey(row?.chip);if(key)st.chips[chipHalf(num(row?.gw),payload)][key]=true}}
function applyResult(st,lineup,result,gw,payload){
 st.pointsHistory=arr(st.pointsHistory).filter(x=>num(x?.gw)!==gw);st.pointsHistory.push(result);st.pointsHistory.sort((a,b)=>num(a?.gw)-num(b?.gw));
 if(!st.gameweekLineups||typeof st.gameweekLineups!=='object'||Array.isArray(st.gameweekLineups))st.gameweekLineups={};st.gameweekLineups[String(gw)]={gw:Number(gw),squad:[...(lineup.squad||[])],starters:[...(lineup.starters||[])],bench:[...(lineup.bench||[])],captain:lineup.captain||null,vice:lineup.vice||null,chip:lineup.chip||null,hit:num(lineup.hit)};
 st.totalPoints=st.pointsHistory.reduce((n,x)=>n+num(x?.net??x?.gross),0);st.completedGameweek=gw;st.currentGameweek=gw+1;st.firstGameweekPlayed=true;
 if(num(st.lastTransferRollGW)<gw){st.freeTransfers=Math.min(5,Math.max(0,num(st.freeTransfers))+1);st.lastTransferRollGW=gw}st.transferHitThisGW=0;st.activeChip=null;reconcileChips(st,payload);
}
function identityMaps(items){const byTeam=new Map(),byName=new Map();for(const item of items){const st=item.state||{},team=norm(st.teamName||st.team||''),name=norm(st.managerName||st.name||'');if(team&&!byTeam.has(team))byTeam.set(team,item);if(name&&!byName.has(name))byName.set(name,item)}return {byTeam,byName}}
function memberPatch(source){const st=source?.state||{};return {points:num(st.totalPoints),totalPoints:num(st.totalPoints),pointsHistory:clone(arr(st.pointsHistory)),currentGameweek:num(st.currentGameweek)||Math.max(1,num(st.entryGameweek)||1),completedGameweek:doneGw(st),entryGameweek:Math.max(1,num(st.entryGameweek)||1),teamConfirmed:st.teamConfirmed===true,squad:clone(arr(st.squad)),starters:clone(arr(st.starters)),bench:clone(arr(st.bench)),captain:st.captain||null,vice:st.vice||null,gameweekLineups:clone(st.gameweekLineups&&typeof st.gameweekLineups==='object'?st.gameweekLineups:{})}}
function syncLeagues(item,maps){const st=item.state;if(!Array.isArray(st?.leagues))return;for(const league of st.leagues){if(!Array.isArray(league?.members))continue;for(const member of league.members){const source=maps.byTeam.get(norm(member?.team||member?.teamName||''))||maps.byName.get(norm(member?.name||member?.managerName||''));if(source)Object.assign(member,memberPatch(source))}}}
async function finaliseAll(force=false){
 if(busy||!window.FMCloud?.ready?.()||!window.FMCloud?.isCreator?.())return false;const call=rpc();if(typeof call!=='function'){lastRun={version:VERSION,ok:false,error:'shared session RPC unavailable'};return false}busy=true;
 try{
   const world=window.FMCloud.getWorld?.();if(!world?.id)throw new Error('World unavailable');const payload=force?await window.FMCloud.loadWorld?.(true):(world.payload||await window.FMCloud.loadWorld?.(true));if(!payload?.players)throw new Error('Canonical player payload unavailable');
   const target=num(payload?.meta?.completed_gameweek);if(!target)throw new Error('Completed Gameweek unavailable');const sig=`${world.id}|${target}|${world.updated_at||''}|${world.payload_version||0}`;if(!force&&sig===lastSig)return true;
   const rows=arr(await call('fmfantasy_creator_list_manager_states',{p_world_id:world.id})),map=playerMap(payload),items=rows.map(row=>({user_id:String(row?.user_id||''),original:clone(row?.state||{}),state:clone(row?.state||{}),from:doneGw(row?.state||{}),to:doneGw(row?.state||{}),scored:false}));let eligible=0;
   for(const item of items){const st=item.state;if(!(st.teamConfirmed===true||validSubmitted(st)))continue;eligible++;st.teamConfirmed=true;const entry=Math.max(1,num(st.entryGameweek)||1),oldDone=doneGw(st);let done=oldDone;for(let gw=Math.max(entry,oldDone+1);gw<=target;gw++){const lineup=lineupFor(st,gw,map);if(!lineup)break;const result=score(map,lineup,gw);if(!result)break;applyResult(st,lineup,result,gw,payload);done=gw}item.from=oldDone;item.to=done;item.scored=done>oldDone}
   const maps=identityMaps(items);for(const item of items)syncLeagues(item,maps);
   let changed=0;const scored=[];for(const item of items){if(!item.user_id||JSON.stringify(item.original)===JSON.stringify(item.state))continue;await call('fmfantasy_creator_save_manager_state',{p_world_id:world.id,p_user_id:item.user_id,p_state:item.state});changed++;if(item.scored)scored.push({user_id:item.user_id,from:item.from,to:item.to,total:num(item.state.totalPoints)})}
   lastSig=sig;lastRun={version:VERSION,ok:true,target,rows:rows.length,eligible,changed,scored,at:new Date().toISOString()};console.info('[FM world scorer V3]',lastRun);
   if(changed){window.dispatchEvent(new CustomEvent('fmworldmanagersscored',{detail:{gameweek:target,managers:changed,scored,source:VERSION}}));setTimeout(async()=>{try{await window.FMManagerStateAuthority?.refreshOwnFromServer?.();if(typeof renderAll==='function')renderAll();if(typeof renderLeagues==='function')renderLeagues()}catch(_e){}},180)}
   return true;
 }catch(e){lastRun={version:VERSION,ok:false,error:String(e?.message||e),at:new Date().toISOString()};console.warn('[FM world scorer V3] failed',e);return false}finally{busy=false}
}
window.FMWorldScorerV3={version:VERSION,finaliseAll,score,validSubmitted,status:()=>clone(lastRun)};
window.fmCreatorFinaliseWorldManagers=()=>finaliseAll(true);
const kick=()=>setTimeout(()=>finaliseAll(true),350);
window.addEventListener('fmcloudready',kick);window.addEventListener('fmcanonicalpublished',kick);window.addEventListener('focus',kick);document.addEventListener('visibilitychange',()=>{if(!document.hidden)kick()});
setInterval(()=>{if(window.FMCloud?.ready?.()&&window.FMCloud?.isCreator?.())finaliseAll(false)},5000);
})();
