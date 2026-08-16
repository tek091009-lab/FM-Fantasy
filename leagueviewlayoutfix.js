(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rawHist=s=>Array.isArray(s?.pointsHistory)?s.pointsHistory:Array.isArray(s?.history)?s.history:[];
  const hist=s=>{const entry=Number(s?.entryGameweek||1)||1;return rawHist(s).filter(x=>(Number(x?.gw)||0)>=entry)};
  const totalPts=s=>{const h=hist(s);return h.length?h.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0):Number(s?.points??s?.totalPoints??0)};
  const gwPts=(s,gw)=>{const x=hist(s).find(r=>Number(r?.gw)===Number(gw));return x?Number(x?.net??x?.gross??0):0};

  function styles(){
    if(document.getElementById('fmLeagueLayoutFixStyles'))return;
    const s=document.createElement('style');s.id='fmLeagueLayoutFixStyles';s.textContent=`
      #teamPage.fmLeagueHardLayout{position:relative!important;overflow-x:hidden!important;box-sizing:border-box!important}
      #teamPage.fmLeagueHardLayout #fmLeagueManagerPanel,
      #teamPage.fmLeagueHardLayout #fmLeagueManagerSidePanel{display:none!important}
      #teamPage.fmLeagueHardLayout .fmLeagueOverviewHost{display:none!important}
      #teamPage.fmLeagueHardLayout .fmLeaguePitchTarget{box-sizing:border-box!important;width:calc(100% - 304px)!important;max-width:calc(100% - 304px)!important;min-width:0!important;margin-left:0!important;margin-right:304px!important}
      #teamPage.fmLeagueHardLayout .fmLeaguePitchTarget .pitch,
      #teamPage.fmLeagueHardLayout .fmLeaguePitchTarget .pitchCard,
      #teamPage.fmLeagueHardLayout .fmLeaguePitchTarget .pitchWrap{max-width:100%!important;width:100%!important;min-width:0!important}
      #teamPage.fmLeagueHardLayout #fmLeagueManagerSummary{width:100%!important;max-width:100%!important;box-sizing:border-box!important;overflow:hidden!important;margin-left:0!important;margin-right:0!important}
      #teamPage.fmLeagueHardLayout #viewBanner{max-width:100%!important;box-sizing:border-box!important}
      #fmLeagueManagerRightPanel{position:absolute!important;z-index:20!important;right:12px!important;width:280px!important;box-sizing:border-box!important;display:flex!important;flex-direction:column!important;border:1px solid rgba(255,255,255,.14)!important;border-radius:10px!important;overflow:hidden!important;background:linear-gradient(180deg,#1b1239,#110b28)!important;box-shadow:0 12px 32px rgba(0,0,0,.24)!important;color:#fff!important}
      .fmLrfHero{padding:22px 18px 20px;min-height:170px;box-sizing:border-box;background:linear-gradient(155deg,#c51a69,#a71156 58%,#7d103f);display:flex;flex-direction:column;justify-content:center}.fmLrfIcon{width:43px;height:43px;border-radius:50%;display:grid;place-items:center;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.08);font-size:22px;margin-bottom:15px}.fmLrfHero h3{margin:0 0 7px;font-size:23px;line-height:1.05;font-weight:1000;color:#fff}.fmLrfHero p{margin:0;font-size:12px;line-height:1.45;color:rgba(255,255,255,.92);font-weight:700}.fmLrfBody{padding:12px;display:flex;flex-direction:column;flex:1;min-height:0}.fmLrfBox{border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(35,22,73,.78);overflow:hidden}.fmLrfTitle{padding:13px 14px;font-size:13px;font-weight:950;border-bottom:1px solid rgba(255,255,255,.11)}.fmLrfRow{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.09);font-size:12px;color:#d0c7df}.fmLrfRow:last-child{border-bottom:0}.fmLrfRow b{color:#fff;font-size:12.5px;text-align:right;max-width:58%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fmLrfRow b.pink{color:#ff4ba8}.fmLrfHint{margin-top:auto;padding:12px 13px;border:1px solid rgba(255,255,255,.11);border-radius:8px;background:rgba(17,10,43,.65);font-size:11px;line-height:1.45;color:#bfb4d2}
      @media(max-width:1050px){#teamPage.fmLeagueHardLayout .fmLeaguePitchTarget{width:100%!important;max-width:100%!important;margin-right:0!important}#fmLeagueManagerRightPanel{position:relative!important;right:auto!important;top:auto!important;width:100%!important;margin-top:12px!important;min-height:0!important}.fmLrfHint{margin-top:12px}}
    `;document.head.appendChild(s);
  }

  function member(){
    const banner=document.getElementById('viewBanner');if(!banner?.classList.contains('show')||typeof state==='undefined')return null;
    const text=(banner.textContent||'').toLowerCase(),members=[];
    for(const l of(state.leagues||[]))for(const m of(l.members||[]))if(!m.own)members.push(m);
    members.sort((a,b)=>Math.max(String(b.team||'').length,String(b.name||'').length)-Math.max(String(a.team||'').length,String(a.name||'').length));
    return members.find(m=>(m.team&&text.includes(String(m.team).toLowerCase()))||(m.name&&text.includes(String(m.name).toLowerCase())))||members[0]||null;
  }

  function selectedGw(m){
    const page=document.getElementById('teamPage');if(page){for(const el of page.querySelectorAll('*')){if(el.children.length||el.offsetParent===null)continue;const t=(el.textContent||'').trim(),x=t.match(/^Gameweek\s*(\d+)$/i)||t.match(/^GW\s*(\d+)$/i);if(x)return Number(x[1])}}
    return Number(m?.currentGameweek||state?.currentGameweek||1);
  }

  function pitchTarget(page){
    const candidates=[...page.querySelectorAll('.pitchCard,.pitchWrap,.pitch')].filter(el=>el.offsetParent!==null);
    if(!candidates.length)return null;
    candidates.sort((a,b)=>{const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();return (br.width*br.height)-(ar.width*ar.height)});
    let target=candidates[0];
    // Prefer the outer wrapper when it only contains the pitch and naturally spans the main content column.
    let p=target.parentElement;
    const pageRect=page.getBoundingClientRect();
    for(let i=0;i<3&&p&&p!==page;i++,p=p.parentElement){const r=p.getBoundingClientRect();if(r.width>target.getBoundingClientRect().width*.98&&r.width<pageRect.width*1.05)target=p}
    return target;
  }

  function clear(){
    const page=document.getElementById('teamPage');page?.classList.remove('fmLeagueHardLayout');
    document.querySelectorAll('.fmLeaguePitchTarget').forEach(x=>x.classList.remove('fmLeaguePitchTarget'));
    document.getElementById('fmLeagueManagerRightPanel')?.remove();
  }

  function render(){
    styles();
    const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');
    if(!page||!banner?.classList.contains('show')){clear();return}
    const m=member(),target=pitchTarget(page);if(!m||!target){clear();return}
    page.classList.add('fmLeagueHardLayout');
    document.querySelectorAll('.fmLeaguePitchTarget').forEach(x=>{if(x!==target)x.classList.remove('fmLeaguePitchTarget')});target.classList.add('fmLeaguePitchTarget');
    let panel=document.getElementById('fmLeagueManagerRightPanel');if(!panel){panel=document.createElement('aside');panel.id='fmLeagueManagerRightPanel';page.appendChild(panel)}
    const pr=page.getBoundingClientRect(),tr=target.getBoundingClientRect(),top=Math.max(0,tr.top-pr.top),height=Math.max(560,tr.height);
    if(innerWidth>1050){panel.style.top=`${top}px`;panel.style.height=`${height}px`}else{panel.style.top='auto';panel.style.height='auto';if(panel.parentElement!==target.parentElement)target.insertAdjacentElement('afterend',panel)}
    const gw=selectedGw(m),gp=gwPts(m,gw),total=totalPts(m);
    panel.innerHTML=`<div class="fmLrfHero"><div class="fmLrfIcon">★</div><h3>${esc(m.team||'My Team')}</h3><p>${esc(m.name||'Manager')} · read-only league team view.</p></div><div class="fmLrfBody"><div class="fmLrfBox"><div class="fmLrfTitle">Manager Overview</div><div class="fmLrfRow"><span>Team Name</span><b>${esc(m.team||'My Team')}</b></div><div class="fmLrfRow"><span>Manager</span><b>${esc(m.name||'Manager')}</b></div><div class="fmLrfRow"><span>Gameweek</span><b>GW ${gw}</b></div><div class="fmLrfRow"><span>Gameweek Points</span><b class="pink">${gp}</b></div><div class="fmLrfRow"><span>Total Points</span><b class="pink">${total}</b></div></div><div class="fmLrfHint">Use the Gameweek arrows above the pitch to browse this manager's available Gameweeks. Their team remains read-only.</div></div>`;
  }

  let timer;const refresh=()=>{clearTimeout(timer);timer=setTimeout(render,100)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
  window.addEventListener('fmcloudready',refresh);window.addEventListener('resize',refresh);
  document.addEventListener('click',()=>setTimeout(refresh,140),true);
  new MutationObserver(refresh).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
})();
