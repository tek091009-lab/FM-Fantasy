(()=>{
'use strict';
const VERSION='news-club-filter-v1';
function clubList(){
 try{return [...new Set((Array.isArray(PLAYERS)?PLAYERS:[]).map(p=>p?.club).filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b)))}catch(_e){return[]}
}
function rowClubs(row){
 const spans=[...row.querySelectorAll(':scope > span')].map(s=>(s.textContent||'').trim()).filter(Boolean);
 if(row.classList.contains('transfer'))return spans.slice(0,2);
 return spans.length?[spans[0]]:[];
}
function scopeFor(el){return el.closest('#fmNewsOverlay [id^="news"], #newsTransfers, #newsPriceUp, #newsPriceDown, #newsInjuries, #newsSuspensions')||el.parentElement}
function filter(scope,club){
 if(!scope)return;const overlay=!!scope.closest('#fmNewsOverlay'),rows=[...scope.querySelectorAll('[data-news-text]')],full=scope.querySelector('[id$="Full"]'),toggle=scope.querySelector('[data-news-toggle]');
 if(club){if(full)full.classList.remove('newsHidden');for(const r of rows)r.style.display=rowClubs(r).includes(club)?'':'none';if(toggle)toggle.style.display='none'}
 else{for(const r of rows)r.style.display='';if(!overlay&&full)full.classList.add('newsHidden');if(toggle){toggle.style.display='';toggle.textContent=`View all ${toggle.dataset.newsCount||rows.length}`}}
}
function makeSelect(input){
 if(!input||input.dataset.fmClubFilterReady==='1')return input;
 const clubs=clubList(),sel=document.createElement('select');sel.className=(input.className||'ctrl newsSearch')+' fmNewsClubFilter';sel.dataset.fmClubFilterReady='1';sel.setAttribute('aria-label','Filter news by club');
 const all=document.createElement('option');all.value='';all.textContent='All clubs';sel.appendChild(all);
 for(const club of clubs){const o=document.createElement('option');o.value=club;o.textContent=club;sel.appendChild(o)}
 sel.addEventListener('change',()=>filter(scopeFor(sel),sel.value));input.replaceWith(sel);return sel;
}
function hydrateSelect(sel){if(!sel||sel.dataset.fmClubFilterBound==='1')return;sel.dataset.fmClubFilterBound='1';sel.addEventListener('change',()=>filter(scopeFor(sel),sel.value))}
function install(root=document){root.querySelectorAll?.('[data-news-search]').forEach(makeSelect);root.querySelectorAll?.('select.fmNewsClubFilter').forEach(hydrateSelect)}
function styles(){if(document.getElementById('fmNewsClubFilterStyle'))return;const s=document.createElement('style');s.id='fmNewsClubFilterStyle';s.textContent='.fmNewsClubFilter{width:100%;margin:9px 0 5px;cursor:pointer}.fmNewsClubFilter option{background:#17112f;color:#fff}';document.head.appendChild(s)}
styles();install();let busy=false;new MutationObserver(()=>{if(busy)return;busy=true;requestAnimationFrame(()=>{busy=false;install()})}).observe(document.documentElement,{subtree:true,childList:true});
window.FMNewsClubFilter={version:VERSION,install,filter,clubList};
})();
