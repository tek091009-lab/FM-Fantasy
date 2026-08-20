(()=>{
'use strict';
const VERSION='historical-boundary-v12-canonical-through-completed-gw';
const clone=v=>v==null?v:JSON.parse(JSON.stringify(v));
const arr=v=>Array.isArray(v)?v:[];
const num=v=>Number(v||0)||0;
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const playerId=p=>String(p?.pid??p?.player_id??p?.person_id??p?.eid??p?.id??'');
const fixtureId=x=>String(x?.fixture_id??x?.id??'');
const fixtureGw=x=>num(x?.gameweek??x?.gw??x?.round_gameweek);
const dateKey=x=>String(x?.date||'').slice(0,10);
function teamName(x,s){return norm(x?.[s]??x?.[s+'_team']??x?.[s+'_name']??x?.[s+'_club']??'')}
function compKey(p){return norm(p?.meta?.competition_code||p?.meta?.competition||'')}
function matchFallbackKey(m){const h=teamName(m,'home'),a=teamName(m,'away'),d=dateKey(m);return h&&a&&d?`${h}|${a}|${d}`:''}
function activeMode(meta){const x=norm(meta?.import_mode||meta?.importMode||'');if(x)return x;try{return norm(window.__FM_IMPORT_MODE_ACTIVE||'')}catch(_){return ''}}
function histGw(h){return num(h?.gameweek??h?.gw)}
function histDate(h){return dateKey(h)}
function isAfterBoundary(h,oldDone,oldSnapshot){const gw=histGw(h);if(gw)return gw>oldDone;const d=histDate(h);return !!(d&&oldSnapshot&&d>oldSnapshot)}
function sortHistory(rows){return rows.slice().sort((a,b)=>String(a?.date||'').localeCompare(String(b?.date||''))||histGw(a)-histGw(b)||num(a?.match_id)-num(b?.match_id))}
function recomputePlayer(p,startsByPlayer){
 const hs=sortHistory(arr(p?.history));const sum=k=>hs.reduce((z,h)=>z+num(h?.[k]),0);
 p.apps=hs.reduce((z,h)=>z+(num(h?.minutes)>0?1:0),0);p.minutes=sum('minutes');p.goals=sum('goals');p.assists=sum('assists');p.yc=sum('yc');p.rc=sum('rc');p.saves=sum('saves');p.gc=sum('gc');
 const pts=sum('fpl_points');p.fantasy_points=pts;p.points=pts;
 const ratings=hs.map(h=>Number(h?.rating)).filter(Number.isFinite);p.avg_rating=ratings.length?Math.round((ratings.reduce((a,b)=>a+b,0)/ratings.length)*100)/100:0;
 const tail=hs.slice(-4);const form=tail.length?Math.round((tail.reduce((z,h)=>z+num(h?.fpl_points),0)/tail.length)*10)/10:0;p.form_points=form;p.form=form;
 if(startsByPlayer&&startsByPlayer.has(playerId(p)))p.starts=num(startsByPlayer.get(playerId(p)));return p;
}
function freezePlayerHistory(payload,old,oldDone){
 const oldSnapshot=String(old?.meta?.snapshot_date||'').slice(0,10),oldById=new Map(arr(old?.players).map(p=>[playerId(p),p]).filter(([id])=>id)),startsByPlayer=new Map();
 for(const [id,p] of oldById)startsByPlayer.set(id,num(p?.starts));
 for(const m of arr(payload?.matches)){if(fixtureGw(m)<=oldDone)continue;for(const r of [...arr(m?.home_players),...arr(m?.away_players)]){const id=String(r?.player_id??'');if(!id||num(r?.minutes)<=0)continue;if(num(r?.sub_on)<=0)startsByPlayer.set(id,num(startsByPlayer.get(id))+1)}}
 let playersPreserved=0,oldHistoryRows=0,newHistoryRows=0,retroRowsDropped=0;
 for(const p of arr(payload?.players)){
   const id=playerId(p),op=oldById.get(id),incoming=arr(p?.history),newRows=incoming.filter(h=>isAfterBoundary(h,oldDone,oldSnapshot));retroRowsDropped+=incoming.length-newRows.length;
   if(op){const oldRows=arr(op?.history).filter(h=>!isAfterBoundary(h,oldDone,oldSnapshot));oldHistoryRows+=oldRows.length;newHistoryRows+=newRows.length;p.history=sortHistory([...clone(oldRows),...newRows]);const wp={};for(const [gw,v] of Object.entries(op?.weekly_points||{}))if(num(gw)<=oldDone)wp[gw]=clone(v);for(const [gw,v] of Object.entries(p?.weekly_points||{}))if(num(gw)>oldDone)wp[gw]=clone(v);p.weekly_points=wp;playersPreserved++}
   else{p.history=sortHistory(newRows);p.weekly_points=Object.fromEntries(Object.entries(p?.weekly_points||{}).filter(([gw])=>num(gw)>oldDone));newHistoryRows+=newRows.length}
   recomputePlayer(p,startsByPlayer);
 }
 return {players_preserved:playersPreserved,old_history_rows:oldHistoryRows,new_history_rows:newHistoryRows,retro_history_rows_dropped:retroRowsDropped};
}
function freezeHistoricalMatches(payload,old,oldDone){
 const canonical=arr(old?.matches).filter(m=>fixtureGw(m)<=oldDone),oldIds=new Set(canonical.map(fixtureId).filter(Boolean)),oldFallback=new Set(canonical.map(matchFallbackKey).filter(Boolean)),incoming=arr(payload?.matches);let replaced=0,droppedBackfills=0;
 for(const m of incoming){if(fixtureGw(m)>oldDone)continue;const id=fixtureId(m),fk=matchFallbackKey(m);if((id&&oldIds.has(id))||(fk&&oldFallback.has(fk)))replaced++;else droppedBackfills++}
 const future=incoming.filter(m=>fixtureGw(m)>oldDone);payload.matches=[...clone(canonical),...future];payload.meta=payload.meta||{};payload.meta.rich_matches=payload.matches.length;if(num(payload.meta.played_results)>0)payload.meta.rich_matches_missing=Math.max(0,num(payload.meta.played_results)-payload.matches.length);
 return {canonical_matches_preserved:canonical.length,redecoded_historical_rows_replaced:replaced,retroactive_backfill_rows_dropped:droppedBackfills,newer_match_rows_retained:future.length};
}
function rebaseDynamicPricing(old,payload){try{const fn=window.FMDynamicPricingV13?.applyDynamicPricing;if(typeof fn!=='function')return false;fn(old,payload,{});return true}catch(e){console.warn('[FM historical boundary] dynamic pricing rebase failed',e);return false}}
function apply(payload,old){
 if(!payload||!old||activeMode(payload?.meta)!=='update'||!arr(old?.players).length)return null;if(!compKey(old)||compKey(old)!==compKey(payload))return null;const oldDone=num(old?.meta?.completed_gameweek);if(oldDone<=0)return null;
 const m=freezeHistoricalMatches(payload,old,oldDone),p=freezePlayerHistory(payload,old,oldDone),pricingRebased=rebaseDynamicPricing(old,payload);payload.meta=payload.meta||{};payload.meta.historical_match_freeze_v12={version:VERSION,policy:'same-world weekly updates keep all match and player history through the previously completed Gameweek exactly canonical; later saves may append only post-boundary history, never rewrite or backfill earlier fantasy scoring',old_completed_gameweek:oldDone,old_snapshot_date:String(old?.meta?.snapshot_date||'').slice(0,10)||null,dynamic_pricing_rebased_on_frozen_history:pricingRebased,...m,...p};payload.meta.historical_freeze_policy='canonical-through-previous-completed-gameweek-v12';return payload.meta.historical_match_freeze_v12;
}
function install(){
 const c=window.FMCloud;if(!c||!c.__worldUpdateGuardV11||c.__historicalBoundaryV12||typeof c.publishWorld!=='function')return false;c.__historicalBoundaryV12=true;const guarded=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{if(payload!=null){let old=null;try{old=clone(c.getWorld?.()?.payload||null)}catch(_){}const diag=apply(payload,old);if(diag)console.info('[FM historical boundary]',diag)}return guarded(payload,...args)};
 window.FMHistoricalBoundary={version:VERSION,apply};return true;
}
window.FMHistoricalBoundary={version:VERSION,apply};window.addEventListener('fmcloudready',()=>setTimeout(install,0));let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>60)clearInterval(timer)},100);
})();