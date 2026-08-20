(()=>{
'use strict';
const VERSION='goalkeeper-eligibility-v1-current-club-over-cohort';
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase();
function unavailable(p){const s=[p?.injury_status,p?.suspension_status,p?.status,p?.availability_status].filter(Boolean).join(' ').toLowerCase();return !!(p?.injured||p?.suspended||s.includes('injur')||s.includes('suspend'))}
function fix(payload){
 if(!payload||!Array.isArray(payload.players))return payload;
 const clubs=new Set();for(const f of arr(payload.fixtures)){if(f?.home)clubs.add(norm(f.home));if(f?.away)clubs.add(norm(f.away))}
 let rescued=0;const examples=[];
 for(const p of payload.players){
   if(String(p?.pos||p?.position||'').toUpperCase()!=='GK')continue;
   const club=norm(p?.club||p?.club_full||p?.team||'');
   if(!club||!clubs.has(club)||p?.unresolved===true)continue;
   const wasHidden=p.visible===false||p.competition_eligible===false||String(p.registration_status||'').includes('not_in_current_competition_cohort');
   if(!wasHidden)continue;
   p.competition_eligible=true;
   p.visible=true;
   p.registration_status='current_club_goalkeeper_exception';
   p.registration_evidence={...(p.registration_evidence||{}),eligible:true,override:VERSION,reason:'Goalkeepers assigned to a current selected-league club cannot be hard-excluded by the competition cohort table.'};
   if(!unavailable(p))p.available=true;
   rescued++;if(examples.length<20)examples.push({id:p.id??p.pid??null,name:p.name??p.display_name??null,club:p.club??p.club_full??null});
 }
 payload.meta=payload.meta||{};
 payload.meta.goalkeeper_eligibility_policy=VERSION;
 payload.meta.goalkeepers_rescued_from_cohort_filter=rescued;
 payload.meta.goalkeeper_eligibility_examples=examples;
 return payload;
}
function install(){
 let original;try{original=globalThis.fmApplyPostPayloadPricingCorrections}catch(_e){return false}
 if(typeof original!=='function'||original.__fmGoalkeeperEligibilityV1)return false;
 const wrapped=function(payload,...args){const out=original(payload,...args);fix(payload);try{if(typeof fmDebugAdd==='function')fmDebugAdd('info','Goalkeeper eligibility correction applied.',{version:VERSION,rescued:payload?.meta?.goalkeepers_rescued_from_cohort_filter||0})}catch(_e){}return out};
 wrapped.__fmGoalkeeperEligibilityV1=true;wrapped.__fmGoalkeeperEligibilityOriginal=original;globalThis.fmApplyPostPayloadPricingCorrections=wrapped;return true;
}
window.FMGoalkeeperEligibilityFix={version:VERSION,fix,install};let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>60)clearInterval(timer)},100);window.addEventListener('fmcloudready',install);
})();