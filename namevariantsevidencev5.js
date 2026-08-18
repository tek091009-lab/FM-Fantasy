(()=>{
'use strict';
const VERSION='name-variants-evidence-v5';
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
  common:clean(p?.common_known_as||p?.common_name||p?.known_as||e?.common_known_as||e?.common_name),
  nickname:clean(p?.nickname||e?.nickname),
  shirt:clean(p?.shirt_name||p?.shirtname||e?.shirt_name),
  preferred_short:clean(p?.preferred_short_name||p?.short_name||e?.preferred_short_name),
  display:clean(p?.public_name||p?.display_name||p?.name||e?.resolved_display_name)
 };
}
function relation(display,value){
 const d=low(display),v=low(value);if(!v)return 'absent';if(d===v)return 'equals_display';if(d.startsWith(v+' '))return 'display_prefix';if(d.endsWith(' '+v))return 'display_suffix';if(d.includes(' '+v+' '))return 'display_contains';return 'distinct_from_display';
}
function run(){
 let ps=[];try{ps=arr(PLAYERS)}catch(_){}
 const out={version:VERSION,policy:'Evidence-only. Legal/full, common/known-as, nickname, shirt name and preferred short name are separate roles; none may overwrite public display without independent validation.',players:0,variant_counts:{nickname:0,shirt_name:0,preferred_short_name:0},relations:{nickname:{},shirt_name:{},preferred_short_name:{}},examples:[],taty:null};
 for(const p of ps){if(!p||p.visible===false)continue;out.players++;const f=fields(p);
  for(const [key,val] of [['nickname',f.nickname],['shirt_name',f.shirt],['preferred_short_name',f.preferred_short]]){
   if(!val)continue;out.variant_counts[key]++;const r=relation(f.display,val);out.relations[key][r]=(out.relations[key][r]||0)+1;
   if(out.examples.length<18)out.examples.push({person_id:pid(p),role:key,value:val,display:f.display,relationship:r});
  }
  if(pid(p)==='24517')out.taty={person_id:'24517',legal:f.legal||null,first:f.first||null,surname:f.surname||null,common:f.common||null,nickname:f.nickname||null,shirt_name:f.shirt||null,preferred_short_name:f.preferred_short||null,display:f.display||null,relationships:{common:relation(f.display,f.common),nickname:relation(f.display,f.nickname),shirt_name:relation(f.display,f.shirt),preferred_short_name:relation(f.display,f.preferred_short)},validation_only_no_display_override:true};
 }
 try{window.FM_NAME_VARIANTS_EVIDENCE_V5=out;if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG)FM_DEBUG.nameVariantsEvidenceV5=out;if(typeof META==='object'&&META)META.name_variants_evidence_v5=out}catch(_){}
 return out;
}
function install(){let orig;try{orig=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){}if(orig&&!orig.__fmNameVariantsV5){const w=function(...a){const r=orig.apply(this,a);try{run()}catch(e){console.warn('name variant evidence failed',e)}return r};w.__fmNameVariantsV5=true;try{applyImportedPayload=w}catch(_){}}try{run()}catch(_){}}
window.FMNameVariantsEvidenceV5={version:VERSION,run};install();
})();
