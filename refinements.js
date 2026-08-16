(()=>{
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const norm=v=>clean(v).toLocaleLowerCase('en-GB').normalize('NFKD').replace(/[\u0300-\u036f]/g,'');

  function addStyles(){
    if($('fmDesktopRefinementStyles'))return;
    const s=document.createElement('style');s.id='fmDesktopRefinementStyles';s.textContent=`
      /* The desktop type scale is intentional at first paint: primary identity first,
         secondary club/form copy second. */
      #statsPage .statsWorkspace{grid-template-rows:44px 74px minmax(0,1fr) clamp(198px,22vh,218px)!important;gap:8px!important}
      #statsPage .statsToolbar{padding:6px 11px 6px 14px!important}
      #statsPage .statsHeroCard{padding:8px 12px!important}
      #statsPage .statsHeroCard small{font-size:7px!important}
      #statsPage .statsHeroCard span{margin-top:3px!important;color:#f4edf9!important;font-size:9.5px!important;font-weight:850!important;line-height:1.15!important}
      #statsPage .statsHeroCard em{margin-top:2px!important;color:#8d819d!important;font-size:6.5px!important;line-height:1.15!important}
      #statsPage .statRow .nm{color:#f8f3fc!important;font-size:8.7px!important;line-height:1.12!important;font-weight:900!important}
      #statsPage .statRow .sub{color:#81758f!important;font-size:6.2px!important;line-height:1.08!important;font-weight:600!important}
      #statsPage .statsBottom{grid-template-columns:minmax(0,1fr) 252px!important;gap:7px!important}
      #statsPage .statsBottom>.card{display:grid!important;grid-template-rows:29px minmax(0,1fr)!important;min-height:0!important}
      #statsPage .statsBottom .statsCardHead{height:29px!important;min-height:29px!important;padding:5px 9px!important}
      #statsPage .statsBottom .statsCardHead small{display:none!important}
      #statsPage #statsInsights{height:auto!important;min-height:0!important;gap:7px!important;padding:8px!important}
      #statsPage .insightCard{counter-reset:insightRank!important;min-height:0!important;padding:8px!important}
      #statsPage .insightCard>b{font-size:9px!important}
      #statsPage .insightCard>small{margin:2px 0 6px!important;font-size:6.5px!important}
      #statsPage .insightLine{grid-template-columns:16px minmax(0,1fr) 48px 28px!important;gap:5px!important;margin-top:6px!important;font-size:7.4px!important;line-height:1!important}
      #statsPage .insightLine:before{width:15px!important;height:15px!important;font-size:6.5px!important;border-radius:4px!important}
      #statsPage .insightBar{height:5px!important}
      #statsPage #statsHighlights{height:auto!important;min-height:0!important;padding:6px 9px!important}
      #statsPage .highlightRow{min-height:35px!important}
      #statsPage .highlightRow b{font-size:8px!important}
      #statsPage .highlightRow span{font-size:6px!important}

      /* Rules retain the clearer hierarchy without producing a page scrollbar. */
      @media(min-width:1181px){
        #rulesPage.active{height:calc(100vh - 119px)!important;overflow:hidden!important}
        #rulesPage .rulesConceptGrid{height:calc(100% - 22px)!important;grid-template-rows:repeat(3,minmax(0,1fr))!important;gap:7px!important}
        #rulesPage .ruleConcept{min-height:0!important;padding:9px 10px!important;overflow:hidden!important}
        #rulesPage .ruleTitle{gap:8px!important;margin-bottom:7px!important}
        #rulesPage .ruleTitle>span{width:22px!important;height:22px!important;flex-basis:22px!important;font-size:10px!important}
        #rulesPage .ruleTitle h2{font-size:13px!important;line-height:1.12!important}
        #rulesPage .ruleTitle p{font-size:8px!important;line-height:1.32!important}
        #rulesPage .ruleScoringTop,#rulesPage .ruleTwin,#rulesPage .ruleThirds,#rulesPage .ruleFour{gap:7px!important}
        #rulesPage .ruleMini,#rulesPage .ruleStrip{min-height:56px!important;gap:8px!important;padding:8px 9px!important}
        #rulesPage .ruleMini>i,#rulesPage .ruleStrip>i{width:30px!important;height:30px!important;flex-basis:30px!important;font-size:12px!important}
        #rulesPage .ruleMini b,#rulesPage .ruleStrip b{margin-bottom:3px!important;font-size:8.7px!important;line-height:1.18!important}
        #rulesPage .ruleMini p,#rulesPage .ruleStrip p{font-size:8px!important;line-height:1.34!important}
        #rulesPage .ruleGoalRows{font-size:8px!important;line-height:1.28!important}
        #rulesPage .ruleScoring .ruleTwin{margin-top:7px!important}
        #rulesPage .ruleInfo{min-height:32px!important;margin-top:7px!important;padding:7px 9px!important;font-size:7.5px!important;line-height:1.32!important}
        #rulesPage .rulesFooter{height:20px!important;padding:4px 4px 0!important;font-size:7px!important}
      }

      /* Fixtures: a compact filter rail leaves room for the calendar and the list owns
         its scroll, including the new all-Gameweeks grouping. */
      #fixturesPage .fixtureRail{grid-template-rows:236px minmax(0,1fr)!important;gap:9px!important}
      #fixturesPage .fixtureRailHead{min-height:37px!important;padding:7px 11px!important}
      #fixturesPage .fixtureFilters>label{margin:6px 11px 3px!important;font-size:7px!important}
      #fixturesPage .fixtureFilters>.ctrl{width:calc(100% - 22px)!important;height:28px!important;margin:0 11px!important;padding:5px 8px!important;font-size:8px!important}
      #fixturesPage .fixtureChecks{gap:4px!important;margin:7px 11px!important}
      #fixturesPage .fixtureChecks label{gap:6px!important;font-size:7.5px!important;line-height:1.15!important}
      #fixturesPage .fixtureChecks input{width:11px!important;height:11px!important}
      #fixturesPage .fixtureReset{padding:4px 7px!important;font-size:6.5px!important}
      #fixturesPage .fixtureAllRound{margin:7px 4px 2px;padding:7px 8px 4px;border-top:1px solid rgba(255,255,255,.08);color:#e5daf0;font-size:9px;font-weight:900;letter-spacing:.01em}

      /* Separate Star XI aggregate action and align every pitch navigator consistently. */
      #teamPage .pitchTopControls,#starPage .pitchTopControls{right:1.4%!important;display:flex!important;align-items:center!important;justify-content:flex-end!important;gap:6px!important}
      #starAllToggle{order:2!important;margin:0!important;min-width:45px!important;height:29px!important;border-radius:8px!important;pointer-events:auto!important}
      #starPage .pitchTopControls>.gwNav{order:1!important}

      /* Transfer list hierarchy: club column is the club identity, the first column is
         reserved for the player. */
      #transfersPage .prow .pinfo .nm{font-size:9px!important;line-height:1.12!important;font-weight:900!important}
      #transfersPage .prow .pinfo .sub{font-size:6.2px!important;color:#827790!important}
      #transfersPage .prow>div:nth-child(2){font-size:10px!important;line-height:1.15!important;font-weight:850!important;color:#f0e9f7!important}

      /* League crest selection. */
      .fmLeagueIconPicker{margin-top:10px;padding:10px;border:1px solid rgba(206,119,237,.18);border-radius:10px;background:#130b30}
      .fmLeagueIconPicker>small{display:block;margin-bottom:7px;color:#a99abd;font-size:8px;font-weight:800}
      .fmLeagueIconChoices{display:grid;grid-template-columns:repeat(6,1fr);gap:6px}
      .fmLeagueIconChoice{display:grid;place-items:center;height:39px;border:1px solid rgba(255,255,255,.1);border-radius:9px;color:#eadff5;background:#241447;font-size:20px;cursor:pointer}
      .fmLeagueIconChoice:hover,.fmLeagueIconChoice.active{border-color:#f04eb0;color:#fff;background:linear-gradient(145deg,#8b246e,#4c216e);box-shadow:0 0 0 2px rgba(240,78,176,.12)}
      #leagueModal .fmLeagueIconPicker{margin:0 0 14px}
    `;document.head.appendChild(s);
  }

  /* Public football names are a presentation field only. Player ids and legal names
     remain untouched for imports, joins, history and scoring. */
  const exactPublicNames=new Map([
    ['24517','Taty Castellanos'],
    ['valentin mariano jose castellanos gimenez','Taty Castellanos']
  ]);
  let aliasSignature='',matchAliases=new Map();
  function rebuildMatchAliases(){
    const matches=typeof MATCHES!=='undefined'&&Array.isArray(MATCHES)?MATCHES:[],sig=`${matches.length}:${matches.reduce((n,m)=>n+(m?.home_players?.length||0)+(m?.away_players?.length||0),0)}`;if(sig===aliasSignature)return;aliasSignature=sig;
    const counts=new Map();for(const m of matches)for(const key of ['home_players','away_players'])for(const r of (m?.[key]||[])){const id=clean(r?.player_id??r?.pid??r?.id),name=clean(r?.display_name??r?.known_as??r?.name);if(!id||!name||name.split(/\s+/).length>4)continue;const k=`${id}\u0000${name}`,n=counts.get(k)||0;counts.set(k,n+1)}
    matchAliases=new Map();for(const [key,count] of counts){const [id,name]=key.split('\u0000'),old=matchAliases.get(id);if(!old||count>old.count)matchAliases.set(id,{name,count})}
  }
  function publicPlayerName(p){
    if(!p)return'Unknown';rebuildMatchAliases();
    const ids=[p.pid,p.player_id,p.id,p.eid,p.uid].map(clean).filter(Boolean),legal=clean(p.legal_full_name||p.full_name||p.name),legalNorm=norm(legal);
    for(const id of ids)if(exactPublicNames.has(id))return exactPublicNames.get(id);if(exactPublicNames.has(legalNorm))return exactPublicNames.get(legalNorm);
    const surname=clean(p.football_surname||p.surname||p.family_name||p.last_name),preferred=clean(p.preferred_name||p.known_as||p.common_name||p.nickname),explicit=clean(p.canonical_display_name||p.public_name||p.football_display_name);
    if(explicit&&norm(explicit)!==legalNorm)return explicit;
    if(preferred){if(!surname||norm(preferred)===norm(surname)||preferred.split(/\s+/).some(x=>norm(x)===norm(surname)))return preferred;if(preferred.split(/\s+/).length>1)return preferred;return `${preferred} ${surname}`}
    for(const id of ids){const alias=matchAliases.get(id)?.name;if(alias&&norm(alias)!==legalNorm&&(alias.split(/\s+/).length<legal.split(/\s+/).length||!legal))return alias}
    const display=clean(p.display_name);if(display&&norm(display)!==legalNorm&&(display.split(/\s+/).length<=3||!legal))return display;
    const first=clean(p.first_name||p.forename);if(first&&surname)return `${first} ${surname}`;
    return legal||display||'Unknown';
  }
  function installPublicNames(){
    try{playerName=publicPlayerName;playerCardName=publicPlayerName;fmCanonicalPlayerName=publicPlayerName}catch(e){console.warn('Public player names could not be installed',e)}
  }

  function installTransferRows(){
    try{marketPlayerRow=function(p){return `<div class="prow" data-open-player="${esc(p.id)}"><div class="pinfo"><div class="round">${esc(typeof initials==='function'?initials(playerName(p)):playerName(p).slice(0,2))}</div><div><div class="nm">${esc(playerName(p))}${typeof playerStatusBadge==='function'?playerStatusBadge(p):''}</div><div class="sub">${Number(p.form_points||p.form||0)} form</div></div></div><div>${esc(p.club)}</div><div><span class="pospill">${esc(p.pos)}</span></div><div class="price">£${Number(p.price||0).toFixed(1)}m</div><div>${Number(p.fantasy_points||0)}</div><div>${state.squad.includes(p.id)?`<button class="add" data-remove="${esc(p.id)}">−</button>`:`<button class="add" data-add="${esc(p.id)}" ${canAdd(p)?'':'disabled'}>+</button>`}</div></div>`}}catch(e){console.warn('Transfer row hierarchy could not be installed',e)}
  }

  function fixtureDetail(f){
    const m=f.match_id?MATCHES.find(x=>String(x.id)===String(f.match_id)):null;if(m){const e=matchEvents(m);return `<div class="fixtureDetail"><div class="eventGrid">${eventBox('Goals',e.goals)}${eventBox('Assists',e.assists)}${eventBox('Yellow / red cards',e.cards)}${eventBox('Goalkeeper saves',e.saves)}${eventBox('DEFCON',e.defcon)}${eventBox('Bonus / BPS',e.bonus)}</div>${m.score_note?`<div class="ruleNote">${esc(m.score_note)}</div>`:''}</div>`}
    return `<div class="fixtureDetail"><div class="infoBox"><b>${f.status==='future'?'Fixture not played yet':'Detailed match record unavailable'}</b><div class="muted" style="margin-top:5px">${f.status==='future'?`Scheduled kick-off: ${fixtureKickoffTime(f)}.`:'The fixture is retained without inventing missing player-level match detail.'}</div></div></div>`;
  }
  function fixtureRow(f,doubleSet){
    const time=fixtureKickoffTime(f),post=f.status==='postponed',result=f.status==='played'?`${f.home_score} – ${f.away_score}`:f.status==='undecoded'?'—':time,cls=f.status==='played'?'played':post?'postponed':f.status==='undecoded'?'unknown':f.calendar_reassigned?'moved':'',sub=f.status==='played'?'Full time':post?'Postponed':f.status==='undecoded'?'Result pending':f.calendar_reassigned?'Rescheduled':'Kick-off',marker=doubleSet.has(`${f.gameweek}\u0000${f.home}`)||doubleSet.has(`${f.gameweek}\u0000${f.away}`)?'D':f.calendar_reassigned?'R':'';
    return `<div class="fixtureConcept"${f.match_id?` data-match="${esc(f.match_id)}"`:''}><div class="fixtureHead"><div class="fixtureGWChip">GW ${Number(f.gameweek)}</div><div class="fixtureKickoff">${esc(time)}</div><div class="fixtureTeam home">${esc(f.home)}</div><div class="fixtureBadge">${clubBadge(f.home)}</div><div class="fixtureResult ${cls}">${esc(result)}<small>${sub}</small></div><div class="fixtureBadge">${clubBadge(f.away)}</div><div class="fixtureTeam away">${esc(f.away)}</div><div class="fixtureChevron">${marker?`<span class="fixtureMarker">${marker}</span>`:'⌄'}</div></div>${fixtureDetail(f)}</div>`;
  }
  function renderAllFixtures(){
    const club=$('fixtureClub')?.value||'',all=[...(SEASON_FIXTURES||[])].sort((a,b)=>Number(a.gameweek)-Number(b.gameweek)||String(a.date||'').localeCompare(String(b.date||''))||String(a.home||'').localeCompare(String(b.home||''))),appearance=new Map();
    for(const f of all)for(const c of [f.home,f.away]){const k=`${f.gameweek}\u0000${c}`;appearance.set(k,(appearance.get(k)||0)+1)}const doubles=new Set([...appearance].filter(([,n])=>n>1).map(([k])=>k));
    let arr=all.filter(f=>!club||f.home===club||f.away===club);if(!$('fixtureShowDoubles')?.checked)arr=arr.filter(f=>!doubles.has(`${f.gameweek}\u0000${f.home}`)&&!doubles.has(`${f.gameweek}\u0000${f.away}`));if(!$('fixtureShowRescheduled')?.checked)arr=arr.filter(f=>!f.calendar_reassigned);if(!$('fixtureShowPostponed')?.checked)arr=arr.filter(f=>f.status!=='postponed');
    $('fixturePrevGW').disabled=true;$('fixtureNextGW').disabled=true;$('fixtureSummaryGW').textContent='All';$('fixtureSummaryCount').textContent=`${arr.length} fixture${arr.length===1?'':'s'}`;$('fixtureDoubleValue').textContent=doubles.size;$('fixtureBlankValue').textContent='—';$('fixtureRescheduledValue').textContent=arr.filter(f=>f.calendar_reassigned).length;$('fixtureListTitle').textContent=club?`${club} Fixtures`:'All Fixtures';$('fixtureGWLabel').textContent='All Gameweeks';$('fixtureDateRange').textContent=club?'Full club schedule':'Full season schedule';$('fixtureRoundMeta').textContent=`${arr.length} matching fixtures · Gameweeks 1–${seasonGWMax()}`;
    if($('fixtureCalendar'))$('fixtureCalendar').innerHTML=fixtureCalendarHTML(all.filter(f=>Number(f.gameweek)===Number(state.currentGameweek||META.current_gameweek||1)));
    const byGw=new Map();for(const f of arr){const gw=Number(f.gameweek)||0;if(!byGw.has(gw))byGw.set(gw,[]);byGw.get(gw).push(f)}
    $('fixtureRows').innerHTML=[...byGw].map(([gw,fixtures])=>{const byDate=new Map();for(const f of fixtures){const k=f.date||'Date TBC';if(!byDate.has(k))byDate.set(k,[]);byDate.get(k).push(f)}const days=[...byDate].map(([date,rows])=>{const d=fixtureDateObject(date),heading=d?d.toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'}):'Date to be confirmed';return `<div class="fixtureDay">${heading}<span>${rows.length} fixture${rows.length===1?'':'s'}</span></div>${rows.map(f=>fixtureRow(f,doubles)).join('')}`}).join('');return `<div class="fixtureAllRound">Gameweek ${gw}</div>${days}`}).join('')||'<div class="blankGW"><b>No matching fixtures</b>Change the club or availability filters.</div>';
  }
  function addAllFixtureOption(){const sel=$('fixtureGW');if(!sel||sel.querySelector('option[value="all"]'))return;const o=document.createElement('option');o.value='all';o.textContent='All Gameweeks';sel.insertBefore(o,sel.firstChild)}
  function installAllFixtures(){
    try{
      const baseRender=renderFixtures,baseRefresh=refreshCompetitionUI;refreshCompetitionUI=function(){const all=$('fixtureGW')?.value==='all';baseRefresh();addAllFixtureOption();if(all)$('fixtureGW').value='all'};renderFixtures=function(){addAllFixtureOption();if($('fixtureGW')?.value==='all')return renderAllFixtures();return baseRender()};
      addAllFixtureOption();$('fixtureGW').onchange=()=>{if($('fixtureGW').value!=='all')fixtureViewGW=Number($('fixtureGW').value);renderFixtures()};$('fixtureClub').onchange=renderFixtures;$('fixtureReset').onclick=()=>{$('fixtureClub').value='';for(const id of ['fixtureShowDoubles','fixtureShowBlanks','fixtureShowRescheduled','fixtureShowPostponed'])$(id).checked=true;fixtureViewGW=Math.max(1,state.currentGameweek||META.current_gameweek||1);$('fixtureGW').value=String(fixtureViewGW);renderFixtures()};$('fixturePrevGW').onclick=()=>{if($('fixtureGW').value==='all')fixtureViewGW=Math.max(1,Number(state.currentGameweek||META.current_gameweek||1));else fixtureViewGW=Math.max(1,fixtureViewGW-1);$('fixtureGW').value=String(fixtureViewGW);renderFixtures()};$('fixtureNextGW').onclick=()=>{if($('fixtureGW').value==='all')fixtureViewGW=Math.max(1,Number(state.currentGameweek||META.current_gameweek||1));else fixtureViewGW=Math.min(seasonGWMax(),fixtureViewGW+1);$('fixtureGW').value=String(fixtureViewGW);renderFixtures()};
    }catch(e){console.warn('All-fixtures view could not be installed',e)}
  }

  const leagueIcons=['★','♜','♛','⚽','◆','✦'];let createLeagueIcon='★';
  function iconPicker(current,index){return `<div class="fmLeagueIconPicker"${index==null?'':' data-league-icon-index="'+index+'"'}><small>League badge</small><div class="fmLeagueIconChoices">${leagueIcons.map(icon=>`<button type="button" class="fmLeagueIconChoice${icon===current?' active':''}" data-league-icon="${esc(icon)}">${icon}</button>`).join('')}</div></div>`}
  function paintLeagueIcons(){if(typeof state==='undefined')return;document.querySelectorAll('#leaguesPage [data-league]').forEach(root=>{const i=Number(root.dataset.league),icon=state.leagues?.[i]?.icon||'★';const target=root.querySelector('.leagueTileIcon,.featuredCrest');if(target)target.textContent=icon});if(state.leagues?.length===1){const c=document.querySelector('#leaguesPage .leagueSingleCrest');if(c)c.textContent=state.leagues[0].icon||'★'}}
  function installLeagueIcons(){
    try{
      const body=$('createLeagueModal')?.querySelector('.modalBody');if(body&&!$('fmCreateLeagueIconPicker')){const host=document.createElement('div');host.id='fmCreateLeagueIconPicker';host.innerHTML=iconPicker(createLeagueIcon);body.insertBefore(host,$('confirmCreateLeague'))}
      $('confirmCreateLeague').onclick=()=>{const name=$('leagueNameInput').value.trim();if(!name)return;const code=Math.random().toString(36).slice(2,8).toUpperCase();state.leagues.push({name,code,icon:createLeagueIcon,members:[ownMember()]});$('leagueNameInput').value='';$('createLeagueModal').classList.remove('show');save();renderLeagues();paintLeagueIcons()};
      const baseRender=renderLeagues;renderLeagues=function(){baseRender();paintLeagueIcons()};
      const baseOpen=openLeague;openLeague=function(i){baseOpen(i);const body=$('leagueBody');if(!body)return;body.insertAdjacentHTML('afterbegin',iconPicker(state.leagues?.[i]?.icon||'★',i))};
      document.addEventListener('click',e=>{const b=e.target.closest('[data-league-icon]');if(!b)return;e.preventDefault();e.stopPropagation();const picker=b.closest('.fmLeagueIconPicker'),icon=b.dataset.leagueIcon;picker.querySelectorAll('.fmLeagueIconChoice').forEach(x=>x.classList.toggle('active',x===b));const index=picker.dataset.leagueIconIndex;if(index==null){createLeagueIcon=icon;return}const n=Number(index);if(state.leagues?.[n]){state.leagues[n].icon=icon;save();paintLeagueIcons()}},true);
      paintLeagueIcons();
    }catch(e){console.warn('League badge choices could not be installed',e)}
  }

  function refreshVisible(){
    try{if(typeof renderStats==='function'&&$('statsPage')?.classList.contains('active'))renderStats();if(typeof renderMarket==='function'&&$('transfersPage')?.classList.contains('active'))renderMarket();if(typeof renderTeam==='function'&&$('teamPage')?.classList.contains('active'))renderTeam();if(typeof renderStar==='function'&&$('starPage')?.classList.contains('active'))renderStar()}catch(e){console.warn('Visible page refresh skipped',e)}
  }
  function fixTeamSummaryLabel(){const label=$('teamGWSum')?.closest('.sum')?.querySelector('small');if(label)label.textContent='Gameweek'}
  function loadMobileLayer(){if(document.querySelector('script[data-fm-mobile]'))return;const s=document.createElement('script');s.src='./mobile.js?v=4';s.dataset.fmMobile='true';document.head.appendChild(s)}
  function boot(){addStyles();installPublicNames();installTransferRows();installAllFixtures();installLeagueIcons();fixTeamSummaryLabel();loadMobileLayer();requestAnimationFrame(refreshVisible);setTimeout(()=>{fixTeamSummaryLabel();refreshVisible()},120)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  window.addEventListener('fmcloudready',()=>{aliasSignature='';installPublicNames();addAllFixtureOption();fixTeamSummaryLabel();requestAnimationFrame(refreshVisible)});
})();
