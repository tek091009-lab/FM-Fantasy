(()=>{
'use strict';
const VERSION='registration-news-v3-success-boundary-transfer-arrivals';
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
 const rawCandidates=arr(next?.meta?._transfer_news_candidates_v3),arrivalTransfers=[];let candidateAccepted=0,candidateRejected=0;
 for(const row of rawCandidates){
   const id=candidateId(row,nextByName),p=nextById.get(id),prev=oldById.get(id)||null;if(!id||!p||!visible(p)){candidateRejected++;continue}
   const newClub=club(p),claimedNew=String(row?.new_club||row?.to||row?.club||'').trim();if(!newClub||(claimedNew&&norm(claimedNew)!==norm(newClub))){candidateRejected++;continue}
   const prevClub=club(prev),oldClub=String(row?.old_club||row?.from||row?.previous_club||prevClub||'Outside league').trim()||'Outside league';
   if(norm(oldClub)===norm(newClub)){candidateRejected++;continue}
   const reg=regById.get(id)||null,direct=!!(prev&&visible(prev)&&prevClub&&norm(prevClub)!==norm(newClub));
   if(!direct&&!reg){candidateRejected++;continue}
   let date=String(row?.date||row?.transfer_date||reg?.date||newSnapshot||'').slice(0,10)||null;if(date&&oldSnapshot&&date<=oldSnapshot){candidateRejected++;continue}
   arrivalTransfers.push({id,name:label(p),old_club:direct?prevClub:oldClub,new_club:newClub,date,source:direct?'canonical_club_change':'validated_import_arrival'});candidateAccepted++;
 }
 const transfers=[],seen=new Set();for(const e of [...directTransfers,...arrivalTransfers]){const k=`${e.id}|${norm(e.new_club)}`;if(seen.has(k))continue;seen.add(k);transfers.push(e)}
 next.meta=next.meta||{};delete next.meta._transfer_news_candidates_v3;
 next.meta.transfer_news_policy='successful-update only: canonical visible club changes plus import-observed arrivals validated against the new canonical player and a genuine registration boundary';
 next.meta.transfer_news_guard={version:VERSION,old_snapshot:oldSnapshot||null,new_snapshot:newSnapshot||null,events:transfers,candidate_rows_seen:rawCandidates.length,candidate_rows_accepted:candidateAccepted,candidate_rows_rejected:candidateRejected};
 next.meta.registration_news={version:VERSION,old_snapshot:oldSnapshot||null,new_snapshot:newSnapshot||null,events:registrationEvents};
 return {transfers,registrationEvents};
}
function installPublishGuard(){const c=window.FMCloud;if(!c||c.__registrationNewsV3||typeof c.publishWorld!=='function')return false;c.__registrationNewsV3=true;const original=c.publishWorld.bind(c);c.publishWorld=async(payload,...args)=>{if(!payload)return original(payload,...args);const old=JSON.parse(JSON.stringify(c.getWorld?.()?.payload||null));buildEvidence(payload,old);return original(payload,...args)};return true}
function currentPayload(){try{return window.FMCloud?.getWorld?.()?.payload||null}catch(_e){return null}}
function allowedTransferNames(){return arr(currentPayload()?.meta?.transfer_news_guard?.events).map(e=>norm(e?.name)).filter(Boolean)}
function pruneTransfers(root=document){const scope=root.querySelector?.('#newsTransfers');if(!scope)return;const allowed=allowedTransferNames(),rows=[...new Set([...scope.querySelectorAll('[data-news-text]'),...scope.querySelectorAll('.transfer')])];for(const row of rows){const text=norm(row.textContent||'');row.style.display=allowed.some(n=>text.includes(n))?'':'none'}const shown=rows.filter(r=>r.style.display!=='none').length,toggle=scope.querySelector('[data-news-toggle]');if(toggle){toggle.dataset.newsCount=String(shown);toggle.textContent=`View all ${shown}`;toggle.style.display=shown?'':'none'}}
function ensureRegistrationCard(root=document){const transfers=root.querySelector?.('#newsTransfers');if(!transfers)return null;let card=root.querySelector('#newsRegistrations');if(card)return card;card=document.createElement('section');card.id='newsRegistrations';card.className=transfers.className||'newsCard';card.innerHTML='<div class="newsHead"><div><div class="newsRegEyebrow">PLAYER POOL</div><h3>New registrations</h3></div></div><input class="ctrl newsSearch" data-news-search placeholder="Filter by club"><div class="newsRegRows"></div>';transfers.insertAdjacentElement('afterend',card);return card}
function renderRegistrations(root=document){const card=ensureRegistrationCard(root);if(!card)return;const rows=card.querySelector('.newsRegRows'),events=arr(currentPayload()?.meta?.registration_news?.events);rows.replaceChildren();if(!events.length){const empty=document.createElement('div');empty.className='fmNewsRegEmpty';empty.textContent='No new registrations since the last successful database update.';rows.appendChild(empty);return}for(const e of events){const row=document.createElement('div');row.className='newsRegRow';row.dataset.newsText='1';row.innerHTML='<span class="newsRegClub"></span><span class="newsRegName"></span><span class="newsRegReason"></span><span class="newsRegDate"></span>';row.children[0].textContent=e.club||'—';row.children[1].textContent=e.name||'Player';row.children[2].textContent=e.reason||'New registration';row.children[3].textContent=e.date||'';rows.appendChild(row)}try{window.FMNewsClubFilter?.install?.(card)}catch(_e){}}
function styles(){if(document.getElementById('fmRegistrationNewsStyle'))return;const s=document.createElement('style');s.id='fmRegistrationNewsStyle';s.textContent='#newsRegistrations{margin-top:14px}.newsRegEyebrow{font-size:9px;letter-spacing:.12em;color:#a99bc7;font-weight:900}.newsRegRows{display:grid;gap:7px}.newsRegRow{display:grid;grid-template-columns:minmax(105px,.8fr) minmax(140px,1.2fr) minmax(190px,1.6fr) auto;gap:10px;align-items:center;padding:10px 12px;border-radius:11px;background:rgba(255,255,255,.035);font-size:11px}.newsRegClub{color:#d9cfff;font-weight:800}.newsRegName{color:#fff;font-weight:900}.newsRegReason{color:#bcb3d2}.newsRegDate{color:#8d83a9;font-size:10px}.fmNewsRegEmpty{padding:12px;color:#968da9;font-size:11px}@media(max-width:700px){.newsRegRow{grid-template-columns:1fr 1fr}.newsRegReason{grid-column:1/-1}.newsRegDate{text-align:right}}';document.head.appendChild(s)}
function refresh(){styles();pruneTransfers(document);renderRegistrations(document)}
window.FMRegistrationNewsGuard={version:VERSION,buildEvidence,refresh,pruneTransfers,renderRegistrations};window.addEventListener('fmcloudready',()=>{installPublishGuard();setTimeout(refresh,0);setTimeout(refresh,500)});let tries=0;const timer=setInterval(()=>{tries++;if(installPublishGuard()||tries>50)clearInterval(timer)},200);document.addEventListener('click',e=>{const b=e.target.closest?.('button,a,[role="button"]');if(!b)return;const txt=norm(b.textContent||'');if(txt==='news'||b.dataset?.nav==='news'||b.getAttribute('data-page')==='news')setTimeout(refresh,60)},true);window.addEventListener('fmworldloaded',()=>setTimeout(refresh,0));
})();