(()=>{
'use strict';
const g=(n,f)=>{try{return typeof window[n]!=='undefined'?window[n]:f}catch(_){return f}};
const norm=v=>String(v??'').trim().toLowerCase();
const MANUAL_SOURCES=new Set(['user_preference','manual','manual_override','user_override','user_selection','prompt_choice']);
function build(){
  const meta=g('META',{})||{};
  const source=norm(meta.league_selection_source||meta.competition_selection_source||meta.league_source||meta.competition_source||'unknown');
  const resolved=!!(meta.competition||meta.competition_name||meta.league||meta.league_name||meta.competition_fixture_id||meta.competition_id);
  const manual=MANUAL_SOURCES.has(source)||source.includes('user_preference')||source.includes('manual')||source.includes('override');
  const season=meta.fixture_season_start??meta.season_start_year??meta.season??meta.season_id??null;
  const calendar=Array.isArray(g('SEASON_FIXTURES',[]))?g('SEASON_FIXTURES',[]):[];
  const currentSeasonSupported=season!==null&&season!==undefined&&calendar.length>0;
  const out={
    version:1,
    competition_resolved:resolved,
    selection_source:source||'unknown',
    resolved_via_manual_override:manual,
    automatic_competition_detection_proven:resolved&&!manual&&source!=='unknown',
    automatic_competition_detection_unproven:resolved&&(manual||source==='unknown'),
    current_season_anchor_present:currentSeasonSupported,
    fixture_season_start:season,
    policy:'A manual/user league choice may produce a correct payload but does not prove universal automatic league detection. Preserve the successful payload while keeping automatic current-season competition detection open as a separate decoder capability.'
  };
  try{window.FM_COMPETITION_EVIDENCE=out}catch(_){ }
  try{
    if(window.FM_IMPORT_CAPABILITIES){
      const c=window.FM_IMPORT_CAPABILITIES;
      c.competition_detection_evidence=out;
      c.competition=c.competition||{};
      c.competition.selection_source=out.selection_source;
      c.competition.automatic_detection_proven=out.automatic_competition_detection_proven;
      c.competition.resolved_via_manual_override=out.resolved_via_manual_override;
      c.unresolved_capabilities=Array.isArray(c.unresolved_capabilities)?c.unresolved_capabilities:[];
      if(out.automatic_competition_detection_unproven&&!c.unresolved_capabilities.includes('automatic_current_season_competition_detection'))c.unresolved_capabilities.push('automatic_current_season_competition_detection');
    }
  }catch(_){ }
  try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.competitionDetectionEvidence=out}}catch(_){ }
  return out;
}
function install(){
  let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
  if(original&&!original.__fmCompetitionEvidenceWrapped){
    const wrapped=function(...args){const out=original.apply(this,args);try{setTimeout(build,0)}catch(_){ }return out};
    wrapped.__fmCompetitionEvidenceWrapped=true;
    try{applyImportedPayload=wrapped}catch(_){ }
  }
  try{setTimeout(build,0)}catch(_){ }
}
window.fmBuildCompetitionEvidence=build;
install();
})();
