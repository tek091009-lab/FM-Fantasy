(()=>{'use strict';
const VERSION=3,clean=v=>String(v??'').replace(/\s+/g,' ').trim(),low=v=>clean(v).toLowerCase();
function id(p){const x=p?.pid??p?.player_id??p?.person_id??p?.uid??String(p?.id??'').split('|')[0];return clean(x)}
function ref(role,v){return v===null||v===undefined||String(v)===''?null:`${role}:${String(v)}`}
function comp(p){const e=p?.name_component_evidence||{},pools=e.component_pool_ids||{};const firstId=pools.first??p.first_pool_id??p.first_name_id??null,surnameId=pools.surname??p.surname_pool_id??p.surname_name_id??null,commonId=pools.common??p.common_pool_id??p.common_name_id??null;return{first:clean(p.first||p.first_name||e.first||e.first_name),surname:clean(p.surname_family||p.surname_name||p.surname||e.surname_family||e.surname_name),common:clean(p.common_known_as||p.common_name||p.known_as||e.common_known_as||e.common_name),display:clean(p.public_name||p.display_name||p.name||e.resolved_display_name),first_id:firstId,surname_id:surnameId,common_id:commonId,first_ref:ref('forename',firstId),surname_ref:ref('surname',surnameId),common_ref:ref('common',commonId)}}
function atStart(d,v){v=low(v);return !!v&&(d===v||d.startsWith(v+' '))}
function atEnd(d,v){v=low(v);return !!v&&(d===v||d.endsWith(' '+v))}
function run(){let ps=[];try{ps=Array.isArray(PLAYERS)?PLAYERS:[]}catch(_){}const s={version:VERSION,players:0,component_rows:0,first_rows:0,surname_rows:0,common_rows:0,first_role_hits:0,surname_role_hits:0,common_role_hits:0,first_end_only:0,surname_start_only:0,common_end_only:0,common_plus_surname_cross_validated:0,semantic_role_conflicts:0,pool_id_policy:'IDs are namespaced by pool; raw numeric IDs are never compared across forename/surname/common pools',taty:null,examples:[]};
 for(const p of ps){if(!p||p.visible===false)continue;const c=comp(p),d=low(c.display);s.players++;if(!(c.first||c.surname||c.common))continue;s.component_rows++;
  const fs=atStart(d,c.first),fe=atEnd(d,c.first),ss=atStart(d,c.surname),se=atEnd(d,c.surname),cs=atStart(d,c.common),ce=atEnd(d,c.common);
  if(c.first){s.first_rows++;if(fs)s.first_role_hits++;if(fe&&!fs)s.first_end_only++}
  if(c.surname){s.surname_rows++;if(se)s.surname_role_hits++;if(ss&&!se)s.surname_start_only++}
  if(c.common){s.common_rows++;if(cs)s.common_role_hits++;if(ce&&!cs)s.common_end_only++}
  const ne=p.name_schema_evidence||{};if(ne.cross_source_common_plus_surname_validated)s.common_plus_surname_cross_validated++;
  // Cross-pool numeric IDs are unrelated namespaces. Only semantic behaviour can indicate a role conflict.
  const semanticConflict=(c.first&&c.surname&&fe&&!fs&&ss&&!se)||(c.common&&c.surname&&ce&&!cs&&ss&&!se);
  if(semanticConflict){s.semantic_role_conflicts++;if(s.examples.length<10)s.examples.push({person_id:id(p),display:c.display,first:c.first,surname:c.surname,common:c.common,first_ref:c.first_ref,surname_ref:c.surname_ref,common_ref:c.common_ref})}
  if(id(p)==='24517')s.taty={person_id:'24517',display:c.display,first:c.first||null,surname:c.surname||null,common:c.common||null,first_pool_ref:c.first_ref,surname_pool_ref:c.surname_ref,common_pool_ref:c.common_ref,raw_pool_ids:{first:c.first_id,surname:c.surname_id,common:c.common_id},common_plus_surname_candidate:clean([c.common,c.surname].filter(Boolean).join(' '))||null,common_plus_surname_cross_validated:!!ne.cross_source_common_plus_surname_validated,validation_only:true};
 }
 const ratios={first:s.first_rows?s.first_role_hits/s.first_rows:0,surname:s.surname_rows?s.surname_role_hits/s.surname_rows:0,common:s.common_rows?s.common_role_hits/s.common_rows:0};
 const confusion={first_end_only:s.first_rows?s.first_end_only/s.first_rows:0,surname_start_only:s.surname_rows?s.surname_start_only/s.surname_rows:0,common_end_only:s.common_rows?s.common_end_only/s.common_rows:0};s.role_hit_ratios=ratios;s.role_confusion_ratios=confusion;s.role_eligible_rows={first:s.first_rows,surname:s.surname_rows,common:s.common_rows};
 const enoughCore=s.first_rows>=20&&s.surname_rows>=20,commonEvidence=s.common_rows>=5;const swapped=confusion.first_end_only>=0.35&&confusion.surname_start_only>=0.35;
 s.pool_role_status=!enoughCore?'insufficient_evidence':swapped?'probable_forename_surname_role_swap':s.semantic_role_conflicts>Math.max(5,Math.floor(s.component_rows*.08))?'semantic_conflict_detected':(ratios.surname>=0.7&&ratios.first>=0.45&&(!commonEvidence||ratios.common>=0.45))?'roles_consistent_with_person_records':'role_order_unproven';
 s.policy='Evidence-only v3: pool IDs are separate namespaces. Role validation uses component position in independently resolved football displays plus cross-source retained-match validation; visible names are never rewritten.';
 try{window.FM_NAME_POOL_ROLE_EVIDENCE=s;if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG)FM_DEBUG.namePoolRoleEvidence=s;if(typeof META==='object'&&META)META.name_pool_role_evidence=s}catch(_){}return s}
function install(){let orig;try{orig=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){}if(orig&&!orig.__fmNamePoolRoleWrapped){const w=function(...a){const o=orig.apply(this,a);try{run()}catch(e){console.warn('name pool role evidence failed',e)}return o};w.__fmNamePoolRoleWrapped=true;try{applyImportedPayload=w}catch(_){}}try{run()}catch(_){}}
window.fmValidateNamePoolRoles=run;install();})();
