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

      #statsPage [class*="leader"],#statsPage [class*="insight"],
      #leaguesPage [class*="league"],#newsPage [class*="news"]{line-height:1.38!important}
    `;
    document.head.appendChild(s);
  }

  function pageMinimum(root){
    const id=(root?.id||'').toLowerCase();
    if(id.includes('news')) return 9;
    if(id.includes('settings')) return 9;
    return 0;
  }

  function readableLeaf(el,min){
    if(!el||!min||el.closest(SKIP_CLOSEST)) return;
    const text=(el.textContent||'').trim();
    if(!text||!/[A-Za-z0-9£€%]/.test(text)) return;
    const cs=getComputedStyle(el), current=parseFloat(cs.fontSize||'0');
    if(!current||current>=min) return;

    let target=min;
    if(el.tagName==='SMALL') target=Math.max(target,8.5);
    if(el.matches('button,a')) target=Math.max(target,9);

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

  let frame=0;
  const schedule=()=>{cancelAnimationFrame(frame);scanActive();frame=requestAnimationFrame(scanActive)};

  addStyles();
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',schedule,{once:true});
  else schedule();

  new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('click',schedule,true);
  window.addEventListener('fmcloudready',schedule);
})();

/* Final desktop polish: stable shell, interactive comparisons, aggregate Star XI,
   richer concept components and FM injury-table enrichment. */
(()=>{
  const byId=id=>document.getElementById(id);
  const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function addFinalStyles(){
    if(byId('fmFinalPolishStyles'))return;
    const s=document.createElement('style');s.id='fmFinalPolishStyles';s.textContent=`
      html,body,.app{min-width:0!important;max-width:100%!important}
      .main,.page,.page.active{min-width:0!important;max-width:100%!important;box-sizing:border-box!important}
      .page{zoom:1!important;width:100%!important}

      /* Fixed desktop navigation that fits at 100% browser zoom on first paint. */
      @media(min-width:1181px){
        .app{grid-template-columns:255px minmax(0,1fr)!important}
        .sidebar{position:sticky!important;top:0!important;display:flex!important;flex-direction:column!important;width:255px!important;height:100dvh!important;min-height:0!important;padding:10px 9px 9px!important;box-sizing:border-box!important;overflow-x:hidden!important;overflow-y:auto!important;scrollbar-width:thin!important;scrollbar-color:#57327b transparent!important}
        .sidebar .logo{flex:0 0 auto!important;min-height:54px!important;padding:2px 6px 12px!important}
        .sidebar .snav{flex:0 0 auto!important;gap:2px!important}
        .sidebar .snav button{min-height:43px!important;padding:0 12px!important;font-size:13px!important}
        .sidebar .snav button.subnav{min-height:35px!important;padding-left:27px!important;font-size:11px!important}
        .sidebar .syncbox{flex:0 0 auto!important;margin:10px 6px 0!important;padding:10px!important}
        .sidebar .syncBtns{gap:5px!important}.sidebar .syncBtn{min-height:30px!important;padding:5px 7px!important;font-size:8px!important}
        .sidebar .syncStatus{font-size:7px!important}.sidebar .syncLeague{font-size:8px!important}
        body:has(#teamPage.fmLeagueStarExact.active) .main{overflow-x:hidden!important}
        #teamPage.fmLeagueStarExact{width:100%!important;max-width:100%!important;overflow-x:hidden!important}
        #teamPage.fmLeagueStarExact .teamGrid.teamWorkspace{grid-template-columns:minmax(0,1fr) clamp(250px,17.5vw,290px)!important;width:100%!important;max-width:100%!important;box-sizing:border-box!important}
        #teamPage.fmLeagueStarExact #teamSide.fmLeagueStarSide{min-width:0!important;width:100%!important;box-sizing:border-box!important}
      }
      @media(min-width:1181px) and (max-height:860px){
        .sidebar .logo{min-height:47px!important;padding-bottom:8px!important}.sidebar .logoMark{width:30px!important;height:30px!important;flex-basis:30px!important}
        .sidebar .snav button{min-height:37px!important}.sidebar .snav button.subnav{min-height:30px!important}
        .sidebar .syncbox{margin-top:6px!important;padding:8px!important}.sidebar .syncBtn{min-height:27px!important;padding:4px 6px!important}
      }

      /* Star XI alignment and aggregate view. */
      #starPage .pitch .pchip{isolation:isolate!important}
      #starPage .pitch .clubCrest{top:19px!important;left:50%!important;margin-left:8px!important;transform:translateX(-50%)!important}
      #starPage .pitch .starXIJump{right:7px!important;bottom:7px!important;display:grid!important;place-items:center!important;padding:0!important;line-height:1!important;transform:none!important}
      #starPage .pitch .starXIJump:hover{transform:scale(1.06)!important}
      #starPage .pitch .allStar{border:1px solid rgba(255,241,160,.9)!important;color:#4a2b00!important;background:linear-gradient(145deg,#fff3a4,#f5b51b 54%,#d98400)!important;box-shadow:0 5px 15px rgba(235,171,15,.48)!important;cursor:default!important}
      #starPage .pitch .pchip.starAllCard{box-shadow:inset 1px 0 rgba(255,255,255,.2),inset -1px 0 rgba(255,255,255,.2),0 9px 20px rgba(0,0,0,.2),0 0 0 1px rgba(255,211,71,.16)!important}
      #starAllToggle{min-width:42px;height:27px;margin-left:5px;padding:0 9px;border:1px solid rgba(255,255,255,.13);border-radius:8px;color:#d8cce8;background:#211440;font:800 9px/1 inherit;cursor:pointer;pointer-events:auto!important}
      #starAllToggle.active{border-color:#f4c54c;color:#352000;background:linear-gradient(135deg,#fff2a0,#f1b72d)}
      @media(min-width:1181px) and (max-height:850px){#starPage .pitch .clubCrest{top:10px!important;margin-left:5px!important}#starPage .pitch .starXIJump{right:5px!important;bottom:4px!important}}

      /* Comparison concept: real category tabs and one focused stat panel. */
      #compareModal .compareModal{width:min(1180px,calc(100vw - 32px))!important;max-height:calc(100dvh - 28px)!important;overflow:hidden!important;border-radius:16px!important;background:linear-gradient(180deg,#160d36,#0e0928)!important;box-shadow:0 32px 80px rgba(0,0,0,.55)!important}
      #compareModal .modalBody{max-height:calc(100dvh - 96px)!important;overflow:auto!important}
      .compareCategoryNav span{position:relative;cursor:pointer!important;user-select:none;transition:.16s ease!important}
      .compareCategoryNav span:hover,.compareCategoryNav span:focus-visible{color:#fff!important;background:rgba(206,53,230,.08)!important;outline:0!important}
      .compareCategoryNav span.active{color:#fff!important;background:linear-gradient(180deg,rgba(244,42,159,.16),rgba(158,50,233,.04))!important}
      .compareSection[hidden]{display:none!important}.compareSection.fmCompareActive{display:block!important;animation:fmCompareIn .18s ease both}
      @keyframes fmCompareIn{from{opacity:.35;transform:translateY(3px)}to{opacity:1;transform:none}}

      /* Featured league concept. */
      #leaguesPage .featuredCard{position:relative;grid-template-columns:92px minmax(0,1fr) auto!important;min-height:190px!important;padding:22px!important;overflow:hidden!important;border-color:rgba(224,118,255,.3)!important;background:radial-gradient(circle at 85% 15%,rgba(244,45,181,.2),transparent 35%),linear-gradient(125deg,#35115d,#1e103f 54%,#291050)!important;box-shadow:inset 0 1px rgba(255,255,255,.05),0 18px 38px rgba(0,0,0,.22)!important}
      #leaguesPage .featuredCard:before{content:'TOP LEAGUE';position:absolute;top:15px;right:18px;padding:5px 9px;border:1px solid rgba(250,210,91,.35);border-radius:999px;color:#ffe17d;background:rgba(94,55,9,.26);font-size:8px;font-weight:900;letter-spacing:.09em}
      #leaguesPage .featuredCrest{width:82px!important;height:94px!important;border-radius:24px 24px 34px 34px!important;font-size:39px!important;background:radial-gradient(circle at 50% 24%,#bb54cb,#632281 45%,#281747 78%)!important;box-shadow:0 0 0 7px rgba(211,77,234,.06),0 20px 30px rgba(0,0,0,.3)!important}
      #leaguesPage .featuredCard h3{margin-bottom:14px!important;font-size:21px!important}.featuredMeta{gap:34px!important}.featuredMeta span{font-size:9px!important}.featuredMeta b{font-size:16px!important}.featuredAvatar{width:31px!important;height:31px!important;font-size:8px!important}.featuredOpen{min-height:34px!important;padding:8px 19px!important;font-size:9px!important}

      /* League detail concept. */
      #leagueModal .modal{width:min(760px,calc(100vw - 28px))!important;overflow:hidden!important;border:1px solid rgba(210,111,238,.28)!important;border-radius:18px!important;background:linear-gradient(180deg,#1c1040,#100a2c)!important}
      #leagueModal .modalHead{min-height:92px!important;padding:20px 24px!important;background:radial-gradient(circle at 80% 0,rgba(242,49,171,.2),transparent 45%),linear-gradient(110deg,#671344,#351358)!important}
      #leagueModal .modalBody{padding:18px!important;background:transparent!important}
      #leagueModal .metrics{display:grid!important;grid-template-columns:repeat(3,1fr)!important;gap:10px!important;margin-bottom:16px!important}
      #leagueModal .metric{position:relative!important;min-height:86px!important;padding:17px 14px!important;border:1px solid rgba(219,164,255,.18)!important;border-radius:13px!important;color:#fff!important;background:linear-gradient(145deg,#271449,#1b103c)!important;text-align:center!important}
      #leagueModal .metric small{color:#a99abb!important}#leagueModal .metric b{display:block!important;margin-top:6px!important;color:#fff!important;font-size:20px!important}
      #leagueModal .leagueRow{min-height:58px!important;margin-top:7px!important;padding:10px 13px!important;border:1px solid rgba(213,154,247,.13)!important;border-radius:10px!important;background:#160d35!important}

      /* Season insights concept. */
      #statsPage #statsInsights{gap:7px!important;padding:7px!important}
      #statsPage .insightCard{counter-reset:insightRank;position:relative!important;min-height:0!important;padding:8px!important;overflow:hidden!important;border-color:rgba(255,255,255,.09)!important;border-radius:9px!important;background:radial-gradient(circle at 100% 0,rgba(197,48,241,.12),transparent 38%),linear-gradient(145deg,#221345,#130c31)!important}
      #statsPage .insightCard:nth-child(2){background:radial-gradient(circle at 100% 0,rgba(40,133,255,.14),transparent 38%),linear-gradient(145deg,#181b48,#100d30)!important}
      #statsPage .insightCard:nth-child(3){background:radial-gradient(circle at 100% 0,rgba(39,210,152,.13),transparent 38%),linear-gradient(145deg,#123b3b,#100d30)!important}
      #statsPage .insightCard:nth-child(4){background:radial-gradient(circle at 100% 0,rgba(255,183,55,.13),transparent 38%),linear-gradient(145deg,#36243c,#100d30)!important}
      #statsPage .insightCard>b{font-size:9px!important}#statsPage .insightCard>small{margin:2px 0 5px!important;font-size:6px!important}
      #statsPage .insightLine{counter-increment:insightRank;grid-template-columns:16px minmax(0,1fr) 52px 27px!important;gap:5px!important;margin-top:5px!important;font-size:7px!important}
      #statsPage .insightLine:before{content:counter(insightRank);display:grid;place-items:center;width:17px;height:17px;border-radius:5px;color:#e8dcf7;background:#37205e;font-size:7px;font-weight:900}
      #statsPage .insightBar{height:6px!important;background:rgba(3,2,22,.45)!important}#statsPage .insightLine em{font-size:7px!important}
      #statsPage .insightCard:nth-child(2) .insightBar i{background:linear-gradient(90deg,#477cff,#2ac8ff)!important}#statsPage .insightCard:nth-child(3) .insightBar i{background:linear-gradient(90deg,#25a77a,#65e8ae)!important}#statsPage .insightCard:nth-child(4) .insightBar i{background:linear-gradient(90deg,#e79826,#ffd160)!important}

      @media(max-width:800px){#leaguesPage .featuredCard{grid-template-columns:70px 1fr!important}.featuredCard>div:last-child{grid-column:1/-1!important}#leagueModal .metrics{grid-template-columns:1fr!important}}
    `;document.head.appendChild(s);
  }

  function resetPageFit(){
    document.querySelectorAll('.page').forEach(p=>{p.style.setProperty('zoom','1','important');p.style.setProperty('width','100%','important')});
  }

  function installStableFit(){
    try{fitActivePage=function(){resetPageFit()}}catch(_e){}
    resetPageFit();requestAnimationFrame(resetPageFit);setTimeout(resetPageFit,120);setTimeout(resetPageFit,600);
  }

  function updateIdentity(){
    if(typeof state==='undefined')return;
    const manager=String(state.managerName||'The Gaffer').trim()||'The Gaffer';
    const user=document.querySelector('.top .user,.user');
    const name=user?.querySelector(':scope > div:last-child > b');if(name)name.textContent=manager;
    const avatar=user?.querySelector('.userAvatar');if(avatar)avatar.textContent=manager.split(/\s+/).map(x=>x[0]).join('').slice(0,2).toUpperCase()||'G';
  }

  function installOwnMemberIdentity(){
    try{const original=ownMember;ownMember=function(){const out=original();out.name=state?.managerName||'The Gaffer';out.team=state?.teamName||out.team||'My Team';return out}}catch(_e){}
  }

  let compareCategory=0;
  function wireComparison(){
    const body=byId('compareBody'),nav=body?.querySelector('.compareCategoryNav');if(!nav)return;
    const tabs=[...nav.querySelectorAll('span')],sections=[...body.querySelectorAll(':scope > .compareSection')];if(tabs.length!==4||sections.length<4)return;
    const apply=i=>{compareCategory=Math.max(0,Math.min(3,Number(i)||0));tabs.forEach((t,n)=>{t.classList.toggle('active',n===compareCategory);t.setAttribute('aria-selected',String(n===compareCategory));t.tabIndex=0;t.setAttribute('role','tab')});sections.forEach((x,n)=>{x.hidden=n!==compareCategory;x.classList.toggle('fmCompareActive',n===compareCategory)})};
    if(!nav.dataset.fmTabs){nav.dataset.fmTabs='1';tabs.forEach((t,i)=>{t.dataset.compareCategory=String(i);t.onclick=()=>apply(i);t.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();apply(i)}if(e.key==='ArrowRight'){e.preventDefault();apply((i+1)%4);tabs[(i+1)%4].focus()}if(e.key==='ArrowLeft'){e.preventDefault();apply((i+3)%4);tabs[(i+3)%4].focus()}}})}
    apply(compareCategory);
  }

  let starAll=false,baseRenderStar=null;
  function aggregatePlayerPoints(p){
    const max=Number(META?.completed_gameweek||0),hist=Array.isArray(p?.history)?p.history:[];
    const rows=hist.filter(h=>{const gw=Number(h?.gameweek??h?.gw??0);return gw>0&&gw<=max});
    if(rows.length)return Math.round(rows.reduce((n,h)=>n+Number(h?.fpl_points??h?.fantasy_points??h?.points??0),0));
    const weekly=p?.weekly_points||{};const vals=Object.entries(weekly).filter(([gw])=>Number(gw)<=max).map(([,v])=>Number(v||0));
    if(vals.length)return Math.round(vals.reduce((a,b)=>a+b,0));
    return Math.round(Number(p?.fantasy_points||0));
  }
  function allStarTeam(){
    const pool=(PLAYERS||[]).filter(p=>p&&p.visible!==false&&p.available!==false).map(p=>({p,pts:aggregatePlayerPoints(p)}));
    const grouped={};for(const pos of ['GK','DEF','MID','FWD'])grouped[pos]=pool.filter(x=>x.p.pos===pos).sort((a,b)=>b.pts-a.pts||Number(b.p.fantasy_points||0)-Number(a.p.fantasy_points||0));
    let best=null;for(let d=3;d<=5;d++)for(let m=2;m<=5;m++){const f=10-d-m;if(f<1||f>3)continue;const picks=[...grouped.GK.slice(0,1),...grouped.DEF.slice(0,d),...grouped.MID.slice(0,m),...grouped.FWD.slice(0,f)];if(picks.length!==11||new Set(picks.map(x=>String(x.p.id))).size!==11)continue;const points=picks.reduce((n,x)=>n+x.pts,0);if(!best||points>best.points)best={picks,points,formation:{GK:1,DEF:d,MID:m,FWD:f}}}
    return best||{picks:[],points:0,formation:{}};
  }
  function ensureAllControl(){
    const nav=byId('starGWLabel')?.parentElement,host=nav?.parentElement;if(!nav||!host)return null;let b=byId('starAllToggle');if(!b){b=document.createElement('button');b.id='starAllToggle';b.type='button';b.textContent='All';b.title='Highest aggregate points across all completed Gameweeks';host.appendChild(b)}else if(b.parentElement!==host)host.appendChild(b);if(!b.dataset.fmAllBound){b.dataset.fmAllBound='1';b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();starAll=!starAll;renderStar()})}b.style.pointerEvents='auto';b.classList.toggle('active',starAll);b.setAttribute('aria-pressed',String(starAll));return b;
  }
  function renderStarAll(){
    ensureAllControl();const best=allStarTeam(),players=best.picks.map(x=>x.p),pointMap=new Map(best.picks.map(x=>[String(x.p.id),x.pts]));
    const completed=Object.entries(STAR_TEAMS||{}).filter(([gw,x])=>Number(gw)<=Number(META?.completed_gameweek||0)&&x).length||Number(META?.completed_gameweek||0),value=players.reduce((n,p)=>n+Number(p.price||0),0);
    if(byId('starPrevGW')){byId('starPrevGW').disabled=false;byId('starPrevGW').title='Return to the latest Gameweek'}if(byId('starNextGW')){byId('starNextGW').disabled=true}
    if(byId('starGWLabel'))byId('starGWLabel').textContent='All Gameweeks';if(byId('starGWValue'))byId('starGWValue').textContent='All';if(byId('starPoints'))byId('starPoints').textContent=best.points;if(byId('starValue'))byId('starValue').textContent=`£${value.toFixed(1)}m`;
    if(byId('starSidePoints'))byId('starSidePoints').textContent=best.points;if(byId('starSideValue'))byId('starSideValue').textContent=`£${value.toFixed(1)}m`;if(byId('starSideWeeks'))byId('starSideWeeks').textContent=completed;if(byId('starSideAverage'))byId('starSideAverage').textContent=completed?(best.points/completed).toFixed(1):'0.0';
    for(const pos of ['GK','DEF','MID','FWD']){const host=byId('star'+pos),list=players.filter(p=>p.pos===pos);if(!host)continue;host.innerHTML=list.map(p=>chip(p,'','','view',null)).join('');[...host.children].forEach((card,i)=>{const p=list[i],stat=[...card.querySelectorAll('span')].find(x=>!x.classList.contains('statusFlag'));if(stat)stat.textContent=`${pointMap.get(String(p.id))||0} pts`;card.classList.add('starAllCard');const star=document.createElement('span');star.className='starXIJump allStar';star.title='All-Gameweeks Star XI';star.textContent='★';card.appendChild(star)})}
    ensureAllControl()?.classList.add('active');
  }
  function installStarAll(){
    if(typeof renderStar!=='function'||baseRenderStar)return;baseRenderStar=renderStar;
    renderStar=function(){ensureAllControl();if(starAll){renderStarAll();return}baseRenderStar();ensureAllControl()?.classList.remove('active');if(byId('starNextGW'))byId('starNextGW').disabled=false};
    if(byId('starPrevGW'))byId('starPrevGW').onclick=()=>{if(starAll){starAll=false;starViewGW=Math.max(1,Number(META?.completed_gameweek||1))}else starViewGW=Math.max(1,starViewGW-1);renderStar()};
    if(byId('starNextGW'))byId('starNextGW').onclick=()=>{const last=Math.max(1,Number(META?.completed_gameweek||1));if(starAll){starAll=false;starViewGW=last}else starViewGW=Math.min(last,starViewGW+1);renderStar()};
    renderStar();
  }

  function normaliseInjuryRow(row,players){
    if(!row)return null;const rawId=row.pid??row.player_id??row.id??row.playerId,byPlayer=players.find(p=>rawId!=null&&[p.pid,p.id,p.eid,p.uid].some(x=>String(x)===String(rawId))),name=row.name??row.player_name??(byPlayer?playerName(byPlayer):null);if(!name)return null;
    const status=row.detail??row.injury_status??row.injury_name??row.injury??row.type??row.reason??'Injured',back=row.return_date??row.expected_return_date??row.end_date??null,text=String(status);if(/^(fit|none|false|0)$/i.test(text)||/recovered|fully fit|available/i.test(text))return null;
    return{pid:String(byPlayer?.pid??rawId??''),name:String(name),club:row.club??byPlayer?.club??'',pos:row.pos??byPlayer?.pos??'',detail:`${/^injur/i.test(text)?text:`Injured · ${text}`}${back?` · expected back ${typeof fmFmtStatusDate==='function'?fmFmtStatusDate(back):back}`:''}`};
  }
  function collectPayloadInjuries(payload){
    const sources=[payload?.injuries,payload?.active_injuries,payload?.player_injuries,payload?.injury_table,payload?.medical_statuses,payload?.medical?.injuries,payload?.medical?.active,payload?.availability?.injuries,payload?.statuses?.injuries].filter(Array.isArray),players=payload?.players||[],out=[];for(const rows of sources)for(const row of rows){const x=normaliseInjuryRow(row,players);if(x)out.push(x)}for(const p of players){const raw=p?.injury_status??p?.injury??p?.injury_name??p?.medical_status??p?.absence_reason??(p?.injured?'Injured':null);if(!raw)continue;const x=normaliseInjuryRow({...p,pid:p.pid??p.id,name:playerName(p),detail:raw},players);if(x)out.push(x)}return out;
  }
  const injurySeeds=['injur','hamstring','achilles','cruciate','ligament','tendon','knee','ankle','calf','groin','thigh','shoulder','wrist','foot','heel','concussion','illness','virus','fracture','strain','sprain','rehab','sidelined'];
  const injurySeedFirst=new Set(injurySeeds.map(word=>word.charCodeAt(0)));
  const injuryLabels=[
    [/anterior cruciate|cruciate|\bacl\b/i,'Cruciate ligament injury'],[/achilles/i,'Achilles injury'],[/hamstring/i,'Hamstring injury'],[/concussion|head injury/i,'Concussion'],[/fractur|broken /i,'Fracture'],[/ankle/i,'Ankle injury'],[/knee/i,'Knee injury'],[/calf/i,'Calf injury'],[/groin/i,'Groin injury'],[/thigh/i,'Thigh injury'],[/shoulder/i,'Shoulder injury'],[/wrist/i,'Wrist injury'],[/foot/i,'Foot injury'],[/heel/i,'Heel injury'],[/back/i,'Back injury'],[/hip/i,'Hip injury'],[/ligament/i,'Ligament injury'],[/tendon/i,'Tendon injury'],[/muscle/i,'Muscle injury'],[/strain/i,'Muscle strain'],[/sprain/i,'Sprain'],[/illness|virus|viral/i,'Illness'],[/injur|rehab|sidelined/i,'Injured']
  ];
  function injuryLabel(text){for(const [pattern,label] of injuryLabels)if(pattern.test(String(text||'')))return label;return'Injured'}
  function injuryTextHits(data,limit=18000){
    const letter=b=>{const c=b|32;return c>=97&&c<=122},hits=[];outer:for(let i=0;i<data.length;i++){const c=data[i]|32;if(!injurySeedFirst.has(c))continue;for(const word of injurySeeds){if(c!==word.charCodeAt(0))continue;let ascii=true,wide=true;for(let j=1;j<word.length;j++){if(i+j>=data.length||((data[i+j]|32)!==word.charCodeAt(j)))ascii=false;if(i+j*2>=data.length||data[i+j*2-1]!==0||((data[i+j*2]|32)!==word.charCodeAt(j)))wide=false;if(!ascii&&!wide)break}const asciiBefore=i===0||!letter(data[i-1]),asciiAfter=i+word.length>=data.length||!letter(data[i+word.length]),wideBefore=i<2||data[i-1]!==0||!letter(data[i-2]),wideAfter=i+word.length*2>=data.length||data[i+word.length*2-1]!==0||!letter(data[i+word.length*2]);ascii=ascii&&asciiBefore&&asciiAfter;wide=wide&&wideBefore&&wideAfter;if(ascii||wide){hits.push({at:i,wide,seed:word});i+=ascii?word.length-1:word.length*2-1;if(hits.length>=limit)break outer;break}}}return hits;
  }
  function nearestPlayerId(data,ids,at,span=850){
    const view=new DataView(data.buffer,data.byteOffset,data.byteLength),start=Math.max(0,at-span),end=Math.min(data.length-4,at+span);let best=null,bestDistance=Infinity,bestId=null;for(let off=start;off<=end;off++){const le=view.getUint32(off,true),be=view.getUint32(off,false),p=ids.get(le)||ids.get(be);if(!p)continue;const distance=Math.abs(off-at);if(distance<bestDistance){best=p;bestId=ids.has(le)?le:be;bestDistance=distance;if(distance<10)break}}return best?{player:best,distance:bestDistance,id:bestId}:null;
  }
  function inferredSaveDate(payload){
    const fixtures=payload?.fixtures||[],current=Number(payload?.meta?.current_gameweek||0),future=fixtures.filter(f=>(!current||Number(f.gameweek)>=current)&&f.status!=='played'&&f.date).map(f=>new Date(`${f.date}T12:00:00Z`)).filter(d=>!Number.isNaN(+d)).sort((a,b)=>a-b);if(future.length){const d=new Date(future[0]);d.setUTCDate(d.getUTCDate()-1);return d}const played=fixtures.filter(f=>f.status==='played'&&f.date).map(f=>new Date(`${f.date}T12:00:00Z`)).filter(d=>!Number.isNaN(+d)).sort((a,b)=>b-a);return played[0]||new Date();
  }
  function nearestRecoveryDate(data,at,saveDate,span=720){
    const view=new DataView(data.buffer,data.byteOffset,data.byteLength),start=Math.max(0,at-span),end=Math.min(data.length-4,at+span),min=+saveDate-3*86400000,max=+saveDate+550*86400000;let best=null,bestScore=Infinity;for(let off=start;off<=end;off++){const stamp=view.getUint16(off,true),year=view.getUint16(off+2,true),day=stamp&0x1ff;if(year<2020||year>2100||day<1||day>366)continue;const date=new Date(Date.UTC(year,0,day,12));if(+date<min||+date>max)continue;const score=Math.abs(off-at)+Math.max(0,(+date-(+saveDate+240*86400000))/86400000);if(score<bestScore){best=date;bestScore=score}}
    return best?best.toISOString().slice(0,10):null;
  }
  function decodeInjuryWindow(data,hit,latin,utf16){const start=Math.max(0,hit.at-90),end=Math.min(data.length,hit.at+360),wideStart=start-(start%2),clean=x=>x.replace(/[^\x20-\x7e]+/g,' ').replace(/\s+/g,' ').trim();return`${clean(latin.decode(data.subarray(start,end)))} ${clean(utf16.decode(data.subarray(wideStart,end-(end-wideStart)%2)))}`.trim()}
  async function addPlayerUids(gameDb,players,ids){
    if(!gameDb)return 0;const byEid=new Map(players.map(p=>[Number(p.pid??p.id),p]).filter(([n])=>Number.isInteger(n)&&n>0)),view=new DataView(gameDb.buffer,gameDb.byteOffset,gameDb.byteLength);let linked=0,zero=gameDb.indexOf(0),checks=0;while(zero>=0&&zero+15<=gameDb.length){if(gameDb[zero+1]===0&&gameDb[zero+2]===0){const eid=view.getUint32(zero+3,true),p=byEid.get(eid);if(p){const uid=view.getUint32(zero+7,true),uid2=view.getUint32(zero+11,true);if(uid&&uid!==0xffffffff&&uid===uid2){p.eid=String(eid);p.uid=String(uid);ids.set(uid,p);linked++;byEid.delete(eid);if(!byEid.size)break}}}zero=gameDb.indexOf(0,zero+1);if(++checks%350000===0)await new Promise(resolve=>setTimeout(resolve,0))}return linked;
  }
  async function binaryInjuryRecords(data,ids,saveDate,latin,utf16,limit=5000){
    const out=[],view=new DataView(data.buffer,data.byteOffset,data.byteLength),seen=new Set();let nextYield=1800000;for(let off=0;off+4<=data.length;off++){if(off>=nextYield){nextYield+=1800000;await new Promise(resolve=>setTimeout(resolve,0))}const id=view.getUint32(off,true),p=ids.get(id);if(!p)continue;const recovery=nearestRecoveryDate(data,off,saveDate,300);if(!recovery)continue;const key=`${p.pid??p.id}\u0000${recovery}`;if(seen.has(key))continue;seen.add(key);const text=decodeInjuryWindow(data,{at:off,wide:false},latin,utf16),label=injuryLabel(text);out.push({player:p,recovery,label,at:off,id});if(out.length>=limit)break;off+=3}return out;
  }
  async function enrichPayloadFromInjuryTables(file,payload){
    const existing=collectPayloadInjuries(payload),found=new Map(existing.map(x=>[String(x.pid||x.name).toLowerCase(),x]));if(!file||!payload?.players?.length)return payload;if(!window.fzstd){try{await FM_RUNTIME.ensure()}catch(e){payload.meta=payload.meta||{};payload.meta.injury_scan_error=`Parser runtime unavailable: ${String(e?.message||e)}`;return payload}}
    payload.meta=payload.meta||{};const diagnostics={archiveMembers:[],strongMembers:[],textHits:0,identityLinks:0,candidates:0,rejectedNoPlayer:0,rejectedExpired:0,decoded:0};
    try{
      const raw=await file.arrayBuffer(),b=new Uint8Array(raw),marker=new Uint8Array([2,1,102,109,102,46]),magicBytes=new Uint8Array([0x28,0xb5,0x2f,0xfd]),tail=b.subarray(Math.max(0,b.length-4000000)),rel=FM_RUNTIME.rfind(tail,marker),magic=FM_RUNTIME.find(tail,magicBytes,Math.max(0,rel+marker.length));if(rel<0||magic<0)return payload;
      const manifest=window.fzstd.decompress(tail.subarray(magic)),allItems=FM_RUNTIME.parseManifest(manifest).items,baseName=x=>String(x||'').split(/[\\/]/).pop().toLowerCase(),strongName=x=>/(injur|medical|health|unavail|condition|physio|absence|rehab|treat|availability|status)/i.test(x),items=allItems.filter(m=>m.plain>0&&m.plain<=268435456&&(strongName(m.name)||/^(game_db|news)\.dat$/i.test(baseName(m.name))));diagnostics.archiveMembers=items.map(x=>x.name);diagnostics.strongMembers=items.filter(x=>strongName(x.name)).map(x=>x.name);
      const ids=new Map();for(const p of payload.players)for(const key of ['pid','id','eid','uid']){const n=Number(p?.[key]);if(Number.isInteger(n)&&n>0&&n<=0xffffffff)ids.set(n,p)}
      const extract=item=>{const src=b.subarray(26+item.offset,26+item.offset+item.stored);return window.fzstd.decompress(src,new Uint8Array(item.plain))},gameItem=items.find(x=>baseName(x.name)==='game_db.dat');let gameDb=null;try{if(gameItem)gameDb=extract(gameItem)}catch(_e){}
      diagnostics.identityLinks=await addPlayerUids(gameDb,payload.players,ids);const latin=new TextDecoder('latin1'),utf16=new TextDecoder('utf-16le'),saveDate=inferredSaveDate(payload),scanItems=items.filter(x=>baseName(x.name)!=='game_db.dat');if(gameItem&&!diagnostics.strongMembers.length)scanItems.push(gameItem);
      for(const item of scanItems){let data;try{data=baseName(item.name)==='game_db.dat'?gameDb:extract(item)}catch(_e){continue}if(!data)continue;const strong=strongName(item.name),news=baseName(item.name)==='news.dat',span=strong?950:news?520:300,hits=injuryTextHits(data,strong?18000:7000);diagnostics.textHits+=hits.length;
        for(const hit of hits){diagnostics.candidates++;const link=nearestPlayerId(data,ids,hit.at,span);if(!link){diagnostics.rejectedNoPlayer++;continue}const text=decodeInjuryWindow(data,hit,latin,utf16),label=injuryLabel(text),recovery=nearestRecoveryDate(data,hit.at,saveDate,strong?900:480),distanceScore=link.distance<=48?3:link.distance<=180?2:1,dateScore=recovery?3:0,sourceScore=strong?5:news?2:0,termScore=label==='Injured'?2:3,score=distanceScore+dateScore+sourceScore+termScore;if((strong&&score<9)||(!strong&&score<10)){if(!recovery)diagnostics.rejectedExpired++;continue}
          const p=link.player,key=String(p.pid??p.id??playerName(p)).toLowerCase();if(found.has(key))continue;const detail=`Injured · ${label}${recovery?` · expected back ${typeof fmFmtStatusDate==='function'?fmFmtStatusDate(recovery):recovery}`:''}`;p.injured=true;p.injury_status=label;p.injury_name=label;if(recovery){p.injury_return_date=recovery;p.expected_return_date=recovery}const row={pid:String(p.pid??p.id??''),name:playerName(p),club:p.club,pos:p.pos,injury_status:label,expected_return_date:recovery,source:item.name,detail};found.set(key,row);diagnostics.decoded++}
        if(strong&&baseName(item.name)!=='game_db.dat'){const binary=await binaryInjuryRecords(data,ids,saveDate,latin,utf16);diagnostics.candidates+=binary.length;for(const candidate of binary){const p=candidate.player,key=String(p.pid??p.id??playerName(p)).toLowerCase();if(found.has(key))continue;const label=candidate.label,recovery=candidate.recovery,detail=`Injured · ${label}${recovery?` · expected back ${typeof fmFmtStatusDate==='function'?fmFmtStatusDate(recovery):recovery}`:''}`;p.injured=true;p.injury_status=label;p.injury_name=label;p.injury_return_date=recovery;p.expected_return_date=recovery;found.set(key,{pid:String(p.pid??p.id??''),name:playerName(p),club:p.club,pos:p.pos,injury_status:label,expected_return_date:recovery,source:item.name,detail});diagnostics.decoded++}}
        if(data!==gameDb)data=null;await new Promise(resolve=>setTimeout(resolve,0))
      }
      gameDb=null;payload.injuries=[...found.values()];payload.meta.injury_scan_version='binary-id-date-v2';payload.meta.injury_members_scanned=diagnostics.archiveMembers;payload.meta.injury_strong_members=diagnostics.strongMembers;payload.meta.injury_text_hits=diagnostics.textHits;payload.meta.injury_identity_links=diagnostics.identityLinks;payload.meta.injury_candidate_links=diagnostics.candidates;payload.meta.injury_candidates_without_player=diagnostics.rejectedNoPlayer;payload.meta.injury_candidates_without_active_date=diagnostics.rejectedExpired;payload.meta.injury_records_decoded=payload.injuries.length;payload.meta.injury_new_records=diagnostics.decoded;if(typeof fmDebugAdd==='function')fmDebugAdd(payload.injuries.length?'info':'warning',payload.injuries.length?`Decoded ${payload.injuries.length} active injur${payload.injuries.length===1?'y':'ies'} from the FM save.`:`No active injuries decoded. Scanned ${diagnostics.archiveMembers.length} availability candidates (${diagnostics.strongMembers.length} dedicated table${diagnostics.strongMembers.length===1?'':'s'}).`,diagnostics);
    }catch(e){payload.meta.injury_scan_error=String(e?.message||e);if(typeof fmDebugAdd==='function')fmDebugAdd('warning','FM injury table enrichment failed',{message:String(e?.message||e),stack:String(e?.stack||'')});console.warn('FM injury table enrichment skipped',e)}
    payload.injuries=payload.injuries||[...found.values()];payload.meta.injury_records_decoded=payload.injuries.length;return payload;
  }
  function installInjuryImport(){
    try{if(FM_RUNTIME.__fmInjuryWrapped)return;FM_RUNTIME.__fmInjuryWrapped=true;const original=FM_RUNTIME.importFile.bind(FM_RUNTIME);FM_RUNTIME.importFile=async function(file,...args){const result=await original(file,...args);if(result?.payload){await enrichPayloadFromInjuryTables(file,result.payload);return result}if(result?.duplicate&&typeof fmStoredGet==='function'){const cached=await fmStoredGet();if(cached){await enrichPayloadFromInjuryTables(file,cached);return{...result,duplicate:false,payload:cached,injuryRefreshOnly:true}}}return result};const inferBase=fmInferActiveInjuries;fmInferActiveInjuries=function(payload){const merged=[...inferBase(payload),...collectPayloadInjuries(payload)],seen=new Set();return merged.filter(x=>{const k=String(x.pid||x.name).toLowerCase();if(seen.has(k))return false;seen.add(k);return true})}}catch(e){console.warn('Could not install injury import enrichment',e)}
  }

  function enhanceConceptComponents(){wireComparison();updateIdentity();resetPageFit()}
  function boot(){addFinalStyles();installStableFit();installOwnMemberIdentity();installStarAll();installInjuryImport();enhanceConceptComponents();const body=byId('compareBody');if(body)new MutationObserver(wireComparison).observe(body,{childList:true,subtree:true});let queued=0;new MutationObserver(()=>{cancelAnimationFrame(queued);queued=requestAnimationFrame(enhanceConceptComponents)}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',()=>requestAnimationFrame(enhanceConceptComponents),true);window.addEventListener('resize',resetPageFit);window.addEventListener('fmcloudready',enhanceConceptComponents)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
