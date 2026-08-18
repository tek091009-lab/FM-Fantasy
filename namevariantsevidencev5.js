(()=>{
'use strict';
const VERSION='name-variants-evidence-v6-role-separation';
const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
const low=v=>clean(v).toLowerCase();
const arr=v=>Array.isArray(v)?v:[];
function pid(p){return clean(p?.pid??p?.player_id??p?.person_id??p?.uid??String(p?.id??'').split('|')[0]);}
function fields(p){
 const e=p?.name_component_evidence||{};
 return {
  legal:clean(p?.legal_full||p?.legal_name||e?.legal_full||e?.legal_name),
  first:clean(p?.first||p?.first_name||e?.first||e?.first_name),
  surname:clean(p?.surname_family||p?.surname_name||p?.surname||e?.surname_family||e?.surname_name),
  // common/known-as is deliberately NOT populated from generic preferred_name.
  // Some FM/schema generations use preferred_name for a short/display preference;
  // conflating that with the dedicated common-name pool would teach the wrong role.
  common:clean(p?.common_known_as||p?.common_name||p?.known_as||e?.common_known_as||e?.common_name),
  nickname:clean(p?.nickname||e?.nickname),
  shirt:clean(p?.shirt_name||p?.shirtname||e?.shirt_name),
  preferred_short:clean(p?.preferred_short_name||p?.short_name||e?.preferred_short_name),
  preferred_name_raw:clean(p?.preferred_name||e?.preferred_name),
  display:clean(p?.public_name||p?.display_name||p?.name||e?.resolved_display_name)
 };
}
function relation(display,value){
 const d=low(display),v=low(value);if(!v)return 'absent';if(d===v)return 'equals_display';if(d.startsWith(v+' '))return 'display_prefix';if(d.endsWith(' '+v))return 'display_suffix';if(d.includes(' '+v+' '))return 'display_contains';return 'distinct_from_display';
}
function run(){
 let ps=[];try{ps=arr(PLAYERS)}catch(_){}
 const out={version:VERSION,policy:'Evidence-only. Legal/full, common/known-as, nickname, shirt name, preferred short name and generic preferred_name are separate roles. preferred_name is ambiguous until independently mapped and must not be treated as common/known-as by default.',players:0,variant_counts:{nickname:0,shirt_name:0,preferred_short_name:0,preferred_name_raw:0},relations:{nickname:{},shirt_name:{},preferred_short_name:{},preferred_name_raw:{}},preferred_name_role_evidence:{equals_common:0,equals_preferred_short:0,equals_display:0,distinct:0},examples:[],taty:null};
 for(const p of ps){if(!p||p.visible===false)continue;out.players++;const f=fields(p);
  for(const [key,val] of [['nickname',f.nickname],['shirt_name',f.shirt],['preferred_short_name',f.preferred_short],['preferred_name_raw',f.preferred_name_raw]]){
   if(!val)continue;out.variant_counts[key]++;const r=relation(f.display,val);out.relations[key][r]=(out.relations[key][r]||0)+1;
   if(out.examples.length<24)out.examples.push({person_id:pid(p),role:key,value:val,display:f.display,relationship:r});
  }
  if(f.preferred_name_raw){
   if(f.common&&low(f.preferred_name_raw)===low(f.common))out.preferred_name_role_evidence.equals_common++;
   else if(f.preferred_short&&low(f.preferred_name_raw)===low(f.preferred_short))out.preferred_name_role_evidence.equals_preferred_short++;
   else if(f.display&&low(f.preferred_name_raw)===low(f.display))out.preferred_name_role_evidence.equals_display++;
   else out.preferred_name_role_evidence.distinct++;
  }
  if(pid(p)==='24517')out.taty={person_id:'24517',legal:f.legal||null,first:f.first||null,surname:f.surname||null,common:f.common||null,nickname:f.nickname||null,shirt_name:f.shirt||null,preferred_short_name:f.preferred_short||null,preferred_name_raw:f.preferred_name_raw||null,display:f.display||null,relationships:{common:relation(f.display,f.common),nickname:relation(f.display,f.nickname),shirt_name:relation(f.display,f.shirt),preferred_short_name:relation(f.display,f.preferred_short),preferred_name_raw:relation(f.display,f.preferred_name_raw)},validation_only_no_display_override:true};
 }
 try{window.FM_NAME_VARIANTS_EVIDENCE_V6=out;if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.nameVariantsEvidenceV6=out;FM_DEBUG.nameVariantsPolicyV6=out.policy}if(typeof META==='object'&&META)META.name_variants_evidence_v6=out}catch(_){}
 return out;
}
function install(){let orig;try{orig=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){}if(orig&&!orig.__fmNameVariantsV6){const w=function(...a){const r=orig.apply(this,a);try{run()}catch(e){console.warn('name variant evidence failed',e)}return r};w.__fmNameVariantsV6=true;try{applyImportedPayload=w}catch(_){}}try{run()}catch(_){}}
window.FMNameVariantsEvidenceV6={version:VERSION,run};install();
})();
