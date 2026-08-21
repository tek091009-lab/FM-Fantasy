(()=>{
'use strict';
/* Presentation-only News layout. No fantasy state is read or mutated here. */
const VERSION='news-aesthetic-v35-full-width-parent-grid';
const GRID_ID='fmNewsSixGrid';
const IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions'];
const EMPTY_RX=/\b(?:no confirmed transfers|no transfers|no registration|no new registration|no changes|no active players|no news available|no items|nothing to show)\b/i;
let raf=0,busy=false;

function addStyles(){
  if(document.getElementById('fmNewsAestheticV35Styles'))return;
  const s=document.createElement('style');
  s.id='fmNewsAestheticV35Styles';
  s.textContent=`
    #newsPage{width:100%!important;max-width:none!important;min-width:0!important}
    #${GRID_ID}{
      width:100%!important;
      max-width:none!important;
      min-width:0!important;
      display:grid!important;
      grid-template-columns:repeat(2,minmax(0,1fr))!important;
      grid-template-rows:repeat(3,minmax(0,1fr)) auto!important;
      grid-auto-flow:row!important;
      gap:12px!important;
      align-items:stretch!important;
      box-sizing:border-box!important;
      margin:0!important;
      padding:0!important;
    }
    #${GRID_ID}>#newsTransfers,
    #${GRID_ID}>#newsRegistrations,
    #${GRID_ID}>#newsPriceUp,
    #${GRID_ID}>#newsPriceDown,
    #${GRID_ID}>#newsInjuries,
    #${GRID_ID}>#newsSuspensions{
      grid-column:auto!important;
      grid-row:auto!important;
      width:100%!important;
      max-width:none!important;
      min-width:0!important;
      min-height:0!important;
      height:100%!important;
      max-height:none!important;
      margin:0!important;
      box-sizing:border-box!important;
      overflow:hidden!important;
      align-self:stretch!important;
    }
    #${GRID_ID}>[data-fm-news-full-width-v35="1"]{
      grid-column:1/-1!important;
      width:100%!important;
      max-width:none!important;
      min-width:0!important;
      margin-left:0!important;
      margin-right:0!important;
      box-sizing:border-box!important;
    }
    #${GRID_ID} .newsHead{
      min-height:62px!important;
      box-sizing:border-box!important;
      display:flex!important;
      align-items:center!important;
      flex-wrap:nowrap!important;
      gap:10px!important;
      overflow:visible!important;
    }
    #${GRID_ID} .fmNewsViewAllV34{
      display:inline-flex!important;
      align-items:center!important;
      justify-content:center!important;
      flex:0 0 auto!important;
      min-height:28px!important;
      padding:6px 10px!important;
      margin-left:auto!important;
      border:1px solid rgba(255,255,255,.13)!important;
      border-radius:9px!important;
      background:rgba(255,255,255,.065)!important;
      color:#fff!important;
      font:800 10px/1 Inter,system-ui,sans-serif!important;
      white-space:nowrap!important;
      cursor:pointer!important;
      opacity:1!important;
      visibility:visible!important;
      position:static!important;
      transform:none!important;
    }
    #${GRID_ID} .fmNewsViewAllV34:hover{background:rgba(255,255,255,.11)!important}
    @media(max-width:900px){
      #${GRID_ID}{
        height:auto!important;
        min-height:0!important;
        grid-template-columns:1fr!important;
        grid-template-rows:none!important;
        grid-auto-rows:minmax(220px,auto)!important;
      }
      #${GRID_ID}>#newsTransfers,
      #${GRID_ID}>#newsRegistrations,
      #${GRID_ID}>#newsPriceUp,
      #${GRID_ID}>#newsPriceDown,
      #${GRID_ID}>#newsInjuries,
      #${GRID_ID}>#newsSuspensions{min-height:220px!important;height:auto!important}
    }
  `;
  document.head.appendChild(s);
}

function cards(){return IDS.map(id=>document.getElementById(id)).filter(Boolean)}
function commonParent(nodes){if(nodes.length!==IDS.length)return null;const p=nodes[0].parentElement;return p&&nodes.every(n=>n.parentElement===p)?p:null}

function unwrapLegacyGrid(cs){
  const old=document.getElementById(GRID_ID);
  if(!old||old.dataset.fmParentGridV35==='1')return;
  if(!cs.length||!cs.every(card=>card.parentElement===old))return;
  const parent=old.parentElement;if(!parent)return;
  cs.forEach(card=>parent.insertBefore(card,old));
  old.remove();
}

function ensureGrid(){
  let cs=cards();if(cs.length!==IDS.length)return null;
  unwrapLegacyGrid(cs);
  cs=cards();
  const parent=commonParent(cs);if(!parent)return null;
  const stale=document.getElementById(GRID_ID);
  if(stale&&stale!==parent)stale.removeAttribute('id');
  parent.id=GRID_ID;
  parent.dataset.fmPresentationOnly='1';
  parent.dataset.fmParentGridV35='1';
  cs.forEach((card,i)=>{
    card.dataset.fmNewsSlot=String(i+1);
    card.style.order=String(i+1);
    delete card.dataset.fmNewsFullWidthV35;
  });
  for(const el of Array.from(parent.children)){
    if(IDS.includes(el.id))continue;
    el.dataset.fmNewsFullWidthV35='1';
    el.style.order='99';
  }
  return parent;
}

function headerOf(card){return card.querySelector('.newsHead')||card.firstElementChild||null}
function numericCount(head){
  if(!head)return null;
  const vals=[];
  for(const el of head.querySelectorAll('*')){
    if(el.children.length)continue;
    const t=(el.textContent||'').trim();if(/^\d{1,4}$/.test(t))vals.push(Number(t));
  }
  return vals.length?vals[vals.length-1]:null;
}
function hasInfo(card,head){
  if(card.id==='newsTransfers'){
    const host=card.querySelector('.fmCanonicalTransferRows');
    if(host)return !!host.querySelector('.fmNewsTransferRow');
  }
  if(card.id==='newsRegistrations'){
    const host=card.querySelector('.newsRegRows');
    if(host)return !!host.querySelector('.newsRegRow');
  }
  const c=numericCount(head);if(c!==null)return c>0;
  const rows=Array.from(card.querySelectorAll('[data-news-text],.newsRow,.newsItem')).filter(el=>!EMPTY_RX.test((el.textContent||'').replace(/\s+/g,' ')));
  if(rows.length)return true;
  const bodyText=(Array.from(card.children).filter(n=>n!==head).map(n=>n.textContent||'').join(' ')).replace(/\s+/g,' ').trim();
  return !!bodyText&&!EMPTY_RX.test(bodyText);
}
function bodyViewButtons(card){
  return Array.from(card.querySelectorAll('[data-news-toggle],button,a,[role="button"]')).filter(el=>{
    if(el.classList.contains('fmNewsViewAllV34'))return false;
    return el.hasAttribute('data-news-toggle')||/^(?:show|view)\s*all(?:\s+\d+)?$/i.test((el.textContent||'').trim().replace(/\s+/g,' '));
  });
}
function placeViewAll(card){
  const head=headerOf(card);if(!head)return;
  const info=hasInfo(card,head),originals=bodyViewButtons(card);
  originals.forEach(b=>{b.dataset.fmHiddenBodyViewV34='1';b.style.display='none'});
  let btn=head.querySelector('.fmNewsViewAllV34[data-fm-created-view-all-v34="1"]');
  if(!info){if(btn)btn.remove();return}
  if(!btn){
    btn=document.createElement('button');
    btn.type='button';
    btn.dataset.newsToggle=card.id+'Full';
    btn.dataset.fmCreatedViewAllV34='1';
    btn.className='fmNewsViewAllV34';
    btn.textContent='View all';
    head.appendChild(btn);
  }
  btn.hidden=false;btn.removeAttribute('aria-hidden');btn.style.display='inline-flex';
}

function sizeGrid(grid){
  if(!grid)return;
  if(window.innerWidth<=900){grid.style.removeProperty('height');return}
  const top=grid.getBoundingClientRect().top;
  if(!Number.isFinite(top)||top<0)return;
  const h=Math.max(620,Math.floor(window.innerHeight-top-10));
  grid.style.height=h+'px';
}

function apply(){
  busy=true;
  try{
    addStyles();const grid=ensureGrid();if(!grid)return false;
    cards().forEach(placeViewAll);sizeGrid(grid);return true;
  }finally{busy=false}
}
function schedule(){if(busy||raf)return;raf=requestAnimationFrame(()=>{raf=0;apply()})}

addStyles();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
window.addEventListener('resize',schedule,{passive:true});
window.addEventListener('fmcloudready',schedule);window.addEventListener('fmworldloaded',schedule);window.addEventListener('fmcanonicalpublished',schedule);
new MutationObserver(()=>schedule()).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
setTimeout(schedule,0);setTimeout(schedule,300);setTimeout(schedule,1200);
window.FMNewsAestheticV34={version:VERSION,apply,schedule};
})();
