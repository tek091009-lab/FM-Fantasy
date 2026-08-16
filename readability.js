(()=>{
  const STYLE_ID='fmReadabilityPass';
  const SKIP_CLOSEST='.pitch,.playerCard,.player-card,.shirt,.kit,.avatar,.navIcon,.icon,[class*="pitchPlayer"],[class*="playerTile"]';

  function addStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const s=document.createElement('style');
    s.id=STYLE_ID;
    s.textContent=`
      /* Keep the visual identity, but make supporting copy substantially easier to read. */
      .page.active:not(#teamPage) p,
      .page.active:not(#teamPage) li,
      .page.active:not(#teamPage) label{line-height:1.42!important}

      .page.active:not(#teamPage) small,
      .page.active:not(#teamPage) [class*="sub"],
      .page.active:not(#teamPage) [class*="desc"],
      .page.active:not(#teamPage) [class*="muted"],
      .page.active:not(#teamPage) [class*="meta"]{line-height:1.4!important}

      /* Rules was the clearest example of text being too compressed. */
      #rulesPage h2,#rulesPage .sectionTitle{font-size:17px!important;line-height:1.2!important}
      #rulesPage h3{font-size:14px!important;line-height:1.25!important}
      #rulesPage p,#rulesPage li,#rulesPage label{line-height:1.5!important}
      #rulesPage .card,
      #rulesPage [class*="ruleCard"],#rulesPage [class*="rule-card"],
      #rulesPage [class*="rulesCard"],#rulesPage [class*="rules-card"]{padding:16px!important}
      #rulesPage [class*="ruleGrid"],#rulesPage [class*="rule-grid"],
      #rulesPage [class*="rulesGrid"],#rulesPage [class*="rules-grid"]{gap:14px!important}

      /* Dense data pages: slightly taller rows make the larger type breathe. */
      #statsPage td,#statsPage th,
      #transfersPage td,#transfersPage th,
      #leagueTablePage td,#leagueTablePage th,
      #fixturesPage td,#fixturesPage th{padding-top:8px!important;padding-bottom:8px!important}

      #statsPage [class*="leader"],#statsPage [class*="insight"],
      #leaguesPage [class*="league"],#newsPage [class*="news"]{line-height:1.38!important}

      @media (max-width:1100px){
        #rulesPage .card,
        #rulesPage [class*="ruleCard"],#rulesPage [class*="rule-card"]{padding:13px!important}
      }
    `;
    document.head.appendChild(s);
  }

  function pageMinimum(root){
    const id=(root?.id||'').toLowerCase();
    if(id.includes('rules')) return 12;
    if(id.includes('stats')) return 11;
    if(id.includes('transfer')) return 11;
    if(id.includes('league')) return 11;
    if(id.includes('fixture')) return 11;
    if(id.includes('news')) return 11.25;
    if(id.includes('settings')) return 11;
    return 10.5;
  }

  function readableLeaf(el,min){
    if(!el||el.closest(SKIP_CLOSEST)) return;
    const text=(el.textContent||'').trim();
    if(!text||!/[A-Za-z0-9£€%]/.test(text)) return;
    const cs=getComputedStyle(el), current=parseFloat(cs.fontSize||'0');
    if(!current||current>=min) return;

    let target=min;
    if(el.tagName==='SMALL') target=Math.max(target,11.5);
    if(el.matches('th,[class*="header"],[class*="label"]')) target=Math.max(target,10.75);
    if(el.matches('button,a')) target=Math.max(target,11);

    el.style.setProperty('font-size',target+'px','important');
    if(cs.lineHeight==='normal'||parseFloat(cs.lineHeight)<target*1.25){
      el.style.setProperty('line-height','1.35','important');
    }
    el.dataset.fmReadable='1';
  }

  function scan(root){
    if(!root||root.id==='teamPage') return;
    const min=pageMinimum(root);
    root.querySelectorAll('p,small,li,label,td,th,button,a,span,strong,b').forEach(el=>readableLeaf(el,min));
  }

  function scanActive(){
    addStyles();
    document.querySelectorAll('.page.active,[id$="Page"].active').forEach(scan);
  }

  let timer=null;
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(scanActive,80)};

  addStyles();
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',schedule,{once:true});
  else schedule();

  new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',()=>setTimeout(scanActive,120),true);
  window.addEventListener('fmcloudready',schedule);
})();
