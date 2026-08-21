(()=>{
'use strict';
const VERSION='registration-news-v4-canonical-render-arrival-diff';
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const sid=p=>String(p?.pid??p?.player_id??p?.person_id??p?.eid??p?.id??'');
const club=p=>String(p?.club||p?.club_full||p?.team||'').trim();
const label=p=>String(p?.display_name||p?.public_name||p?.name||p?.legal_name||'Player').trim();
const visible=p=>!!p&&p.visible!==false&&p.competition_eligible!==false;
const cohort=p=>!!p&&p?.registration_evidence?.cohort_eligible===true;
const hkey=h=>[h?.date,h?.gameweek,h?.match_id,h?.home,h?.away].map(x=>String(x??'')).join('|');
function newHistoryRows(oldP,newP,oldSnapshot){const seen=new Set(arr(oldP?.history).map(hkey));return arr(newP?.history).filter(h=>!seen.has(hkey(h))&&(!oldSnapshot||String(h?.date||'')>String(oldSnapshot)))}
function candidateId(row,nextByName){let id=String(row?.pid??row?.player_id??row?.person_id??row?.id??'');if(id)return id;const n=norm(row?.name||row?.display_name||'');if(!n)return '';const ids=nextByName.get(n)||[];return ids.length===1?ids[0]:''}
function priorClubHint(p){for(const k of ['previous_club','previousClub','loan_parent_club','loanParentClub','parent_club','parentClub','loan_from','from_club','fromClub']){const v=String(p?.[k]||'').trim();if(v)return v}return 'Outside league'}
function buildEvidence(next,old){
 const mode=norm(next?.meta?.import_mode||window.__FM_IMPORT_MODE_ACTIVE||'');
 const oldSnapshot=String(old?.meta?.snapshot_date||''),newSnapshot=String(next?.meta?.snapshot_date||'');
 const oldById=new Map(arr(old?.players).map(p=>[sid(p),p]).filter(([id])=>id));
 const nextById=new Map(arr(next?.players).map(p=>[sid(p),p]).filter(([id])=>id));
 const nextByName=new Map();for(const [id,p] of nextById){const n=norm(label(p));if(!n)continue;const ids=nextByName.get(n)||[];ids.push(id);nextByName.set(n,ids)}
 const registrationEvents=[],directTransfers=[];
 if(mode!=='season')for(const p of arr(next?.players)){
   const id=sid(p);if(!id)continue;const prev=oldById.get(id)||null;
   const oldVisible=visible(prev),newVisible=visible(p),oldCohort=cohort(prev),newCohort=cohort(p),rows=newHistoryRows(prev,p,oldSnapshot);
   const oldClub=club(prev),newClub=club(p);
   if(prev&&oldVisible&&newVisible&&oldClub&&newClub&&norm(oldClub)!==norm(newClub))directTransfers.push({id,name:label(p),old_club:oldClub,new_club:newClub,date:rows[0]?.date||newSnapshot||null,source:'canonical_club_change'});
   let kind=null,reason=null;
   if(newVisible&&!oldVisible){if(newCohort&&!oldCohort){kind='registration';reason='New Championship registration'}else if(rows.length){kind='senior_matchday';reason='Added after Championship senior matchday involvement'}}
   else if(newVisible&&oldVisible&&newCohort&&!oldCohort){kind='registration';reason='New Championship registration'}
   if(kind)registrationEvents.push({id,name:label(p),club:newClub||oldClub||'',kind,reason,date:rows[0]?.date||newSnapshot||null});
 }
 const regById=new Map(registrationEvents.map(e=>[String(e.id),e]));
 const inferredArrivals=[];
 for(const reg of registrationEvents){
   const id=String(reg?.id||''),p=nextById.get(id);if(!id||!p||oldById.has(id)||reg?.kind!=='registration')continue;
   const newClub=club(p);if(!newClub)continue;
   inferredArrivals.push({id,name:label(p),old_club:priorClubHint(p),new_club:newClub,date:reg?.date||newSnapshot||null,source:'canonical_new_registration_arrival'});
 }
 const rawCandidates=arr(next?.meta?._transfer_news_candidates_v3),arrivalTransfers=[];let candidateAccepted=0,candidateRejected=0;
 for(const row of rawCandidates){
   const id=candidateId(row,nextByName),p=nextById.get(id),prev=oldById.get(id)||null;if(!id||!p||!visible(p)){candidateRejected++;continue}
   const newClub=club(p),claimedNew=String(row?.new_club||row?.to||row?.club||'').trim();if(!newClub||(claimedNew&&norm(claimedNew)!==norm(newClub))){candidateRejected++;continue}
   const prevClub=club(prev),oldClub=String(row?.old_club||row?.from||row?.previous_club||prevClub||priorClubHint(p)).trim()||'Outside league';
   if(norm(oldClub)===norm(newClub)){candidateRejected++;continue}
   const reg=regById.get(id)||null,direct=!!(prev&&visible(prev)&&prevClub&&norm(prevClub)!==norm(newClub));
   if(!direct&&!reg){candidateRejected++;continue}
   let date=String(row?.date||row?.transfer_date||reg?.date||newSnapshot||'').slice(0,10)||null;if(date&&oldSnapshot&&date<=oldSnapshot){candidateRejected++;continue}
   arrivalTransfers.push({id,name:label(p),old_club:direct?prevClub:oldClub,new_club:newClub,date,source:direct?'canonical_club_change':'validated_import_arrival'});candidateAccepted++;
 }
 const chosen=new Map();
 const put=(e,priority)=>{const k=`${e.id}|${norm(e.new_club)}`;const prev=chosen.get(k);if(!prev||priority>=prev.priority)chosen.set(k,{priority,event:e})};
 inferredArrivals.forEach(e=>put(e,1));directTransfers.forEach(e=>put(e,3));arrivalTransfers.forEach(e=>put(e,4));
 const transfers=[...chosen.values()].map(x=>x.event);
 next.meta=next.meta||{};delete next.meta._transfer_news_candidates_v3;
 next.meta.transfer_news_policy='successful-update only: canonical visible club changes, validated import candidates, plus newly-added canonical Championship registrations absent from the previous payload';
 next.meta.transfer_news_guard={version:VERSION,old_snapshot:oldSnapshot||null,new_snapshot:newSnapshot||null,events:transfers,candidate_rows_seen:rawCandidates.length,candidate_rows_accepted:candidateAccepted,candidate_rows_rejected:candidateRejected,inferred_new_registration_arrivals:inferredArrivals.length,direct_canonical_club_changes:directTransfers.length};
 next.meta.registration_news={version:VERSION,old_snapshot:oldSnapshot||null,new_snapshot:newSnapshot||null,events:registrationEvents};
 return {transfers,registrationEvents};
}
function installPublishGuard(){const c=window.FMCloud;if(!c||c.__registrationNewsV4||typeof c.publishWorld!=='function')return false;c.__registrationNewsV4=true;c.__registrationNewsV3=true;const original=c.publishWorld.bind(c);c.publishWorld=async(payload,...args)=>{if(!payload)return original(payload,...args);const old=JSON.parse(JSON.stringify(c.getWorld?.()?.payload||null));buildEvidence(payload,old);return original(payload,...args)};return true}
function currentPayload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function currentPlayers(){return new Map(arr(currentPayload()?.players).map(p=>[sid(p),p]).filter(([id])=>id))}
function transferEvents(){return arr(currentPayload()?.meta?.transfer_news_guard?.events)}
function registrationEvents(){return arr(currentPayload()?.meta?.registration_news?.events)}
function activateNews(){try{if(currentPayload())window.FMNewsView?.markActive?.()}catch(_e){}}
function ensureTransferHost(root=document){const card=root.querySelector?.('#newsTransfers');if(!card)return null;let host=card.querySelector('.fmCanonicalTransferRows');if(host)return {card,host};host=document.createElement('div');host.className='fmCanonicalTransferRows';const search=card.querySelector('[data-news-search]'),head=card.querySelector('.newsHead');(search||head)?.insertAdjacentElement('afterend',host);if(!host.parentElement)card.appendChild(host);return {card,host}}
function renderTransfers(root=document){const got=ensureTransferHost(root);if(!got)return;const {card,host}=got,events=transferEvents(),byId=currentPlayers(),sig=JSON.stringify(events.map(e=>[e?.id,e?.old_club,e?.new_club,e?.date]));if(host.dataset.fmSig===sig)return;host.dataset.fmSig=sig;for(const row of card.querySelectorAll('[data-news-text],.transfer'))if(!row.closest('.fmCanonicalTransferRows'))row.style.display='none';host.replaceChildren();if(!events.length){const empty=document.createElement('div');empty.className='fmNewsCanonicalEmpty';empty.textContent='No confirmed transfers since the last successful database update.';host.appendChild(empty)}else{events.forEach((e,i)=>{const p=byId.get(String(e?.id||''))||null,row=document.createElement('div');row.className='fmNewsTransferRow transfer';row.dataset.newsText='1';if(i>=6)row.classList.add('newsHidden');row.innerHTML='<span class="fmNewsMove"></span><span class="fmNewsName"></span><span class="fmNewsPrice"></span><span class="fmNewsDate"></span>';row.children[0].textContent=`${e?.old_club||'Outside league'} → ${e?.new_club||p?.club||'—'}`;row.children[1].textContent=e?.name||label(p);row.children[2].textContent=Number.isFinite(Number(p?.price))?`£${Number(p.price).toFixed(1)}m`:'';row.children[3].textContent=e?.date||'';host.appendChild(row)});if(events.length>6){const b=document.createElement('button');b.type='button';b.className='fmCanonicalNewsToggle';b.dataset.newsToggle='fmCanonicalTransfersFull';b.textContent=`View all ${events.length}`;host.appendChild(b)}}const baseToggle=card.querySelector('[data-news-toggle]:not(.fmCanonicalNewsToggle)');if(baseToggle)baseToggle.style.display='none'}
function ensureRegistrationCard(root=document){let card=root.querySelector?.('#newsRegistrations');if(card)return card;const transfers=root.querySelector?.('#newsTransfers'),page=root.querySelector?.('#newsPage,[data-page="news"],.newsPage');if(!transfers&&!page)return null;card=document.createElement('section');card.id='newsRegistrations';card.className=transfers?.className||'newsCard';card.innerHTML='<div class="newsHead"><div><div class="newsRegEyebrow">PLAYER POOL</div><h3>New registrations</h3></div></div><input class="ctrl newsSearch" data-news-search placeholder="Filter by club"><div class="newsRegRows"></div>';if(transfers)transfers.insertAdjacentElement('afterend',card);else page.appendChild(card);return card}
function renderRegistrations(root=document){const card=ensureRegistrationCard(root);if(!card)return;const rows=card.querySelector('.newsRegRows'),events=registrationEvents(),sig=JSON.stringify(events.map(e=>[e?.id,e?.club,e?.kind,e?.date]));if(rows.dataset.fmSig===sig)return;rows.dataset.fmSig=sig;rows.replaceChildren();if(!events.length){const empty=document.createElement('div');empty.className='fmNewsCanonicalEmpty';empty.textContent='No new registrations since the last successful database update.';rows.appendChild(empty);return}for(const [i,e] of events.entries()){const row=document.createElement('div');row.className='newsRegRow';row.dataset.newsText='1';if(i>=6)row.classList.add('newsHidden');row.innerHTML='<span class="newsRegClub"></span><span class="newsRegName"></span><span class="newsRegReason"></span><span class="newsRegDate"></span>';row.children[0].textContent=e.club||'—';row.children[1].textContent=e.name||'Player';row.children[2].textContent=e.reason||'New registration';row.children[3].textContent=e.date||'';rows.appendChild(row)}if(events.length>6){const b=document.createElement('button');b.type='button';b.className='fmCanonicalNewsToggle';b.dataset.newsToggle='fmCanonicalRegistrationsFull';b.textContent=`View all ${events.length}`;rows.appendChild(b)}try{window.FMNewsClubFilter?.install?.(card)}catch(_e){}}
function styles(){if(document.getElementById('fmRegistrationNewsStyle'))return;const s=document.createElement('style');s.id='fmRegistrationNewsStyle';s.textContent='#newsRegistrations{margin-top:14px}.newsRegEyebrow{font-size:9px;letter-spacing:.12em;color:#a99bc7;font-weight:900}.newsRegRows,.fmCanonicalTransferRows{display:grid;gap:7px}.newsRegRow,.fmNewsTransferRow{display:grid;grid-template-columns:minmax(105px,.9fr) minmax(140px,1.2fr) minmax(110px,.7fr) auto;gap:10px;align-items:center;padding:10px 12px;border-radius:11px;background:rgba(255,255,255,.035);font-size:11px}.newsRegClub,.fmNewsMove{color:#d9cfff;font-weight:800}.newsRegName,.fmNewsName{color:#fff;font-weight:900}.newsRegReason{color:#bcb3d2}.newsRegDate,.fmNewsDate,.fmNewsPrice{color:#8d83a9;font-size:10px}.fmNewsPrice{text-align:right}.fmNewsCanonicalEmpty{padding:12px;color:#968da9;font-size:11px}.fmCanonicalNewsToggle{justify-self:start;margin-top:4px;border:1px solid rgba(255,255,255,.12);border-radius:9px;background:#251546;color:#fff;padding:7px 10px;font-size:10px;font-weight:850;cursor:pointer}.newsHidden{display:none!important}@media(max-width:700px){.newsRegRow,.fmNewsTransferRow{grid-template-columns:1fr 1fr}.newsRegReason{grid-column:1/-1}.newsRegDate,.fmNewsDate{text-align:right}}';document.head.appendChild(s)}
let refreshing=false,lastRefresh=0;
function refresh(){if(refreshing)return;refreshing=true;try{activateNews();styles();renderTransfers(document);renderRegistrations(document);lastRefresh=Date.now()}finally{refreshing=false}}
function schedule(ms=0){setTimeout(refresh,ms)}
window.FMRegistrationNewsGuard={version:VERSION,buildEvidence,refresh,renderTransfers,renderRegistrations};
window.addEventListener('fmcloudready',()=>{installPublishGuard();schedule(0);schedule(300);schedule(1000)});
window.addEventListener('fmworldloaded',()=>{schedule(0);schedule(250);schedule(900)});
window.addEventListener('focus',()=>schedule(50));
document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const txt=norm(b.textContent||''),page=norm(b.dataset?.nav||b.getAttribute('data-page')||'');if(txt.includes('news')||page.includes('news')){schedule(40);schedule(250)}},true);
let tries=0;const timer=setInterval(()=>{tries++;installPublishGuard();if(currentPayload())refresh();if(tries>60)clearInterval(timer)},250);
let moQueued=false;new MutationObserver(muts=>{if(refreshing||moQueued||Date.now()-lastRefresh<40)return;if(!muts.some(m=>[...m.addedNodes].some(n=>n?.nodeType===1&&(n.id==='newsTransfers'||n.id==='newsPage'||n.querySelector?.('#newsTransfers,#newsPage')))))return;moQueued=true;requestAnimationFrame(()=>{moQueued=false;refresh()})}).observe(document.documentElement,{childList:true,subtree:true});
})();
