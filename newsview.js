(()=>{
  const ID='fmNewsOverlay', CLEAR_KEY='fmFantasyCloudDatabaseCleared';
  const RX_ALL=/^(?:show|view)\s*all(?:\s+\d+)?$/i;
  const cleared=()=>{try{return localStorage.getItem(CLEAR_KEY)==='1'||sessionStorage.getItem(CLEAR_KEY)==='1'}catch(_){return false}};
  const markActive=()=>{try{localStorage.removeItem(CLEAR_KEY);sessionStorage.removeItem(CLEAR_KEY)}catch(_){}};

  function addStyles(){if(document.getElementById('fmNewsOverlayStyles'))return;const s=document.createElement('style');s.id='fmNewsOverlayStyles';s.textContent=`
    #${ID}{position:fixed;inset:0;z-index:99999;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(5,2,18,.82);backdrop-filter:blur(8px)}
    #${ID}.open{display:flex}#${ID} .fmNewsShell{width:min(980px,94vw);height:min(780px,88vh);display:grid;grid-template-rows:auto minmax(0,1fr);overflow:hidden;border:1px solid rgba(255,255,255,.12);border-radius:20px;background:linear-gradient(180deg,#160a33,#0b061d);box-shadow:0 28px 80px rgba(0,0,0,.5)}
    #${ID} .fmNewsHead{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px;border-bottom:1px solid rgba(255,255,255,.08)}#${ID} .fmNewsHead h2{margin:0;font-size:24px;line-height:1;font-weight:950;color:#fff}#${ID} .fmNewsClose{width:38px;height:38px;border:0;border-radius:11px;background:#2a174d;color:#fff;font-size:22px;cursor:pointer}
    #${ID} .fmNewsBody{min-height:0;overflow:auto;padding:16px 18px 22px}#${ID} .fmNewsBody>*{max-height:none!important;height:auto!important;overflow:visible!important}#${ID} .newsHidden{display:block!important}#${ID} [data-news-toggle]{display:none!important}.fmNewsClearedEmpty{padding:18px;color:#aaa2c8;font-size:12px}
    @media(max-width:700px){#${ID}{padding:0}#${ID} .fmNewsShell{width:100vw;height:100dvh;border-radius:0;border:0}#${ID} .fmNewsHead{padding:16px}#${ID} .fmNewsHead h2{font-size:20px}#${ID} .fmNewsBody{padding:12px}}
  `;document.head.appendChild(s)}

  function ensure(){addStyles();let o=document.getElementById(ID);if(o)return o;o=document.createElement('div');o.id=ID;o.innerHTML='<div class="fmNewsShell"><div class="fmNewsHead"><h2>News</h2><button class="fmNewsClose" type="button" aria-label="Close news">×</button></div><div class="fmNewsBody"></div></div>';document.body.appendChild(o);o.addEventListener('click',e=>{if(e.target===o||e.target.closest('.fmNewsClose'))close()});document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});return o}
  function close(){const o=document.getElementById(ID);if(o)o.classList.remove('open');document.documentElement.style.overflow=''}

  function sectionFromToggle(btn){
    const fullId=String(btn?.dataset?.newsToggle||'');
    if(fullId){
      const baseId=fullId.replace(/Full$/,'');
      const exact=document.getElementById(baseId);
      if(exact)return exact;
      const hidden=document.getElementById(fullId);
      if(hidden){
        const parent=hidden.parentElement?.closest?.('[id^="news"],.newsCard,.card,.panel,.box,section');
        if(parent)return parent;
      }
    }
    let el=btn;for(let i=0;i<8&&el;i++,el=el.parentElement){if(el.id?.startsWith('news')&&!/Full$/.test(el.id)||el.classList?.contains('newsCard'))return el}
    return null;
  }
  function titleFor(section){const h=section?.querySelector?.('h1,h2,h3,h4,.newsHead h3,.title,.cardTitle,.panelTitle,.sectionTitle');return (h?.textContent||'News').trim()||'News'}
  function openToggle(btn){
    const section=sectionFromToggle(btn);if(!section)return false;
    const o=ensure(),body=o.querySelector('.fmNewsBody');o.querySelector('.fmNewsHead h2').textContent=titleFor(section);
    if(cleared()){body.innerHTML='<div class="fmNewsClearedEmpty">No news available. Import an FM database to populate player news.</div>'}
    else{
      const clone=section.cloneNode(true);
      clone.querySelectorAll('.newsHidden').forEach(el=>{el.classList.remove('newsHidden');el.style.display=''});
      clone.querySelectorAll('[data-news-toggle]').forEach(el=>el.remove());
      clone.querySelectorAll('[data-news-search]').forEach(el=>el.value='');
      clone.querySelectorAll('[data-news-text]').forEach(el=>el.style.display='');
      body.replaceChildren(clone);
    }
    o.classList.add('open');document.documentElement.style.overflow='hidden';return true;
  }

  function clearVisibleNews(){
    if(!cleared())return;
    for(const id of ['newsTransfers','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']){
      const el=document.getElementById(id);if(!el)continue;
      const head=el.querySelector('.newsHead')?.cloneNode(true);
      el.innerHTML='';if(head)el.appendChild(head);
      const empty=document.createElement('div');empty.className='fmNewsClearedEmpty';empty.textContent='No news available.';el.appendChild(empty);
    }
    const stamp=document.getElementById('newsStamp');if(stamp)stamp.textContent='No FM database loaded.';
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-news-toggle]');if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();openToggle(b);
  },true);

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('button,a,[role="button"]');if(!b||b.hasAttribute('data-news-toggle'))return;
    const text=(b.textContent||'').trim().replace(/\s+/g,' ');if(!RX_ALL.test(text))return;
    e.preventDefault();e.stopImmediatePropagation();openToggle(b);
  },true);

  let busy=false;new MutationObserver(()=>{if(busy)return;busy=true;requestAnimationFrame(()=>{busy=false;clearVisibleNews()})}).observe(document.documentElement,{subtree:true,childList:true});
  setTimeout(clearVisibleNews,0);setTimeout(clearVisibleNews,350);
  window.FMNewsView={openToggle,close,clearVisibleNews,markActive};
})();
