(()=>{
'use strict';
/* Presentation-only News layout. Do not read or mutate fantasy/import/manager state here. */
const VERSION='news-aesthetic-v34-six-equal-cards';
const IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions'];
const EMPTY_RX=/\b(?:no confirmed transfers|no transfers|no registration|no new registration|no changes|no active players|no news available|no items|nothing to show)\b/i;
const VIEW_RX=/^(?:show|view)\s*all(?:\s+\d+)?$/i;
let raf=0,busy=false;

function addStyles(){
  if(document.getElementById('fmNewsAestheticV34Styles'))return;
  const s=document.createElement('style');
  s.id='fmNewsAestheticV34Styles';
  s.textContent=`
    #fmNewsSixGrid{
      width:100%!important;
      min-width:0!important;
      display:grid!important;
      grid-template-columns:repeat(2,minmax(0,1fr))!important;
      grid-template-rows:repeat(3,minmax(0,1fr))!important;
      gap:12px!important;
      align-items:stretch!important;
      box-sizing:border-box!important;
      margin:0!important;
      padding:0!important;
    }
    #fmNewsSixGrid>#newsTransfers,
    #fmNewsSixGrid>#newsRegistrations,
    #fmNewsSixGrid>#newsPriceUp,
    #fmNewsSixGrid>#newsPriceDown,
    #fmNewsSixGrid>#newsInjuries,
    #fmNewsSixGrid>#newsSuspensions{
      grid-column:auto!important;
      grid-row:auto!important;
      width:100%!important;
      min-width:0!important;
      min-height:0!important;
      height:100%!important;
      max-height:none!important;
      margin:0!important;
      box-sizing:border-box!important;
      overflow:hidden!important;
      align-self:stretch!important;
    }
    #fmNewsSixGrid .newsHead{
      min-height:62px!important;
      box-sizing:border-box!important;
      display:flex!important;
      align-items:center!important;
      flex-wrap:nowrap!important;
      gap:10px!important;
      overflow:visible!important;
    }
    #fmNewsSixGrid .fmNewsViewAllV34{
      display:inline-flex!important;
      align-items:center!important;
      justify-content:center!important;
      flex:0 0 auto!important;
      min-height:28px!important;
      padding:6px 10px!important;
      margin-left:6px!important;
      border:1px solid rgba(255,255,255,.13)!important;
      border-radius:9px!important;
      background:rgba(255,255,255,.065)!important;
      color:#fff!important;
      font:800 10px/1 Inter,system-ui,sans-serif!important;
      letter-spacing:0!important;
      white-space:nowrap!important;
      cursor:pointer!important;
      opacity:1!important;
      visibility:visible!important;
      position:static!important;
      transform:none!important;
    }
    #fmNewsSixGrid .fmNewsViewAllV34:hover{background:rgba(255,255,255,.11)!important}
    #fmNewsSixGrid [data-news-toggle].fmNewsViewAllV34{max-width:none!important;max-height:none!important}
    @media(max-width:900px){
      #fmNewsSixGrid{
        height:auto!important;
        min-height:0!important;
        grid-template-columns:1fr!important;
        grid-template-rows:none!important;
        grid-auto-rows:minmax(220px,auto)!important;
      }
      #fmNewsSixGrid>#newsTransfers,
      #fmNewsSixGrid>#newsRegistrations,
      #fmNewsSixGrid>#newsPriceUp,
      #fmNewsSixGrid>#newsPriceDown,
      #fmNewsSixGrid>#newsInjuries,
      #fmNewsSixGrid>#newsSuspensions{min-height:220px!important;height:auto!important}
    }
  `;
  document.head.appendChild(s);
}

function cards(){return IDS.map(id=>document.getElementById(id)).filter(Boolean)}
function commonParent(nodes){if(nodes.length!==IDS.length)return null;const p=nodes[0].parentElement;return p&&nodes.every(n=>n.parentElement===p)?p:null}

function ensureGrid(){
  const cs=cards();if(cs.length!==IDS.length)return null;
  let grid=document.getElementById('fmNewsSixGrid');
  if(!grid){
    const parent=commonParent(cs);if(!parent)return null;
    grid=document.createElement('div');grid.id='fmNewsSixGrid';grid.dataset.fmPresentationOnly='1';
    parent.insertBefore(grid,cs[0]);
  }
  cs.forEach((card,i)=>{
    if(card.parentElement!==grid)grid.appendChild(card);
    card.dataset.fmNewsSlot=String(i+1);
    card.style.order=String(i+1);
  });
  return grid;
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
  const c=numericCount(head);if(c!==null)return c>0;
  const text=(card.textContent||'').replace(/\s+/g,' ').trim();
  if(!text||EMPTY_RX.test(text))return false;
  const bodyText=(Array.from(card.children).filter(n=>n!==head).map(n=>n.textContent||'').join(' ')).replace(/\s+/g,' ').trim();
  return !!bodyText&&!EMPTY_RX.test(bodyText);
}
function existingViewButtons(card){
  return Array.from(card.querySelectorAll('[data-news-toggle],button,a,[role="button"]')).filter(el=>{
    if(el.hasAttribute('data-news-toggle'))return true;
    return VIEW_RX.test((el.textContent||'').trim().replace(/\s+/g,' '));
  });
}
function placeViewAll(card){
  const head=headerOf(card);if(!head)return;
  const info=hasInfo(card,head),buttons=existingViewButtons(card);
  let btn=buttons[0]||null;
  if(!info){
    buttons.forEach(b=>{if(b.dataset.fmCreatedViewAllV34==='1')b.remove();else{b.classList.remove('fmNewsViewAllV34')}});
    return;
  }
  if(!btn){
    btn=document.createElement('button');btn.type='button';btn.dataset.newsToggle=card.id+'Full';btn.dataset.fmCreatedViewAllV34='1';btn.textContent='View all';
  }
  if(btn.parentElement!==head)head.appendChild(btn);
  btn.classList.add('fmNewsViewAllV34');btn.hidden=false;btn.removeAttribute('aria-hidden');btn.style.display='inline-flex';
  if(VIEW_RX.test((btn.textContent||'').trim().replace(/\s+/g,' ')))btn.textContent='View all';
  buttons.slice(1).forEach(b=>{if(b!==btn)b.style.display='none'});
}

function aboutBlock(grid){
  const parent=grid?.parentElement;if(!parent)return null;
  for(const el of Array.from(parent.children)){
    if(el===grid)continue;
    if(/about this data/i.test((el.textContent||'').replace(/\s+/g,' ')))return el;
  }
  return null;
}
function sizeGrid(grid){
  if(!grid)return;
  if(window.innerWidth<=900){grid.style.removeProperty('height');return}
  const top=grid.getBoundingClientRect().top;
  if(!Number.isFinite(top)||top<0)return;
  const about=aboutBlock(grid),aboutH=about?Math.ceil(about.getBoundingClientRect().height):0;
  const h=Math.max(510,Math.floor(window.innerHeight-top-aboutH-22));
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
