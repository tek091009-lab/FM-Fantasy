(()=>{
  const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rawHist=s=>Array.isArray(s?.pointsHistory)?s.pointsHistory:Array.isArray(s?.history)?s.history:[];
  const hist=s=>{const entry=Number(s?.entryGameweek||1)||1;return rawHist(s).filter(x=>(Number(x?.gw)||0)>=entry)};
  const gwPts=(s,gw)=>{const x=hist(s).find(r=>Number(r?.gw)===Number(gw));return x?Number(x?.net??x?.gross??0):0};
  const totalPts=s=>{const h=hist(s);return h.length?h.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0):Number(s?.points??s?.totalPoints??0)};

  function addCss(){
    if(document.getElementById('fmLeagueStarExactCss'))return;
    const st=document.createElement('style');st.id='fmLeagueStarExactCss';st.textContent=`
      /* Exact league team layout, based directly on the production Star XI grid/sidebar. */
      #teamPage.active.fmLeagueStarExact{overflow-y:auto!important;overflow-x:hidden!important}
      #teamPage.fmLeagueStarExact #fmLeagueManagerSummary{display:none!important}
      #teamPage.fmLeagueStarExact #fmLeagueManagerPanel,
      #teamPage.fmLeagueStarExact #fmLeagueManagerSidePanel,
      #teamPage.fmLeagueStarExact #fmLeagueManagerRightPanel,
      #teamPage.fmLeagueStarExact #fmStarXiLeagueClone{display:none!important}

      #teamPage.leagueReadOnly.fmLeagueStarExact .teamGrid.teamWorkspace,
      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) clamp(285px,19%,315px)!important;
        grid-template-rows:82px minmax(590px,1fr) 58px!important;
        grid-template-areas:"leagueSummary leagueSide" "leaguePitch leagueSide" "leagueFooter leagueSide"!important;
        gap:9px 0!important;
        width:100%!important;
        max-width:none!important;
        height:auto!important;
        min-height:748px!important;
        margin:0!important;
        align-items:stretch!important;
        justify-content:stretch!important;
      }

      #teamPage.leagueReadOnly.fmLeagueStarExact .teamGrid.teamWorkspace>.summary,
      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.summary{
        grid-area:leagueSummary!important;
        display:grid!important;
        grid-template-columns:1fr!important;
        width:calc(100% - 28px)!important;
        max-width:none!important;
        height:82px!important;
        min-height:0!important;
        margin:0 14px!important;
        padding:0!important;
        gap:0!important;
        overflow:hidden!important;
        border:1px solid rgba(189,126,235,.28)!important;
        border-radius:8px!important;
        background:linear-gradient(135deg,#2a154b 0%,#1b0d38 55%,#241044 100%)!important;
        box-shadow:0 12px 28px rgba(4,0,18,.25)!important;
        color:#fff!important;
      }
      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.summary>:not(#fmLeagueInlineSummary){display:none!important}
      #fmLeagueInlineSummary{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;width:100%!important;height:100%!important;grid-column:1/-1!important}
      .fmLeagueSumCell{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-width:0;padding:10px 14px;border-right:1px solid rgba(220,193,244,.14);background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.012))}
      .fmLeagueSumCell:last-child{border-right:0}.fmLeagueSumCell small{margin:0 0 6px!important;color:#bea9d4!important;font-size:10px!important;font-weight:700!important}.fmLeagueSumCell b{color:#fff!important;font-size:19px!important;font-weight:800!important;line-height:1.05!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}.fmLeagueSumCell b.pink,.fmLeagueSumCell em{color:#ff4e9d!important;font-style:normal}.fmLeagueSumCell em{font-size:12px;margin-left:5px}

      #teamPage.leagueReadOnly.fmLeagueStarExact .teamGrid.teamWorkspace>.pitchCard,
      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.pitchCard{
        grid-area:leaguePitch!important;
        display:flex!important;
        flex-direction:column!important;
        width:100%!important;
        max-width:none!important;
        height:100%!important;
        min-height:0!important;
        margin:0!important;
        padding:0 14px 8px!important;
        overflow:hidden!important;
        border:0!important;
        border-radius:0!important;
        background:#100725!important;
        box-shadow:none!important;
      }
      #teamPage.fmLeagueStarExact .pitchCard>.pitchScroll{flex:1 1 auto!important;min-height:0!important;width:100%!important;overflow:hidden!important;display:flex!important;align-items:stretch!important;justify-content:center!important}
      #teamPage.fmLeagueStarExact .pitchCard>.pitchScroll>.pitch{width:100%!important;max-width:none!important;height:100%!important;min-height:0!important;margin:0!important}

      #teamPage.leagueReadOnly.fmLeagueStarExact #teamSide.fmLeagueStarSide,
      #teamPage.fmLeagueStarExact #teamSide.fmLeagueStarSide{
        grid-area:leagueSide!important;
        display:flex!important;
        visibility:visible!important;
        opacity:1!important;
        pointer-events:auto!important;
        flex-direction:column!important;
        min-width:0!important;
        width:auto!important;
        max-width:none!important;
        min-height:0!important;
        height:auto!important;
        margin:0!important;
        padding:0 14px 14px!important;
        position:relative!important;
        top:auto!important;
        border:1px solid rgba(197,114,224,.34)!important;
        border-bottom:0!important;
        border-radius:5px 5px 0 0!important;
        color:#f8f2ff!important;
        background:linear-gradient(180deg,#94164f 0,#a91d67 215px,#1b0d38 215px,#170b31 100%)!important;
        box-shadow:0 16px 38px rgba(0,0,0,.22)!important;
        overflow:hidden!important;
      }
      #teamPage #teamSide.fmLeagueStarSide>:not(#fmLeagueManagerStarPanel){display:none!important}
      #fmLeagueManagerStarPanel{display:flex!important;flex-direction:column!important;flex:1 1 auto!important;min-height:0!important;width:100%!important}
      #fmLeagueManagerStarPanel .starSideHero{margin:0 -14px;padding:25px 20px 22px;min-height:215px;box-sizing:border-box;background:radial-gradient(circle at 100% 0,rgba(255,255,255,.14),transparent 38%),linear-gradient(135deg,#80113f,#b51b68)}
      #fmLeagueManagerStarPanel .starSideIcon{display:grid;place-items:center;width:42px;height:42px;margin-bottom:14px;border:1px solid rgba(255,255,255,.25);border-radius:50%;background:rgba(255,255,255,.1);font-size:21px}
      #fmLeagueManagerStarPanel .starSideHero h3{margin:0 0 7px;font-size:24px;line-height:1;font-weight:800;color:#fff}
      #fmLeagueManagerStarPanel .starSideHero p{margin:0;color:#f7ddeb;font-size:10px;line-height:1.55}
      #fmLeagueManagerStarPanel .starOverview{margin-top:14px;border:1px solid rgba(213,183,238,.16);border-radius:5px;overflow:hidden;background:rgba(39,20,70,.72)}
      #fmLeagueManagerStarPanel .starOverview h4{margin:0;padding:13px 14px;border-bottom:1px solid rgba(213,183,238,.13);font-size:13px;color:#fff}
      #fmLeagueManagerStarPanel .starMetric{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid rgba(213,183,238,.11);color:#c7b5d9;font-size:10px}
      #fmLeagueManagerStarPanel .starMetric:last-child{border-bottom:0}#fmLeagueManagerStarPanel .starMetric b{color:#fff;font-size:13px;text-align:right}#fmLeagueManagerStarPanel .starMetric.points b{color:#ff5aa6}
      #fmLeagueManagerStarPanel .starSideNote{margin-top:auto;padding:13px;border:1px solid rgba(213,183,238,.16);border-radius:5px;background:rgba(31,15,58,.88);color:#c7b5d9;font-size:9px;line-height:1.55}

      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.teamHead{grid-area:leagueFooter!important;display:flex!important;width:calc(100% - 28px)!important;height:58px!important;min-height:0!important;margin:0 14px!important;padding:8px 12px!important;box-sizing:border-box!important;overflow:hidden!important;border:1px solid rgba(189,126,235,.22)!important;border-radius:5px!important;background:linear-gradient(180deg,#211540,#160d33)!important;box-shadow:0 9px 22px rgba(0,0,0,.17)!important}
      #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.teamHead #teamActions{display:none!important}

      @media(max-width:1180px){
        #teamPage.leagueReadOnly.fmLeagueStarExact .teamGrid.teamWorkspace,#teamPage.fmLeagueStarExact .teamGrid.teamWorkspace{grid-template-columns:1fr!important;grid-template-rows:auto auto auto auto!important;grid-template-areas:"leagueSummary" "leaguePitch" "leagueSide" "leagueFooter"!important;min-height:0!important}
        #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.summary{width:100%!important;margin:0 0 9px!important}
        #teamPage.fmLeagueStarExact #teamSide.fmLeagueStarSide{min-height:480px!important;margin-top:9px!important}
        #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.teamHead{width:100%!important;margin:9px 0 0!important}
      }
      @media(min-width:1181px) and (max-height:850px){
        #teamPage.leagueReadOnly.fmLeagueStarExact .teamGrid.teamWorkspace,#teamPage.fmLeagueStarExact .teamGrid.teamWorkspace{grid-template-rows:76px minmax(500px,1fr) 48px!important;min-height:624px!important}
        #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace>.summary{height:76px!important}
        #fmLeagueManagerStarPanel .starSideHero{min-height:175px;padding:18px 17px}
      }
    `;document.head.appendChild(st);
  }

  function memberBeingViewed(){
    const banner=document.getElementById('viewBanner');if(!banner?.classList.contains('show')||typeof state==='undefined')return null;
    const label=document.getElementById('viewTeamName');
    const wanted=norm(String(label?.textContent||'').replace(/^Viewing\s+/i,''));
    if(!wanted)return null;
    const members=[];for(const l of(state.leagues||[]))for(const m of(l.members||[]))members.push(m);
    return members.find(m=>norm(m.team)===wanted)||members.find(m=>norm(m.name)===wanted)||null;
  }
  function currentGw(m){
    const label=document.getElementById('teamGWLabel');const mm=String(label?.textContent||'').match(/(?:Gameweek|GW)\s*(\d+)/i);if(mm)return Number(mm[1]);
    return Number(m?.currentGameweek||state?.currentGameweek||1);
  }

  function cleanup(){
    const page=document.getElementById('teamPage');if(!page)return;
    page.classList.remove('fmLeagueStarExact');
    const side=document.getElementById('teamSide');side?.classList.remove('fmLeagueStarSide');
    document.getElementById('fmLeagueManagerStarPanel')?.remove();
    document.getElementById('fmLeagueInlineSummary')?.remove();
  }

  function render(){
    addCss();
    const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner'),grid=page?.querySelector('.teamGrid.teamWorkspace'),side=document.getElementById('teamSide'),summary=grid?.querySelector(':scope > .summary');
    if(!page||!banner?.classList.contains('show')||!grid||!side||!summary){cleanup();return}
    const m=memberBeingViewed();if(!m){cleanup();return}
    page.classList.add('leagueReadOnly','fmLeagueStarExact');
    grid.classList.remove('fmLeagueViewGrid','fmLeagueFallbackGrid','fmLeaguePitchTarget');
    side.classList.remove('fmLeagueOverviewHost','fmStarXiLeagueHost');side.classList.add('fmLeagueStarSide');
    document.querySelectorAll('#fmLeagueManagerPanel,#fmLeagueManagerSidePanel,#fmLeagueManagerRightPanel,#fmStarXiLeagueClone').forEach(x=>x.remove());
    document.getElementById('fmLeagueManagerSummary')?.remove();

    const gw=currentGw(m),gp=gwPts(m,gw),total=totalPts(m);
    let sum=document.getElementById('fmLeagueInlineSummary');if(!sum){sum=document.createElement('div');sum.id='fmLeagueInlineSummary';summary.appendChild(sum)}
    sum.innerHTML=`<div class="fmLeagueSumCell"><small>Team Name</small><b>${esc(m.team||'My Team')}</b></div><div class="fmLeagueSumCell"><small>Manager</small><b>${esc(m.name||'Manager')}</b></div><div class="fmLeagueSumCell"><small>Gameweek</small><b>GW ${gw} <em>${gp} pts</em></b></div><div class="fmLeagueSumCell"><small>Total Points</small><b class="pink">${total}</b></div>`;

    let panel=document.getElementById('fmLeagueManagerStarPanel');if(!panel){panel=document.createElement('div');panel.id='fmLeagueManagerStarPanel';side.appendChild(panel)}
    panel.innerHTML=`<div class="starSideHero"><div class="starSideIcon">★</div><h3>${esc(m.team||'My Team')}</h3><p>${esc(m.name||'Manager')} · read-only mini-league team view.</p></div><div class="starOverview"><h4>Manager Overview</h4><div class="starMetric"><span>Team Name</span><b>${esc(m.team||'My Team')}</b></div><div class="starMetric"><span>Manager</span><b>${esc(m.name||'Manager')}</b></div><div class="starMetric"><span>Gameweek</span><b>GW ${gw}</b></div><div class="starMetric points"><span>Gameweek Points</span><b>${gp}</b></div><div class="starMetric points"><span>Total Points</span><b>${total}</b></div></div><div class="starSideNote">Use the Gameweek arrows above the pitch to browse this manager's available Gameweeks. Their team remains read-only.</div>`;
  }

  let timer;const refresh=()=>{clearTimeout(timer);timer=setTimeout(render,70)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
  window.addEventListener('fmcloudready',refresh);window.addEventListener('resize',refresh);
  document.addEventListener('click',()=>setTimeout(refresh,100),true);
  new MutationObserver(refresh).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
})();
