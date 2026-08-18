(()=>{
'use strict';
const arr=v=>Array.isArray(v)?v:[];
const nonempty=v=>v!==null&&v!==undefined&&String(v).trim()!=='';
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
 const label=p.club??p.club_name??p.team??p.team_name??null;
 const labelKey=nonempty(label)?norm(label):null;
 const id=nonempty(p.club_id)?String(p.club_id):null;
 if(!id&&!labelKey)return null;
 return {id,label:nonempty(label)?String(label):id,label_key:labelKey};
}
function calendarClubs(fixtures){
 const ids=new Set(),names=new Set();
 for(const f of fixtures){
  if(nonempty(f?.home_id))ids.add(String(f.home_id));
  if(nonempty(f?.away_id))ids.add(String(f.away_id));
  if(nonempty(f?.home))names.add(norm(f.home));
  if(nonempty(f?.away))names.add(norm(f.away));
 }
 return {ids,names};
}
function membership(c,cal){
 if(!c)return {current:false,method:'no_club'};
 const idSeen=!!(c.id&&cal.ids.size&&cal.ids.has(c.id));
 const nameSeen=!!(c.label_key&&cal.names.size&&cal.names.has(c.label_key));
 if(idSeen)return {current:true,method:'calendar_id'};
 if(nameSeen)return {current:true,method:'calendar_name_fallback'};
 if(cal.ids.size||cal.names.size)return {current:false,method:'calendar_miss'};
 return {current:false,method:'calendar_unavailable'};
}
function canonicalClubKey(c,cal){
 if(!c)return null;
 if(c.label_key&&cal.names.has(c.label_key))return `name:${c.label_key}`;
 if(c.id&&cal.ids.has(c.id))return `id:${c.id}`;
 return c.label_key?`name:${c.label_key}`:c.id?`id:${c.id}`:null;
}
function build(){
 const players=arr(g('PLAYERS',[])).filter(p=>p&&p.visible!==false);
 const fixtures=arr(g('SEASON_FIXTURES',[]));
 const cal=calendarClubs(fixtures);
 const byPerson=new Map();
 let recordsWithoutStableId=0,idNamespaceFallbacks=0,calendarMissRecords=0,calendarUnavailableRecords=0;
 for(const p of players){
  const pid=stablePersonId(p);
  if(!pid){recordsWithoutStableId++;continue}
  const club=playerClub(p),m=membership(club,cal);
  if(m.method==='calendar_name_fallback'&&club?.id)idNamespaceFallbacks++;
  if(m.method==='calendar_miss')calendarMissRecords++;
  if(m.method==='calendar_unavailable')calendarUnavailableRecords++;
  const row={record_id:p.id??null,pid,club,current_calendar:m.current,membership_method:m.method,pos:p.pos??p.position??null};
  if(!byPerson.has(pid))byPerson.set(pid,[]);
  byPerson.get(pid).push(row);
 }
 let uniqueCurrent=0,ambiguousCurrent=0,noCurrent=0;
 const uniqueMap={},conflicts=[],outside=[];
 for(const [pid,rows] of byPerson){
  const current=rows.filter(r=>r.club&&r.current_calendar);
  const clubs=new Map();
  for(const r of current){const k=canonicalClubKey(r.club,cal);if(k)clubs.set(k,r.club)}
  if(clubs.size===1){
   uniqueCurrent++;
   const c=[...clubs.values()][0],key=[...clubs.keys()][0];
   uniqueMap[pid]={club_kind:key.startsWith('id:')?'id':'name',club_key:key.slice(key.indexOf(':')+1),club_label:c.label,records:current.length,membership_methods:[...new Set(current.map(r=>r.membership_method))]};
  }else if(clubs.size>1){
   ambiguousCurrent++;
   if(conflicts.length<50)conflicts.push({pid,clubs:[...clubs.values()].map(c=>c.label),records:current.map(r=>({record_id:r.record_id,club:r.club?.label??null,method:r.membership_method}))});
  }else{
   noCurrent++;
   const withClub=rows.filter(r=>r.club);
   if(withClub.length&&outside.length<50)outside.push({pid,clubs:[...new Set(withClub.map(r=>r.club.label))],records:withClub.map(r=>({record_id:r.record_id,club:r.club?.label??null,method:r.membership_method}))});
  }
 }
 const evidence={version:2,generated_from_existing_import_pass:true,no_additional_fm_scan:true,
  policy:'Current squad membership requires positive evidence from the decoded current-season calendar. Prefer compatible club IDs; fall back to normalized calendar club names when FM entity-ID namespaces differ. Never treat an unknown club-ID namespace as current by default.',
  population:{visible_player_records:players.length,stable_persons:byPerson.size,records_without_stable_person_id:recordsWithoutStableId,calendar_club_ids:cal.ids.size,calendar_club_names:cal.names.size},
  namespace_evidence:{club_id_records_validated_by_calendar_name:idNamespaceFallbacks,calendar_miss_records:calendarMissRecords,calendar_unavailable_records:calendarUnavailableRecords},
  current_membership:{unique_persons:uniqueCurrent,ambiguous_persons:ambiguousCurrent,no_current_calendar_membership_persons:noCurrent,unique_by_person:uniqueMap,conflict_examples:conflicts,outside_calendar_examples:outside}
 };
 try{window.FM_CURRENT_SQUAD_IDENTITY_EVIDENCE_V2=evidence;window.FM_CURRENT_SQUAD_IDENTITY_EVIDENCE=evidence;window.fmCurrentSquadIdentityForPerson=pid=>evidence.current_membership.unique_by_person[String(pid)]||null}catch(_){ }
 try{
  const cap=window.FM_IMPORT_CAPABILITIES;
  if(cap&&typeof cap==='object'){
   cap.current_squad_identity=evidence.current_membership;
   cap.current_squad_identity_namespace_evidence=evidence.namespace_evidence;
   if(cap.current_database&&typeof cap.current_database==='object'){
    cap.current_database.stable_persons=byPerson.size;
    cap.current_database.ambiguous_current_membership_persons=ambiguousCurrent;
    cap.current_database.outside_calendar_persons=noCurrent;
   }
   const gaps=Array.isArray(cap.unresolved_capabilities)?cap.unresolved_capabilities:[];
   const i=gaps.indexOf('current_squad_membership_ambiguity');
   if(ambiguousCurrent>0&&i<0)gaps.push('current_squad_membership_ambiguity');
   if(ambiguousCurrent===0&&i>=0)gaps.splice(i,1);
   if(calendarUnavailableRecords>0&&!gaps.includes('current_squad_calendar_membership_evidence'))gaps.push('current_squad_calendar_membership_evidence');
   cap.unresolved_capabilities=gaps;
  }
 }catch(_){ }
 try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.currentSquadIdentityEvidenceV2=evidence;FM_DEBUG.currentSquadIdentitySummaryV2={stable_persons:byPerson.size,unique_current_membership:uniqueCurrent,ambiguous_current_membership:ambiguousCurrent,no_current_calendar_membership:noCurrent,club_id_name_fallbacks:idNamespaceFallbacks,calendar_miss_records:calendarMissRecords,calendar_unavailable_records:calendarUnavailableRecords}}}catch(_){ }
 return evidence;
}
function install(){
 let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
 if(original&&!original.__fmCurrentSquadIdentityCompatWrapped){
  const wrapped=function(...args){const out=original.apply(this,args);try{build()}catch(e){console.warn('Current squad identity compatibility evidence failed',e)}return out};
  wrapped.__fmCurrentSquadIdentityCompatWrapped=true;try{applyImportedPayload=wrapped}catch(_){ }
 }
 try{build()}catch(_){ }
}
window.fmBuildCurrentSquadIdentityEvidenceV2=build;install();
})();
