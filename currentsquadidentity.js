(()=>{
'use strict';
const arr=v=>Array.isArray(v)?v:[];
const nonempty=v=>v!==null&&v!==undefined&&String(v)!=='';
const norm=v=>String(v??'').trim().toLocaleLowerCase();
function g(name,fallback){try{return typeof window[name]!=='undefined'?window[name]:fallback}catch(_){return fallback}}
function stablePersonId(p){
 if(!p)return null;
 for(const k of ['pid','player_id','person_id','uid'])if(nonempty(p[k]))return String(p[k]);
 if(nonempty(p.id)){const m=String(p.id).match(/^(-?\d+)/);if(m)return m[1]}
 return null;
}
function playerClub(p){
 if(!p)return null;
 if(nonempty(p.club_id))return {kind:'id',key:String(p.club_id),label:String(p.club??p.club_name??p.club_id)};
 const n=p.club??p.club_name??p.team??p.team_name;
 if(nonempty(n))return {kind:'name',key:norm(n),label:String(n)};
 return null;
}
function calendarClubs(fixtures){
 const ids=new Set(), names=new Set();
 for(const f of fixtures){
  if(nonempty(f?.home_id))ids.add(String(f.home_id));
  if(nonempty(f?.away_id))ids.add(String(f.away_id));
  if(nonempty(f?.home))names.add(norm(f.home));
  if(nonempty(f?.away))names.add(norm(f.away));
 }
 return {ids,names};
}
function clubIsCurrent(c,cal){
 if(!c)return false;
 if(c.kind==='id'&&cal.ids.size)return cal.ids.has(c.key);
 if(c.kind==='name'&&cal.names.size)return cal.names.has(c.key);
 return true;
}
function nameSnapshot(p){
 const e=p?.name_component_evidence||{};
 const r=p?.name_resolution_evidence||{};
 return {
  display:p?.canonical_display_name??p?.football_display_name??p?.display_name??p?.public_name??p?.name??null,
  legal:p?.legal_full??p?.legal_full_name??p?.legal_name??p?.full_name??e.legal_full??e.legal_name??null,
  first:p?.first??p?.first_name??p?.forename??e.first??e.first_name??null,
  surname:p?.surname_family??p?.surname_name??p?.football_surname??p?.surname??p?.family_name??e.surname_family??e.surname_name??null,
  common:p?.common_known_as??p?.common_name??p?.known_as??p?.preferred_name??e.common_known_as??e.common_name??null,
  nickname:p?.nickname??e.nickname??null,
  shirt_name:p?.shirt_name??e.shirt_name??null,
  preferred_short_name:p?.preferred_short_name??e.preferred_short_name??null,
  first_pool_id:p?.first_pool_id??e.first_pool_id??null,
  surname_pool_id:p?.surname_pool_id??e.surname_pool_id??null,
  common_pool_id:p?.common_pool_id??e.common_pool_id??null,
  common_plus_surname_validated:!!(e.common_plus_surname_is_validated_by_display||r.common_plus_surname_is_validated_by_display||p?.name_schema_evidence?.relationship?.display_exact_common_surname)
 };
}
function build(){
 const players=arr(g('PLAYERS',[])).filter(p=>p&&p.visible!==false);
 const fixtures=arr(g('SEASON_FIXTURES',[]));
 const cal=calendarClubs(fixtures);
 const byPerson=new Map();
 let recordsWithoutStableId=0;
 for(const p of players){
  const pid=stablePersonId(p);
  if(!pid){recordsWithoutStableId++;continue}
  const club=playerClub(p);
  const row={record_id:p.id??null,pid,club,current_calendar:clubIsCurrent(club,cal),name:nameSnapshot(p),pos:p.pos??p.position??null,price:p.price??p.value??null};
  if(!byPerson.has(pid))byPerson.set(pid,[]);
  byPerson.get(pid).push(row);
 }
 let uniqueCurrent=0, ambiguousCurrent=0, noCurrent=0, duplicateSameClub=0, namingDivergence=0;
 const conflicts=[], outside=[], duplicateExamples=[], namingExamples=[];
 const uniqueMap={};
 for(const [pid,rows] of byPerson){
  const current=rows.filter(r=>r.club&&r.current_calendar);
  const clubs=new Map();
  for(const r of current)clubs.set(`${r.club.kind}:${r.club.key}`,r.club);
  if(clubs.size===1){
   uniqueCurrent++;
   const c=[...clubs.values()][0];
   uniqueMap[pid]={club_kind:c.kind,club_key:c.key,club_label:c.label,records:current.length};
   if(current.length>1){duplicateSameClub++;if(duplicateExamples.length<20)duplicateExamples.push({pid,club:c.label,records:current.map(r=>r.record_id)})}
  }else if(clubs.size>1){
   ambiguousCurrent++;
   if(conflicts.length<50)conflicts.push({pid,clubs:[...clubs.values()].map(c=>c.label),records:current.map(r=>({record_id:r.record_id,club:r.club?.label??null,name:r.name.display}))});
  }else{
   noCurrent++;
   const withClub=rows.filter(r=>r.club);
   if(withClub.length&&outside.length<50)outside.push({pid,clubs:[...new Set(withClub.map(r=>r.club.label))],records:withClub.map(r=>r.record_id)});
  }
  const sigs=new Set(rows.map(r=>JSON.stringify([r.name.display,r.name.legal,r.name.first,r.name.surname,r.name.common,r.name.nickname,r.name.shirt_name,r.name.preferred_short_name,r.name.first_pool_id,r.name.surname_pool_id,r.name.common_pool_id])));
  if(sigs.size>1){
   namingDivergence++;
   if(namingExamples.length<20)namingExamples.push({pid,records:rows.map(r=>({record_id:r.record_id,club:r.club?.label??null,...r.name}))});
  }
 }
 const tatyRows=byPerson.get('24517')||[];
 const evidence={
  version:1,
  generated_from_existing_import_pass:true,
  no_additional_fm_scan:true,
  population:{visible_player_records:players.length,stable_persons:byPerson.size,records_without_stable_person_id:recordsWithoutStableId,calendar_club_ids:cal.ids.size,calendar_club_names:cal.names.size},
  current_membership:{unique_persons:uniqueCurrent,ambiguous_persons:ambiguousCurrent,no_current_calendar_membership_persons:noCurrent,duplicate_same_club_persons:duplicateSameClub,unique_by_person:uniqueMap,conflict_examples:conflicts,outside_calendar_examples:outside,duplicate_same_club_examples:duplicateExamples},
  naming_identity_continuity:{persons_with_component_or_display_divergence_across_records:namingDivergence,examples:namingExamples,taty_validation:{person_id:'24517',records:tatyRows,found:tatyRows.length>0,policy:'Stable FM person identity is authoritative for validation. Club-record duplication or transfer drift must not change the natural football display name.'}},
  reusable_policy:'Resolve current squad identity by stable FM person ID first. A person is a safe current-club anchor only when all current-calendar records converge on one club. Multiple current-league clubs are an unresolved conflict, never a majority-vote guess. Records outside the current calendar remain preserved as stale/transfer evidence but are not current-squad anchors.'
 };
 try{window.FM_CURRENT_SQUAD_IDENTITY_EVIDENCE=evidence;window.fmCurrentSquadIdentityForPerson=pid=>evidence.current_membership.unique_by_person[String(pid)]||null}catch(_){ }
 try{
  const cap=window.FM_IMPORT_CAPABILITIES;
  if(cap&&typeof cap==='object'){
   cap.current_squad_identity=evidence.current_membership;
   cap.naming.identity_continuity=evidence.naming_identity_continuity;
   cap.current_database.stable_persons=byPerson.size;
   cap.current_database.ambiguous_current_membership_persons=ambiguousCurrent;
   cap.current_database.outside_calendar_persons=noCurrent;
   const gaps=Array.isArray(cap.unresolved_capabilities)?cap.unresolved_capabilities:[];
   if(ambiguousCurrent>0&&!gaps.includes('current_squad_membership_ambiguity'))gaps.push('current_squad_membership_ambiguity');
   cap.unresolved_capabilities=gaps;
  }
 }catch(_){ }
 try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.currentSquadIdentityEvidence=evidence;FM_DEBUG.currentSquadIdentitySummary={stable_persons:byPerson.size,unique_current_membership:uniqueCurrent,ambiguous_current_membership:ambiguousCurrent,no_current_calendar_membership:noCurrent,naming_divergence:namingDivergence,taty_records:tatyRows.length}}}catch(_){ }
 return evidence;
}
function install(){
 let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
 if(original&&!original.__fmCurrentSquadIdentityWrapped){
  const wrapped=function(...args){const out=original.apply(this,args);try{build()}catch(e){console.warn('Current squad identity evidence failed',e)}return out};
  wrapped.__fmCurrentSquadIdentityWrapped=true;try{applyImportedPayload=wrapped}catch(_){ }
 }
 try{build()}catch(_){ }
}
window.fmBuildCurrentSquadIdentityEvidence=build;install();
})();
