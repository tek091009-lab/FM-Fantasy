(function(){
  'use strict';
  const css=`
    #fmMobileBar,#fmMobileBackdrop{display:none}
    @media(max-width:900px){
      :root{--fm-mobile-bar:58px}
      html,body{width:100%;max-width:100%;overflow-x:hidden}
      body{min-width:0!important}
      .app{display:block!important;width:100%!important;min-width:0!important}
      #fmMobileBar{position:fixed;inset:0 0 auto 0;height:var(--fm-mobile-bar);z-index:10020;display:flex;align-items:center;gap:11px;padding:8px 12px;box-sizing:border-box;background:linear-gradient(110deg,#170728 0%,#4f0b68 55%,#a50a79 100%);border-bottom:1px solid rgba(255,255,255,.14);box-shadow:0 8px 24px rgba(0,0,0,.28)}
      #fmMobileMenu{width:40px;height:40px;border:1px solid rgba(255,255,255,.2);border-radius:10px;background:#25123f;color:#fff;font-size:22px;line-height:1;display:grid;place-items:center;flex:0 0 auto}
      #fmMobileBrand{font-weight:900;font-size:17px;white-space:nowrap}.fmMobileBrandAccent{color:#ff3b9d}
      #fmMobileTitle{margin-left:auto;max-width:45vw;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:800;color:#eaddf5;text-align:right}
      #fmMobileBackdrop{position:fixed;inset:0;z-index:10030;background:rgba(3,0,15,.68);backdrop-filter:blur(2px)}
      body.fmMobileOpen #fmMobileBackdrop{display:block}
      .sidebar{position:fixed!important;inset:0 auto 0 0!important;z-index:10040!important;display:flex!important;flex-direction:column!important;width:min(86vw,320px)!important;height:100dvh!important;min-height:0!important;padding:12px 10px!important;overflow-y:auto!important;overflow-x:hidden!important;transform:translateX(-105%);transition:transform .22s ease;background:linear-gradient(180deg,#150622,#090318 78%)!important;box-shadow:18px 0 40px rgba(0,0,0,.45)}
      body.fmMobileOpen .sidebar{transform:translateX(0)}
      body.fmMobileOpen{overflow:hidden}
      .sidebar .logo{display:flex!important;min-height:48px!important;margin:0 4px 5px!important;padding:2px 5px 8px!important}
      .sidebar .snav{display:flex!important;flex-direction:column!important;gap:2px!important;width:100%!important}
      .sidebar .snav button{display:flex!important;width:100%!important;min-height:42px!important;padding:0 12px!important;font-size:13px!important;text-align:left!important}
      .sidebar .snav button.subnav{min-height:34px!important;padding-left:31px!important;font-size:11px!important}
      .sidebar .syncbox{display:block!important;margin:10px 4px 8px!important;padding:10px!important;flex:0 0 auto!important}
      .sidebar .syncBtn{min-height:32px!important;font-size:9px!important}.sidebar .syncStatus,.sidebar .syncLeague{font-size:8px!important}
      .main{width:100%!important;max-width:100%!important;min-width:0!important;margin:0!important;padding:calc(var(--fm-mobile-bar) + 8px) 8px 14px!important;box-sizing:border-box!important;overflow:visible!important}
      .page{width:100%!important;max-width:100%!important;min-width:0!important;overflow:visible!important}
      .top{min-height:78px!important;height:auto!important;margin:0 0 8px!important;padding:13px 14px!important;border-radius:13px!important;align-items:flex-start!important}
      .top h1{font-size:24px!important;line-height:1.05!important}.top p{font-size:10px!important;margin-top:5px!important}
      .top .profile,.top .account,.top .managerPill{max-width:46%!important;transform:scale(.86);transform-origin:top right}
      .card,.summary,.tableCard{max-width:100%!important;box-sizing:border-box!important}
      .summary{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;height:auto!important;min-height:0!important;overflow:hidden!important}
      .summary .sum{min-width:0!important;min-height:72px!important;padding:10px 8px!important;text-align:center!important;border-bottom:1px solid rgba(189,126,235,.17)}
      .summary .sum:nth-child(odd){border-left:0!important}.summary .sum:nth-child(even){border-right:0!important}
      .summary small{font-size:9px!important}.summary b{font-size:16px!important;overflow-wrap:anywhere}
      .split,.teamGrid,.teamWorkspace,.starWorkspace,.fixtureWorkspace,.leagueBody,.statsBottom{display:grid!important;grid-template-columns:minmax(0,1fr)!important;grid-template-areas:none!important;gap:9px!important;width:100%!important;min-width:0!important}
      .teamGrid>* ,.starWorkspace>* ,.fixtureWorkspace>* ,.leagueBody>*{grid-area:auto!important;width:100%!important;min-width:0!important;max-width:100%!important;margin-left:0!important;margin-right:0!important}
      .pitchCard,.starPitchCard{height:auto!important;min-height:0!important;overflow:hidden!important;border-radius:11px!important}
      .pitchCard>.pitchScroll,.starPitchCard>.pitchScroll{display:block!important;position:relative!important;width:100%!important;max-width:100%!important;height:auto;min-height:0!important;overflow:hidden!important}
      .pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#txPitch{width:760px!important;min-width:760px!important;max-width:none!important;height:610px!important;min-height:610px!important;margin:0!important;transform:scale(var(--fm-mobile-pitch-scale,1));transform-origin:top left!important}
      .pitchTopControls,.gwNav,.gameweekNav{right:10px!important;left:auto!important;top:8px!important;transform:none!important;z-index:20!important}
      .bench{width:calc(100% - 20px)!important;left:10px!important;right:10px!important;min-width:720px!important}
      .teamHead,.starFooter{min-height:44px!important;height:auto!important;padding:7px 9px!important;margin:0!important}
      #teamSide,.teamSide,.starSide{min-height:260px!important;height:auto!important;margin:0!important}
      #viewBanner,#swapBanner{width:100%!important;margin:0 0 8px!important;box-sizing:border-box!important}
      #transfersPage .split{display:flex!important;flex-direction:column!important}
      #transfersPage .pitchCard{order:1}#transfersPage .market,#transfersPage .playerSelection,#transfersPage .right{order:2;width:100%!important;max-width:none!important}
      #transfersPage .summary{grid-template-columns:repeat(2,minmax(0,1fr))!important}
      #transfersPage .summary .sum:last-child:nth-child(odd){grid-column:1/-1!important}
      #transfersPage .prow{min-width:700px!important}.marketRows,.playerRows,.marketTable{overflow-x:auto!important;-webkit-overflow-scrolling:touch}
      .newsGrid{display:grid!important;grid-template-columns:1fr!important;gap:9px!important}.newsGrid>*{grid-column:auto!important;min-height:170px!important}.newsAbout{margin-top:9px!important}
      .fixtureSummary,.leagueStats,.statsHero{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
      .fixtureRail{display:grid!important;grid-template-columns:1fr!important;gap:9px!important}.fixtureMain{min-width:0!important}.fixtureFilters,.fixtureCalendar{width:100%!important}
      .fixtureRows,.fixtureList{overflow-x:auto!important;-webkit-overflow-scrolling:touch}.fixtureRow{min-width:680px!important}
      .fixtureSummary .fixtureSummaryCard{min-width:0!important;padding:10px!important}
      .tableTopbar{display:flex!important;align-items:flex-start!important;gap:8px!important;flex-wrap:wrap!important}.tableTabs{display:flex!important;width:100%!important;overflow-x:auto!important;white-space:nowrap!important}.leagueTableScroll{width:100%!important;max-height:66dvh!important;overflow:auto!important;-webkit-overflow-scrolling:touch}.leagueTable{min-width:900px!important}
      .leagueStats{grid-template-columns:repeat(2,minmax(0,1fr))!important}.leagueMine,.leagueRail{min-height:0!important}.leagueActions,.leagueCreateJoin{display:grid!important;grid-template-columns:1fr!important}.leagueFeatured{min-height:280px!important}
      .statsHero,.statsLeaderGrid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}.statsLeaderGrid>*{min-width:0!important}.statsBottom{grid-template-columns:1fr!important}.seasonInsightGrid{display:grid!important;grid-template-columns:1fr!important}.statsWorkspace{height:auto!important;min-height:0!important;overflow:visible!important}
      .rulesConceptGrid{display:grid!important;grid-template-columns:1fr!important;height:auto!important;min-height:0!important;overflow:visible!important}.ruleConceptCard{min-height:0!important;height:auto!important}.ruleConceptCard p,.ruleConceptCard li,.ruleMini{font-size:12px!important;line-height:1.45!important}.ruleMiniGrid,.ruleScoreGrid{grid-template-columns:1fr!important}
      .modal,.playerDrawer,.drawer,.compareModal{max-width:100vw!important}.playerDrawer,.drawer{width:100vw!important}.modalBox,.compareBox{width:calc(100vw - 16px)!important;max-width:none!important;max-height:calc(100dvh - 16px)!important;margin:8px!important;overflow:auto!important}.modalActions{display:grid!important;grid-template-columns:1fr!important}
      button,input,select{touch-action:manipulation}.btn,.pinkBtn,.primary{min-height:42px}
    }
    @media(max-width:560px){
      .main{padding-left:6px!important;padding-right:6px!important}.top{min-height:70px!important;padding:11px!important}.top h1{font-size:21px!important}.top p{max-width:58%;font-size:9px!important}
      .top .profile,.top .account,.top .managerPill{max-width:43%!important;transform:scale(.76)}
      .summary .sum{min-height:66px!important;padding:8px 5px!important}.summary b{font-size:14px!important}
      .fixtureSummary,.leagueStats,.statsHero,.statsLeaderGrid{grid-template-columns:1fr!important}
      .statsHero{grid-template-columns:repeat(2,minmax(0,1fr))!important}.statsHero>*{min-height:96px!important}
      .pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#txPitch{width:720px!important;min-width:720px!important;height:580px!important;min-height:580px!important}
      .bench{min-width:680px!important}
      .leagueTableScroll{max-height:70dvh!important}
    }
  `;
  function title(){
    const active=document.querySelector('.page.active');
    return active?.querySelector('.top h1')?.textContent?.trim()||active?.querySelector('h1,h2')?.textContent?.trim()||'FM Fantasy';
  }
  function close(){document.body.classList.remove('fmMobileOpen');document.getElementById('fmMobileMenu')?.setAttribute('aria-expanded','false')}
  function updateTitle(){const el=document.getElementById('fmMobileTitle');if(el)el.textContent=title()}
  let fitTimer=0;
  function fitPitches(){
    if(innerWidth>900)return;
    const targets=[...document.querySelectorAll('.pitchCard>.pitchScroll>.pitch,.starPitchCard>.pitchScroll>.pitch,#txPitch')];
    for(const pitch of targets){
      const wrap=pitch.closest('.pitchScroll')||pitch.parentElement;if(!wrap)continue;
      const naturalWidth=parseFloat(getComputedStyle(pitch).width)||760,naturalHeight=parseFloat(getComputedStyle(pitch).height)||610;
      const available=Math.max(280,wrap.clientWidth||document.documentElement.clientWidth-28),scale=Math.min(1,available/naturalWidth);
      pitch.style.setProperty('--fm-mobile-pitch-scale',String(scale));
      wrap.style.setProperty('height',`${Math.ceil(naturalHeight*scale)}px`,'important');
      wrap.style.setProperty('min-height','0px','important');
    }
  }
  function queueFit(){clearTimeout(fitTimer);fitTimer=setTimeout(fitPitches,40)}
  function boot(){
    if(document.getElementById('fmMobileStyles'))return;
    const style=document.createElement('style');style.id='fmMobileStyles';style.textContent=css;document.head.appendChild(style);
    const bar=document.createElement('header');bar.id='fmMobileBar';bar.innerHTML='<button id="fmMobileMenu" type="button" aria-label="Open navigation" aria-expanded="false">☰</button><div id="fmMobileBrand">FM <span class="fmMobileBrandAccent">Fantasy</span></div><div id="fmMobileTitle"></div>';
    const shade=document.createElement('div');shade.id='fmMobileBackdrop';shade.setAttribute('aria-hidden','true');
    document.body.append(bar,shade);
    bar.querySelector('#fmMobileMenu').addEventListener('click',()=>{const open=document.body.classList.toggle('fmMobileOpen');bar.querySelector('#fmMobileMenu').setAttribute('aria-expanded',String(open))});
    shade.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
    document.querySelector('.sidebar')?.addEventListener('click',e=>{if(e.target.closest('button')){setTimeout(()=>{close();updateTitle()},0)}});
    new MutationObserver(()=>{updateTitle();queueFit()}).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
    new MutationObserver(queueFit).observe(document.body,{subtree:true,childList:true});
    addEventListener('resize',queueFit,{passive:true});addEventListener('orientationchange',queueFit,{passive:true});
    updateTitle();queueFit();setTimeout(fitPitches,250);setTimeout(fitPitches,900);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
