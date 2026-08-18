(()=>{
'use strict';
const VERSION='import-model-v86-current-shirt-gk-pricing';
const arr=v=>Array.isArray(v)?v:[];
const num=v=>Number(v||0)||0;
const norm=v=>String(v??'').trim().toLowerCase();
const roundHalf=v=>Math.round((Number(v)||0)*2)/2;
const playerId=p=>String(p?.pid??p?.id??'');
const eligible=p=>p?.available!==false&&String(p?.available??'true')!=='false'&&p?.visible!==false&&String(p?.visible??'true')!=='false';
function startRows(p){return arr(p?.history).filter(h=>num(h?.minutes)>=60&&h?.date).map(h=>({date:String(h.date).slice(0,10),gw:num(h.gameweek)})).sort((a,b)=>a.date.localeCompare(b.date)||a.gw-b.gw)}
function applyCurrentShirtGKPricing(payload){
  const players=arr(payload?.players),byClub=new Map();
  for(const p of players){if(p?.pos!=='GK'||!eligible(p))continue;const club=String(p?.club||'');if(!club)continue;const a=byClub.get(club)||[];a.push(p);byClub.set(club,a)}
  const changes=[];
  for(const [club,gks] of byClub){
    if(gks.length<2)continue;
    const evidence=[];
    for(const p of gks){const rows=startRows(p);for(const r of rows)evidence.push({id:playerId(p),p,date:r.date,gw:r.gw})}
    if(!evidence.length)continue;
    evidence.sort((a,b)=>a.date.localeCompare(b.date)||a.gw-b.gw);
    const latest=evidence[evidence.length-1];
    const latestSame=evidence.filter(x=>x.date===latest.date&&x.gw===latest.gw);
    const latestIds=[...new Set(latestSame.map(x=>x.id))];
    if(latestIds.length!==1)continue;
    const owner=gks.find(p=>playerId(p)===latestIds[0]);if(!owner)continue;
    // Require a real current run, not a one-match emergency cameo. Two 60+ minute
    // selected-league starts are enough, and we also count the uninterrupted run from
    // the most recent keeper-start rows so a mid-season arrival is recognised quickly.
    const ownerRows=startRows(owner);let consecutive=0;
    const uniqueMatches=[];const seen=new Set();
    for(let i=evidence.length-1;i>=0;i--){const e=evidence[i],k=`${e.date}|${e.gw}`;if(seen.has(k))continue;seen.add(k);uniqueMatches.push(e)}
    for(const e of uniqueMatches){if(e.id===playerId(owner))consecutive++;else break}
    const robust=consecutive>=2||ownerRows.length>=2&&num(owner?.starts)>=2;
    if(!robust)continue;
    const before=Object.fromEntries(gks.map(p=>[playerId(p),num(p.price)]));
    const highest=Math.max(...gks.map(p=>num(p.price)||4));
    const ownerPrice=roundHalf(Math.max(num(owner.price)||4,highest));
    const setPrice=(p,v)=>{v=roundHalf(Math.max(4,v));p.price=v;p.model_price=v;p.launch_price=v;p.dynamic_price=v;const c=p.price_context||(p.price_context={});c.price=v;c.current_shirt_owner=p===owner;c.current_shirt_owner_id=playerId(owner);c.current_shirt_latest_start=latest.date;c.current_shirt_consecutive_starts=consecutive;c.gk_price_priority='current selected-league shirt ownership > CA/reputation';c.pricing_model_version=VERSION};
    setPrice(owner,ownerPrice);
    for(const p of gks){if(p===owner)continue;let v=num(p.price)||4;if(v>=ownerPrice)v=Math.max(4,ownerPrice-.5);setPrice(p,v)}
    const after=Object.fromEntries(gks.map(p=>[playerId(p),num(p.price)]));
    if(JSON.stringify(before)!==JSON.stringify(after))changes.push({club,owner:playerId(owner),latest_start:latest.date,consecutive_starts:consecutive,before,after});
  }
  payload.meta=payload.meta||{};payload.meta.gk_pricing_model=VERSION;payload.meta.gk_pricing_policy='within-club current selected-league shirt ownership and recent consecutive starts outrank CA/reputation';payload.meta.gk_current_shirt_price_changes=changes.length;payload.meta.gk_current_shirt_price_change_details=changes;return payload;
}
function transform(payload){if(!payload||!Array.isArray(payload.players))return payload;let mode='';try{mode=norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_e){}if(mode==='season')applyCurrentShirtGKPricing(payload);return payload}
function install(){
  let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
  if(typeof original!=='function'||!original.__fmV86Post||original.__fmV86Wrapped)return false;
  const wrapped=function(payload,...args){const out=original(payload,...args);transform(payload);try{if(typeof FM_DEBUG!=='undefined')FM_DEBUG.lastMeta=payload?.meta||null;if(typeof fmDebugAdd==='function')fmDebugAdd('info','V86 current-shirt goalkeeper pricing finaliser applied.',{changes:payload?.meta?.gk_current_shirt_price_changes||0})}catch(_e){}return out};
  wrapped.__fmV86Wrapped=true;wrapped.__fmV86Post=true;wrapped.__fmV85Wrapped=true;wrapped.__fmV86Original=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true;
}
window.FMImportModelV86={version:VERSION,transform,applyCurrentShirtGKPricing,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>100)clearInterval(timer)},100);install();
})();
