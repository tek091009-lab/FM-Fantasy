(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const hist=s=>{const h=Array.isArray(s?.pointsHistory)?s.pointsHistory:Array.isArray(s?.history)?s.history:[],entry=Number(s?.entryGameweek||1)||1;return h.filter(x=>(Number(x?.gw)||0)>=entry)};
  const gwPts=(s,gw)=>{const x=hist(s).find(r=>Number(r?.gw)===Number(gw));return x?Number(x?.net??x?.gross??0):0};
  const totalPts=s=>{const h=hist(s);return h.length?h.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0):Number(s?.points??s?.totalPoints??0)};

  function addStyles(){
    if(document.getElementById('fmLeagueViewPanelStyles'))return;
    const st=document.createElement('style');st.id='fmLeagueViewPanelStyles';st.textContent=`
      /* Loaded last on purpose: restore the REAL My Team right column for league viewing. */
      #teamPage.leagueReadOnly .rightPanel.fmLeagueOverviewHost,
      #teamPage.leagueReadOnly .chipsPanel.fmLeagueOverviewHost,
      #teamPage.leagueReadOnly .teamSide.fmLeagueOverviewHost,
      #teamPage .fmLeagueOverviewHost{
        display:block!important;visibility:visible!important;opacity:1!important;pointer-events:auto!important;
        align-self:stretch!important;min-width:245px!important;height:auto!important;overflow:visible!important;
      }
      #teamPage .fmLeagueOverviewHost > :not(#fmLeagueManagerSidePanel){display:none!important}
      #fmLeagueManagerSidePanel{display:flex!important;flex-direction:column!important;width:100%!important;height:100%!important;min-height:560px!important;border:1px solid rgba(255,255,255,.14)!important;border-radius:10px!important;overflow:hidden!important;background:linear-gradient(180deg,#1b1239,#110b28)!important;box-shadow:0 12px 32px rgba(0,0,0,.24)!important;color:#fff!important;box-sizing:border-box!important}
      .fmLspHero{padding:22px 18px 20px;min-height:165px;background:linear-gradient(155deg,#c51a69,#a71156 58%,#7d103f);display:flex;flex-direction:column;justify-content:center;box-sizing:border-box}.fmLspIcon{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.08);font-size:22px;margin-bottom:15px}.fmLspHero h3{margin:0 0 7px;font-size:23px;line-height:1.05;font-weight:1000;color:#fff}.fmLspHero p{margin:0;font-size:11.5px;line-height:1.45;color:rgba(255,255,255,.92);font-weight:700}.fmLspBody{padding:12px;display:flex;flex-direction:column;flex:1}.fmLspBox{border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(35,22,73,.78);overflow:hidden}.fmLspTitle{padding:13px 14px;font-size:13px;font-weight:950;border-bottom:1px solid rgba(255,255,255,.11)}.fmLspRow{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.09);font-size:11.5px;color:#d0c7df}.fmLspRow:last-child{border-bottom:0}.fmLspRow b{color:#fff;font-size:12px;text-align:right;max-width:58%;overflow:hidden;text-overflow:ellipsis}.fmLspRow b.pink{color:#ff4ba8}.fmLspHint{margin-top:auto;padding:12px 13px;border:1px solid rgba(255,255,255,.11);border-radius:8px;background:rgba(17,10,43,.65);font-size:10.5px;line-height:1.45;color:#bfb4d2}
      /* Fallback only if this build has no native right panel. */
      #teamPage.leagueReadOnly .fmLeagueFallbackGrid{display:grid!important;grid-template-columns:minmax(0,1fr) 270px!important;gap:14px!important;align-items:stretch!important}
      #teamPage.leagueReadOnly .fmLeagueFallbackGrid>#fmLeagueManagerSidePanel{grid-column:2!important}
      @media(max-width:1050px){#teamPage.leagueReadOnly .fmLeagueFallbackGrid{grid-template-columns:1fr!important}#teamPage.leagueReadOnly .fmLeagueFallbackGrid>#fmLeagueManagerSidePanel{grid-column:1!important}.fmLeagueOverviewHost{min-width:0!important}}
    `;document.head.appendChild(st);
  }

  function memberBeingViewed(){
    const banner=document.getElementById('viewBanner');
    if(!banner?.classList.contains('show')||typeof state==='undefined')return null;
    const text=(banner.textContent||'').toLowerCase();
    const members=[];
    for(const l of(state.leagues||[]))for(const m of(l.members||[]))if(!m.own)members.push(m);
    members.sort((a,b)=>Math.max(String(b.team||'').length,String(b.name||'').length)-Math.max(String(a.team||'').length,String(a.name||'').length));
    return members.find(m=>(m.team&&text.includes(String(m.team).toLowerCase()))||(m.name&&text.includes(String(m.name).toLowerCase())))||members[0]||null;
  }

  function currentGw(member){
    const page=document.getElementById('teamPage');
    if(page){
      for(const el of page.querySelectorAll('*')){
        if(el.children.length||el.offsetParent===null)continue;
        const t=(el.textContent||'').trim(),m=t.match(/^Gameweek\s*(\d+)$/i)||t.match(/^GW\s*(\d+)$/i);
        if(m)return Number(m[1]);
      }
    }
    return Number(member?.currentGameweek||state?.currentGameweek||1);
  }

  function chooseNativeHost(page){
    const direct=[...page.querySelectorAll('.rightPanel,.chipsPanel,.teamSide')];
    if(!direct.length)return null;
    /* Prefer the outer/right-most panel, not a nested child panel. */
    direct.sort((a,b)=>{
      const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
      return br.left-ar.left || br.width-ar.width;
    });
    return direct[0]||null;
  }

  function cleanup(){
    document.getElementById('fmLeagueManagerSidePanel')?.remove();
    document.querySelectorAll('.fmLeagueOverviewHost').forEach(x=>x.classList.remove('fmLeagueOverviewHost'));
    document.querySelectorAll('.fmLeagueFallbackGrid').forEach(x=>x.classList.remove('fmLeagueFallbackGrid'));
    document.getElementById('teamPage')?.removeAttribute('data-fm-league-panel');
  }

  function render(){
    addStyles();
    const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');
    if(!page||!banner?.classList.contains('show')){cleanup();return}
    const member=memberBeingViewed();if(!member){cleanup();return}
    page.classList.add('leagueReadOnly');
    let panel=document.getElementById('fmLeagueManagerSidePanel');
    const native=chooseNativeHost(page);
    let host=native;
    if(native){
      native.classList.add('fmLeagueOverviewHost');
      if(!panel){panel=document.createElement('aside');panel.id='fmLeagueManagerSidePanel'}
      if(panel.parentElement!==native)native.appendChild(panel);
    }else{
      const pitch=page.querySelector('.pitchCard,.pitchWrap,.pitch');
      const parent=pitch?.parentElement||page.querySelector('.teamGrid')||page;
      parent.classList.add('fmLeagueFallbackGrid');
      if(!panel){panel=document.createElement('aside');panel.id='fmLeagueManagerSidePanel'}
      if(panel.parentElement!==parent)parent.appendChild(panel);
      host=parent;
    }
    const gw=currentGw(member),gp=gwPts(member,gw),total=totalPts(member);
    panel.innerHTML=`<div class="fmLspHero"><div class="fmLspIcon">★</div><h3>${esc(member.team||'My Team')}</h3><p>${esc(member.name||'Manager')} · read-only league team view.</p></div><div class="fmLspBody"><div class="fmLspBox"><div class="fmLspTitle">Manager Overview</div><div class="fmLspRow"><span>Team Name</span><b>${esc(member.team||'My Team')}</b></div><div class="fmLspRow"><span>Manager</span><b>${esc(member.name||'Manager')}</b></div><div class="fmLspRow"><span>Gameweek</span><b>GW ${gw}</b></div><div class="fmLspRow"><span>Gameweek Points</span><b class="pink">${gp}</b></div><div class="fmLspRow"><span>Total Points</span><b class="pink">${total}</b></div></div><div class="fmLspHint">Use the Gameweek arrows above the pitch to browse this manager's available Gameweeks. Their team remains read-only.</div></div>`;
    page.dataset.fmLeaguePanel=native?'native-right':'fallback';
  }

  let timer;const refresh=()=>{clearTimeout(timer);timer=setTimeout(render,90)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
  window.addEventListener('fmcloudready',refresh);
  document.addEventListener('click',()=>setTimeout(refresh,130),true);
  new MutationObserver(refresh).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
})();
