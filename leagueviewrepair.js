(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rawHist=s=>Array.isArray(s?.pointsHistory)?s.pointsHistory:Array.isArray(s?.history)?s.history:[];
  const hist=s=>{const entry=Number(s?.entryGameweek||1)||1;return rawHist(s).filter(x=>(Number(x?.gw)||0)>=entry)};
  const totalPts=s=>{const h=hist(s);return h.length?h.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0):Number(s?.points??s?.totalPoints??0)};
  const gwPts=(s,gw)=>{const x=hist(s).find(r=>Number(r?.gw)===Number(gw));return x?Number(x?.net??x?.gross??0):0};

  function addStyles(){
    if(document.getElementById('fmLeagueViewRepairStyles'))return;
    const s=document.createElement('style');s.id='fmLeagueViewRepairStyles';s.textContent=`
      body.fmLeagueViewing{overflow-x:hidden!important}
      #teamPage.fmLeagueViewportRepair{overflow-x:hidden!important;box-sizing:border-box!important}
      #teamPage.fmLeagueViewportRepair #fmLeagueManagerPanel,
      #teamPage.fmLeagueViewportRepair #fmLeagueManagerSidePanel,
      #teamPage.fmLeagueViewportRepair .fmLeagueOverviewHost{display:none!important}
      #teamPage.fmLeagueViewportRepair .fmLeagueRepairPitch{box-sizing:border-box!important;min-width:0!important;margin-right:0!important}
      #teamPage.fmLeagueViewportRepair .fmLeagueRepairPitch .pitch,
      #teamPage.fmLeagueViewportRepair .fmLeagueRepairPitch .pitchCard,
      #teamPage.fmLeagueViewportRepair .fmLeagueRepairPitch .pitchWrap{width:100%!important;max-width:100%!important;min-width:0!important}
      #fmLeagueManagerRightPanel{position:absolute!important;right:auto!important;box-sizing:border-box!important;display:flex!important;visibility:visible!important;opacity:1!important;z-index:500!important;width:280px!important;min-width:280px!important;max-width:280px!important;border:1px solid rgba(255,255,255,.15)!important;border-radius:11px!important;overflow:hidden!important;background:linear-gradient(180deg,#1b1239,#110b28)!important;box-shadow:0 14px 36px rgba(0,0,0,.28)!important;color:#fff!important}
      #fmLeagueManagerSummary.fmLeagueRepairSummary{box-sizing:border-box!important;overflow:hidden!important;margin-right:0!important}
      #fmLeagueManagerSummary.fmLeagueRepairSummary .fmMgrCell{min-width:0!important}
      .fmLrrHero{padding:22px 18px 20px;min-height:170px;box-sizing:border-box;background:linear-gradient(155deg,#c51a69,#a71156 58%,#7d103f);display:flex;flex-direction:column;justify-content:center}.fmLrrIcon{width:43px;height:43px;border-radius:50%;display:grid;place-items:center;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.08);font-size:22px;margin-bottom:15px}.fmLrrHero h3{margin:0 0 7px;font-size:23px;line-height:1.05;font-weight:1000;color:#fff;white-space:normal;overflow-wrap:anywhere}.fmLrrHero p{margin:0;font-size:12px;line-height:1.45;color:rgba(255,255,255,.92);font-weight:700}.fmLrrBody{padding:12px;display:flex;flex-direction:column;flex:1;min-height:0}.fmLrrBox{border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(35,22,73,.78);overflow:hidden}.fmLrrTitle{padding:13px 14px;font-size:13px;font-weight:950;border-bottom:1px solid rgba(255,255,255,.11)}.fmLrrRow{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.09);font-size:12px;color:#d0c7df}.fmLrrRow:last-child{border-bottom:0}.fmLrrRow b{color:#fff;font-size:12.5px;text-align:right;max-width:58%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fmLrrRow b.pink{color:#ff4ba8}.fmLrrHint{margin-top:auto;padding:12px 13px;border:1px solid rgba(255,255,255,.11);border-radius:8px;background:rgba(17,10,43,.65);font-size:11px;line-height:1.45;color:#bfb4d2}
      @media(max-width:1100px){#fmLeagueManagerRightPanel{position:relative!important;left:auto!important;top:auto!important;width:100%!important;min-width:0!important;max-width:none!important;height:auto!important;margin-top:12px!important}.fmLrrHint{margin-top:12px}}
    `;document.head.appendChild(s);
  }

  function viewedTeamName(){
    const b=document.getElementById('viewBanner');if(!b)return'';
    const leaves=[...b.querySelectorAll('*')].filter(x=>!x.children.length).map(x=>(x.textContent||'').trim()).filter(Boolean);
    const leaf=leaves.find(t=>/^Viewing\s+/i.test(t));
    if(leaf)return leaf.replace(/^Viewing\s+/i,'').trim();
    const m=(b.textContent||'').match(/Viewing\s+(.+?)(?:\s{2,}|Back to League|$)/i);
    return m?m[1].trim():'';
  }

  function allMembers(){
    if(typeof state==='undefined')return[];
    const out=[];for(const l of(state.leagues||[]))for(const m of(l.members||[]))out.push(m);
    return out;
  }

  function resolveMember(){
    const team=viewedTeamName().toLowerCase();const members=allMembers();
    if(team){
      const exact=members.find(m=>String(m.team||'').trim().toLowerCase()===team);if(exact)return exact;
      const exactName=members.find(m=>String(m.name||'').trim().toLowerCase()===team);if(exactName)return exactName;
      const partial=members.find(m=>team.includes(String(m.team||'').trim().toLowerCase())||String(m.team||'').trim().toLowerCase().includes(team));if(partial)return partial;
    }
    return null;
  }

  function selectedGw(m){
    const page=document.getElementById('teamPage');if(page){for(const el of page.querySelectorAll('*')){if(el.children.length||el.offsetParent===null)continue;const t=(el.textContent||'').trim(),x=t.match(/^Gameweek\s*(\d+)$/i)||t.match(/^GW\s*(\d+)$/i);if(x)return Number(x[1])}}
    return Number(m?.currentGameweek||state?.currentGameweek||1);
  }

  function findPitchTarget(page){
    let t=page.querySelector('.fmLeaguePitchTarget');if(t&&t.offsetParent!==null)return t;
    const c=[...page.querySelectorAll('.pitchCard,.pitchWrap,.pitch')].filter(x=>x.offsetParent!==null);
    if(!c.length)return null;c.sort((a,b)=>{const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();return br.width*br.height-ar.width*ar.height});
    t=c[0];let p=t.parentElement;const pr=page.getBoundingClientRect();for(let i=0;i<3&&p&&p!==page;i++,p=p.parentElement){const r=p.getBoundingClientRect();if(r.width>=t.getBoundingClientRect().width*.98&&r.width<=pr.width*1.05)t=p}return t;
  }

  function rewriteBanner(member){
    const b=document.getElementById('viewBanner');if(!b)return;
    const leaves=[...b.querySelectorAll('*')].filter(x=>!x.children.length);
    const sub=leaves.find(x=>/read-only/i.test(x.textContent||''));
    if(sub)sub.textContent=`${member.name||'Manager'} · ${totalPts(member)} pts · read-only`;
  }

  function renderSummary(member,gw,gp,total){
    const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');if(!page||!banner)return null;
    let bar=document.getElementById('fmLeagueManagerSummary');if(!bar){bar=document.createElement('div');bar.id='fmLeagueManagerSummary';banner.insertAdjacentElement('afterend',bar)}
    bar.className='fmLeagueRepairSummary';
    bar.innerHTML=`<div class="fmMgrCell"><span>Team Name</span><b>${esc(member.team||'My Team')}</b></div><div class="fmMgrCell"><span>Manager</span><b>${esc(member.name||'Manager')}</b></div><div class="fmMgrCell"><span>Gameweek</span><b>GW ${gw} <em>${gp} pts</em></b></div><div class="fmMgrCell"><span>Total Points</span><b class="pink">${total}</b></div>`;
    return bar;
  }

  function renderPanel(member,gw,gp,total){
    let p=document.getElementById('fmLeagueManagerRightPanel');if(!p){p=document.createElement('aside');p.id='fmLeagueManagerRightPanel';document.body.appendChild(p)}
    p.innerHTML=`<div class="fmLrrHero"><div class="fmLrrIcon">★</div><h3>${esc(member.team||'My Team')}</h3><p>${esc(member.name||'Manager')} · read-only league team view.</p></div><div class="fmLrrBody"><div class="fmLrrBox"><div class="fmLrrTitle">Manager Overview</div><div class="fmLrrRow"><span>Team Name</span><b>${esc(member.team||'My Team')}</b></div><div class="fmLrrRow"><span>Manager</span><b>${esc(member.name||'Manager')}</b></div><div class="fmLrrRow"><span>Gameweek</span><b>GW ${gw}</b></div><div class="fmLrrRow"><span>Gameweek Points</span><b class="pink">${gp}</b></div><div class="fmLrrRow"><span>Total Points</span><b class="pink">${total}</b></div></div><div class="fmLrrHint">Use the Gameweek arrows above the pitch to browse this manager's available Gameweeks. Their team remains read-only.</div></div>`;return p;
  }

  function cleanup(){
    document.body.classList.remove('fmLeagueViewing');const page=document.getElementById('teamPage');page?.classList.remove('fmLeagueViewportRepair');document.querySelectorAll('.fmLeagueRepairPitch').forEach(x=>{x.classList.remove('fmLeagueRepairPitch');x.style.removeProperty('width');x.style.removeProperty('max-width');x.style.removeProperty('margin-right')});document.getElementById('fmLeagueManagerRightPanel')?.remove();
  }

  function layout(){
    addStyles();const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');if(!page||!banner?.classList.contains('show')){cleanup();return}
    const m=resolveMember();if(!m)return;
    document.body.classList.add('fmLeagueViewing');page.classList.add('fmLeagueViewportRepair','leagueReadOnly');rewriteBanner(m);
    const gw=selectedGw(m),gp=gwPts(m,gw),total=totalPts(m),summary=renderSummary(m,gw,gp,total),panel=renderPanel(m,gw,gp,total),target=findPitchTarget(page);if(!target)return;
    document.querySelectorAll('.fmLeagueRepairPitch').forEach(x=>{if(x!==target)x.classList.remove('fmLeagueRepairPitch')});target.classList.add('fmLeagueRepairPitch');
    const pr=page.getBoundingClientRect(),tr=target.getBoundingClientRect();
    if(innerWidth>1100){
      const panelW=280,gap=14,edge=14,visibleRight=Math.min(innerWidth-edge,pr.right-edge),panelLeft=visibleRight-panelW,avail=Math.max(640,panelLeft-gap-tr.left);
      target.style.setProperty('width',`${avail}px`,'important');target.style.setProperty('max-width',`${avail}px`,'important');target.style.setProperty('margin-right','0px','important');
      const tr2=target.getBoundingClientRect();panel.style.left=`${Math.max(edge,panelLeft)+scrollX}px`;panel.style.top=`${tr2.top+scrollY}px`;panel.style.height=`${Math.max(560,tr2.height)}px`;
      if(summary){const sr=summary.getBoundingClientRect(),sw=Math.max(500,panelLeft-gap-sr.left);summary.style.setProperty('width',`${sw}px`,'important');summary.style.setProperty('max-width',`${sw}px`,'important')}
      const br=banner.getBoundingClientRect(),bw=Math.max(500,visibleRight-br.left);banner.style.setProperty('max-width',`${bw}px`,'important');
    }else{
      target.style.setProperty('width','100%','important');target.style.setProperty('max-width','100%','important');panel.style.left='auto';panel.style.top='auto';panel.style.height='auto';if(panel.parentElement!==target.parentElement)target.insertAdjacentElement('afterend',panel);if(summary){summary.style.setProperty('width','100%','important');summary.style.setProperty('max-width','100%','important')}
    }
  }

  let timer;const refresh=()=>{clearTimeout(timer);timer=setTimeout(layout,100)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
  window.addEventListener('fmcloudready',refresh);window.addEventListener('resize',refresh);window.addEventListener('scroll',refresh,{passive:true});document.addEventListener('click',()=>setTimeout(refresh,140),true);
  new MutationObserver(refresh).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
})();
