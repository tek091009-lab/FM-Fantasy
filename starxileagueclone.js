(()=>{
  const styleBackup=new WeakMap();
  const norm=s=>String(s||'').trim().toLowerCase().replace(/\s+/g,' ');
  const rawHist=s=>Array.isArray(s?.pointsHistory)?s.pointsHistory:Array.isArray(s?.history)?s.history:[];
  const hist=s=>{const e=Number(s?.entryGameweek||1)||1;return rawHist(s).filter(x=>(Number(x?.gw)||0)>=e)};
  const totalPts=s=>hist(s).reduce((n,x)=>n+Number(x?.net??x?.gross??0),0);
  const gwPts=(s,gw)=>{const x=hist(s).find(r=>Number(r?.gw)===Number(gw));return x?Number(x?.net??x?.gross??0):0};

  function css(){if(document.getElementById('fmStarXiLeagueCloneCss'))return;const s=document.createElement('style');s.id='fmStarXiLeagueCloneCss';s.textContent=`
    #teamPage.fmStarXiLeagueMode{overflow-x:hidden!important}
    #teamPage.fmStarXiLeagueMode #fmLeagueManagerPanel,#teamPage.fmStarXiLeagueMode #fmLeagueManagerSidePanel,#teamPage.fmStarXiLeagueMode #fmLeagueManagerRightPanel{display:none!important}
    #teamPage.fmStarXiLeagueMode .fmLeaguePitchTarget{width:auto!important;max-width:none!important;margin-right:0!important}
    #teamPage.fmStarXiLeagueMode .teamGrid{display:grid!important;grid-template-columns:minmax(0,1fr) 270px!important;gap:12px!important;align-items:stretch!important;width:100%!important;max-width:none!important}
    #teamPage.fmStarXiLeagueMode .pitchCard,#teamPage.fmStarXiLeagueMode .pitchWrap{width:100%!important;max-width:none!important;min-width:0!important;margin:0!important}
    #teamPage.fmStarXiLeagueMode .rightPanel.fmStarXiLeagueHost,#teamPage.fmStarXiLeagueMode .chipsPanel.fmStarXiLeagueHost,#teamPage.fmStarXiLeagueMode .teamSide.fmStarXiLeagueHost,#teamPage.fmStarXiLeagueMode .fmStarXiLeagueHost{display:block!important;visibility:visible!important;opacity:1!important;pointer-events:none!important;min-width:0!important;width:100%!important;max-width:none!important;height:auto!important;overflow:hidden!important}
    #fmStarXiLeagueClone{display:block!important;visibility:visible!important;opacity:1!important;width:100%!important;max-width:none!important;height:100%!important;min-height:100%!important;box-sizing:border-box!important;position:relative!important;inset:auto!important;transform:none!important}
    #teamPage.fmStarXiLeagueMode #fmLeagueManagerSummary{box-sizing:border-box!important;overflow:hidden!important}
    @media(max-width:1050px){#teamPage.fmStarXiLeagueMode .teamGrid{grid-template-columns:1fr!important}#teamPage.fmStarXiLeagueMode .fmStarXiLeagueHost{margin-top:12px!important}}
  `;document.head.appendChild(s)}

  function viewedMember(){
    const banner=document.getElementById('viewBanner');if(!banner?.classList.contains('show')||typeof state==='undefined')return null;
    const leaf=[...banner.querySelectorAll('*')].find(x=>x.children.length===0&&/^Viewing\s+/i.test((x.textContent||'').trim()));
    const wanted=norm((leaf?.textContent||'').replace(/^Viewing\s+/i,''));
    const members=[];for(const l of(state.leagues||[]))for(const m of(l.members||[]))members.push(m);
    return members.find(m=>norm(m.team)===wanted)||members.find(m=>norm(m.name)===wanted)||null;
  }
  function currentGw(m){const page=document.getElementById('teamPage');if(page){for(const el of page.querySelectorAll('*')){if(el.children.length||el.offsetParent===null)continue;const t=(el.textContent||'').trim(),x=t.match(/^Gameweek\s*(\d+)$/i)||t.match(/^GW\s*(\d+)$/i);if(x)return Number(x[1])}}return Number(m?.currentGameweek||state?.currentGameweek||1)}

  function starSource(){
    const all=[...document.querySelectorAll('div,section,aside,article')].filter(el=>{const t=el.textContent||'';return t.includes('Star XI')&&t.includes('Combined points')&&t.includes('Squad value')&&t.includes('Total Gameweeks')&&t.includes('Average points')});
    all.sort((a,b)=>(a.textContent||'').length-(b.textContent||'').length);
    return all[0]||null;
  }
  function nativeHost(page){
    const chipLeaf=[...page.querySelectorAll('*')].find(x=>x.children.length===0&&/Gameweek Chips/i.test((x.textContent||'').trim()));
    const byLeaf=chipLeaf?.closest('.rightPanel,.chipsPanel,.teamSide');if(byLeaf)return byLeaf;
    const direct=[...page.querySelectorAll('.rightPanel,.chipsPanel,.teamSide')];if(direct.length)return direct[0];
    const grid=page.querySelector('.teamGrid');if(!grid)return null;return [...grid.children].find(x=>x!==page.querySelector('.pitchCard')&&x.textContent?.match(/chip|wildcard|bench boost/i))||null;
  }
  function leaves(root){return [...root.querySelectorAll('*')].filter(x=>x.children.length===0&&String(x.textContent||'').trim())}
  function setLeaf(root,oldText,newText){const n=leaves(root).find(x=>norm(x.textContent)===norm(oldText));if(n)n.textContent=newText;return n}
  function setRow(root,oldLabel,newLabel,newValue){const label=setLeaf(root,oldLabel,newLabel);if(!label)return;let row=label.parentElement;for(let i=0;i<3&&row&&row!==root;i++,row=row.parentElement){const ls=leaves(row).filter(x=>x!==label);if(ls.length){ls[ls.length-1].textContent=String(newValue);return}}}
  function stripIds(root){if(root.id)root.removeAttribute('id');root.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'))}
  function copyVisual(src,dst){const props=['display','flexDirection','flexWrap','alignItems','justifyContent','gap','background','backgroundColor','color','border','borderTop','borderRight','borderBottom','borderLeft','borderRadius','boxShadow','padding','paddingTop','paddingRight','paddingBottom','paddingLeft','margin','marginTop','marginRight','marginBottom','marginLeft','font','fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','textAlign','textTransform','overflow'];const ss=getComputedStyle(src);for(const p of props){try{dst.style[p]=ss[p]}catch{}}const sc=[...src.children],dc=[...dst.children];for(let i=0;i<Math.min(sc.length,dc.length);i++)copyVisual(sc[i],dc[i])}

  function hideOriginalChildren(host,clone){for(const ch of [...host.children]){if(ch===clone)continue;if(!styleBackup.has(ch))styleBackup.set(ch,ch.getAttribute('style'));ch.style.setProperty('display','none','important')}}
  function restoreHost(host){if(!host)return;for(const ch of [...host.children]){if(ch.id==='fmStarXiLeagueClone'){ch.remove();continue}if(styleBackup.has(ch)){const old=styleBackup.get(ch);if(old===null)ch.removeAttribute('style');else ch.setAttribute('style',old);styleBackup.delete(ch)}}host.classList.remove('fmStarXiLeagueHost')}

  function cleanup(){const page=document.getElementById('teamPage');if(!page)return;page.classList.remove('fmStarXiLeagueMode','fmLeagueHardLayout');page.querySelectorAll('.fmLeagueViewGrid,.fmLeagueFallbackGrid,.fmLeaguePitchTarget,.fmLeagueOverviewHost').forEach(x=>x.classList.remove('fmLeagueViewGrid','fmLeagueFallbackGrid','fmLeaguePitchTarget','fmLeagueOverviewHost'));document.querySelectorAll('#fmLeagueManagerPanel,#fmLeagueManagerSidePanel,#fmLeagueManagerRightPanel').forEach(x=>x.remove());const host=page.querySelector('.fmStarXiLeagueHost');restoreHost(host);const sum=document.getElementById('fmLeagueManagerSummary');if(sum){sum.style.width='';sum.style.maxWidth=''}}

  function render(){
    css();const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');if(!page||!banner?.classList.contains('show')){cleanup();return}
    const m=viewedMember(),src=starSource(),host=nativeHost(page),grid=page.querySelector('.teamGrid');if(!m||!src||!host||!grid)return;
    page.classList.add('fmStarXiLeagueMode');page.classList.remove('fmLeagueHardLayout');page.querySelectorAll('.fmLeagueViewGrid,.fmLeagueFallbackGrid,.fmLeaguePitchTarget,.fmLeagueOverviewHost').forEach(x=>x.classList.remove('fmLeagueViewGrid','fmLeagueFallbackGrid','fmLeaguePitchTarget','fmLeagueOverviewHost'));document.querySelectorAll('#fmLeagueManagerPanel,#fmLeagueManagerSidePanel,#fmLeagueManagerRightPanel').forEach(x=>x.remove());
    host.classList.add('fmStarXiLeagueHost');let clone=host.querySelector('#fmStarXiLeagueClone');if(!clone){clone=src.cloneNode(true);stripIds(clone);clone.id='fmStarXiLeagueClone';copyVisual(src,clone);host.appendChild(clone)}hideOriginalChildren(host,clone);
    const gw=currentGw(m),gp=gwPts(m,gw),total=totalPts(m),entry=Number(m.entryGameweek||1);
    const starTitle=leaves(clone).find(x=>norm(x.textContent)==='star xi');if(starTitle)starTitle.textContent=m.team||'My Team';
    const desc=leaves(clone).find(x=>/highest-scoring legal xi|updated automatically/i.test(x.textContent||''));if(desc)desc.textContent=`${m.name||'Manager'} · read-only league team view.`;
    setLeaf(clone,'Overview','Manager Overview');setRow(clone,'Combined points','Gameweek Points',`${gp}`);setRow(clone,'Squad value','Total Points',`${total}`);setRow(clone,'Total Gameweeks','Gameweek',`GW ${gw}`);setRow(clone,'Average points','Entry Gameweek',`GW ${entry}`);
    requestAnimationFrame(()=>{const sum=document.getElementById('fmLeagueManagerSummary');if(sum&&innerWidth>1050){const sr=sum.getBoundingClientRect(),hr=host.getBoundingClientRect(),w=Math.max(320,hr.left-sr.left-12);sum.style.width=`${w}px`;sum.style.maxWidth=`${w}px`}})
  }
  let t;const refresh=()=>{clearTimeout(t);t=setTimeout(render,80)};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();window.addEventListener('fmcloudready',refresh);window.addEventListener('resize',refresh);document.addEventListener('click',()=>setTimeout(refresh,120),true);new MutationObserver(refresh).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
})();
