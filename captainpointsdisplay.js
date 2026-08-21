(()=>{
'use strict';
const VERSION='captain-points-display-v2-viewed-manager-context';
const num=v=>Number(v||0)||0;
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const arr=v=>Array.isArray(v)?v:[];
let patching=false;
function stateRef(){try{return typeof state!=='undefined'?state:null}catch(_e){return null}}
function payload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function viewedMember(){
 const st=stateRef(),banner=document.getElementById('viewBanner');if(!st||!banner?.classList.contains('show'))return null;
 const label=document.getElementById('viewTeamName'),wanted=norm(String(label?.textContent||'').replace(/^Viewing\s+/i,''));if(!wanted)return null;
 const members=[];for(const league of arr(st.leagues))for(const m of arr(league?.members))members.push(m);
 return members.find(m=>norm(m?.team||m?.teamName)===wanted)||members.find(m=>norm(m?.name||m?.managerName)===wanted)||null;
}
function contextState(){return viewedMember()||stateRef()}
function viewedGw(){
 const page=document.getElementById('teamPage');
 const labels=page?[...page.querySelectorAll('.pitchTopControls .gwNav b,.gwNav b,[data-gw-label],#teamGWSum,#teamGWLabel')]:[];
 for(const el of labels){const m=String(el?.textContent||'').match(/(?:Gameweek\s*|GW\s*)?(\d{1,2})/i);if(m){const n=Number(m[1]);if(n>=1&&n<=99)return n}}
 const st=contextState();
 for(const k of ['viewGameweek','viewedGameweek','selectedGameweek','displayGameweek','currentGameweek']){const n=Number(st?.[k]||0);if(n>0)return n}
 return Number(payload()?.meta?.current_gameweek||0)||1;
}
function lineupForGw(gw){
 const st=contextState();if(!st)return null;
 const gl=st.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{};
 const exact=gl[String(gw)]||gl[gw];if(exact)return exact;
 const hist=arr(st.pointsHistory).find(x=>Number(x?.gw)===Number(gw));if(hist)return hist;
 return {captain:st.captain||null,vice:st.vice||null,chip:st.activeChip||null};
}
function multiplier(lineup){const c=norm(lineup?.chip);return c.includes('triple')?3:2}
function playerMap(){const map=new Map();for(const p of arr(payload()?.players)){for(const k of [p?.pid,p?.id,p?.player_id]){const id=String(k??'');if(id)map.set(id,p)}}return map}
function hasAppearance(p,gw){return !!p&&p.weekly_points&&Object.prototype.hasOwnProperty.call(p.weekly_points,String(gw))}
function effectiveCaptain(lineup,gw,map){
 const cap=String(lineup?.captain||''),vice=String(lineup?.vice||'');
 if(cap&&hasAppearance(map.get(cap),gw))return cap;
 if(vice&&hasAppearance(map.get(vice),gw))return vice;
 return cap||'';
}
function publicName(p){return String(p?.public_name||p?.display_name||p?.name||p?.legal_name||'').trim()}
function cardFor(id,p){
 const page=document.getElementById('teamPage');if(!page)return null;
 const esc=globalThis.CSS?.escape?CSS.escape(String(id)):String(id).replace(/(["'\\])/g,'\\$1');
 const selectors=[`[data-open-player="${esc}"]`,`[data-player-id="${esc}"]`,`[data-player="${esc}"]`,`[data-pid="${esc}"]`,`[data-id="${esc}"]`];
 for(const s of selectors){try{const hit=page.querySelector(s);if(hit)return hit.classList?.contains('pchip')?hit:hit.closest?.('.pchip')||hit}catch(_e){}}
 const want=norm(publicName(p));if(want){for(const card of page.querySelectorAll('.pchip')){const b=card.querySelector('b');if(norm(b?.textContent)===want)return card}}
 return null;
}
function pointNode(card,raw){
 const nodes=[...card.querySelectorAll('[data-player-points],[data-points],.playerPoints,.player-points,.points,.pts,span,small')]
   .filter(el=>!el.classList.contains('captag')&&!el.classList.contains('statusFlag'));
 const parsed=nodes.map(el=>{const t=String(el.textContent||'').trim();const m=t.match(/^(-?\d+)\s*(pts?|points?)?$/i);return m?{el,value:Number(m[1]),suffix:m[2]?` ${m[2]}`:''}:null}).filter(Boolean);
 const explicit=parsed.find(x=>/points|pts/i.test(String(x.el.className||''))||/pts?|points?/i.test(x.suffix));
 if(explicit)return explicit;
 const exact=parsed.find(x=>x.value===Number(raw));if(exact)return exact;
 return parsed.length===1?parsed[0]:null;
}
function patch(){
 if(patching)return;patching=true;
 try{
  const page=document.getElementById('teamPage');if(!page||!page.classList.contains('active'))return;
  const gw=viewedGw(),lineup=lineupForGw(gw);if(!lineup)return;
  const map=playerMap(),cid=effectiveCaptain(lineup,gw,map),p=map.get(cid);if(!cid||!p||!hasAppearance(p,gw))return;
  const raw=num(p.weekly_points?.[String(gw)]),mult=multiplier(lineup),expected=raw*mult,card=cardFor(cid,p);if(!card)return;
  const found=pointNode(card,raw);if(!found)return;
  const suffix=found.suffix||'',next=`${expected}${suffix}`;
  if(String(found.el.textContent||'').trim()!==next)found.el.textContent=next;
  card.dataset.fmCaptainPointsDisplay=VERSION;card.dataset.fmCaptainRaw=String(raw);card.dataset.fmCaptainMultiplier=String(mult);
 }finally{patching=false}
}
function schedule(){requestAnimationFrame(patch);setTimeout(patch,40);setTimeout(patch,180)}
window.FMCaptainPointsDisplay={version:VERSION,patch,viewedGw,lineupForGw,effectiveCaptain,viewedMember,contextState};
window.addEventListener('fmcloudready',schedule);window.addEventListener('fmworldloaded',schedule);window.addEventListener('fmworldmanagersscored',schedule);window.addEventListener('fmmanagerprogressfinalised',schedule);window.addEventListener('focus',schedule);
document.addEventListener('click',e=>{if(e.target.closest?.('#teamPage .gwArrow,#teamPage .gwNav,button[data-nav="team"],button[data-page="team"],#viewBanner'))schedule()},true);
new MutationObserver(muts=>{if(patching)return;if(muts.some(m=>m.target?.closest?.('#teamPage')||[...m.addedNodes].some(n=>n?.nodeType===1&&(n.id==='teamPage'||n.querySelector?.('#teamPage,.pchip')))))schedule()}).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
setTimeout(schedule,700);
})();
