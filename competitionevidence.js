(()=>{
'use strict';
const g=(n,f)=>{try{return typeof window[n]!=='undefined'?window[n]:f}catch(_){return f}};
const norm=v=>String(v??'').trim().toLowerCase();
const MANUAL_SOURCES=new Set(['user_preference','manual','manual_override','user_override','user_selection','prompt_choice']);
const uniq=a=>[...new Set(a.filter(v=>v!==null&&v!==undefined&&v!==''))];
function structuralCalendarEvidence(calendar){
  const clubs=uniq(calendar.flatMap(f=>[f?.home_id??f?.home,f?.away_id??f?.away]));
  const n=clubs.length, total=calendar.length, expected=n>1?n*(n-1):0;
  const fullDoubleRoundRobin=!!expected&&total===expected;
  let candidate=null, confidence='none', reason='';
  if(fullDoubleRoundRobin&&n===20&&total===380){candidate='Premier League';confidence='strong';reason='20 unique clubs + 380 fixtures = complete 20-team double round robin';}
  else if(fullDoubleRoundRobin&&n===24&&total===552){candidate='EFL Championship';confidence='strong';reason='24 unique clubs + 552 fixtures = complete 24-team double round robin';}
  return {club_count:n,fixture_count:total,expected_double_round_robin_fixtures:expected,full_double_round_robin:fullDoubleRoundRobin,supported_english_structural_candidate:candidate,confidence,reason};
}
function build(){
  const meta=g('META',{})||{};
  const source=norm(meta.league_selection_source||meta.competition_selection_source||meta.league_source||meta.competition_source||'unknown');
  const resolvedName=meta.competition||meta.competition_name||meta.league||meta.league_name||null;
  const resolved=!!(resolvedName||meta.competition_fixture_id||meta.competition_id);
  const manual=MANUAL_SOURCES.has(source)||source.includes('user_preference')||source.includes('manual')||source.includes('override');
  const season=meta.fixture_season_start??meta.season_start_year??meta.season??meta.season_id??null;
  const calendar=Array.isArray(g('SEASON_FIXTURES',[]))?g('SEASON_FIXTURES',[]):[];
  const currentSeasonSupported=season!==null&&season!==undefined&&calendar.length>0;
  const structural=structuralCalendarEvidence(calendar);
  const resolvedNorm=norm(resolvedName);
  const candidateNorm=norm(structural.supported_english_structural_candidate);
  const structuralAgrees=!!candidateNorm&&!!resolvedNorm&&(resolvedNorm.includes('premier')&&candidateNorm.includes('premier')||resolvedNorm.includes('champ')&&candidateNorm.includes('champ'));
  const structuralConflicts=!!candidateNorm&&!!resolvedNorm&&!structuralAgrees;
  const independentStructuralProof=structural.confidence==='strong'&&structuralAgrees;
  const out={
    version:2,
    competition_resolved:resolved,
    resolved_name:resolvedName,
    selection_source:source||'unknown',
    resolved_via_manual_override:manual,
    automatic_competition_detection_proven:resolved&&!manual&&source!=='unknown',
    automatic_competition_detection_unproven:resolved&&(manual||source==='unknown'),
    current_season_anchor_present:currentSeasonSupported,
    fixture_season_start:season,
    structural_calendar_evidence:structural,
    independent_structural_candidate:structural.supported_english_structural_candidate,
    independent_structural_candidate_agrees_with_resolved:structuralAgrees,
    independent_structural_candidate_conflicts_with_resolved:structuralConflicts,
    independent_structural_validation_proven:independentStructuralProof,
    reusable_fallback_candidate:structural.confidence==='strong'?structural.supported_english_structural_candidate:null,
    policy:'Preserve the existing competition decoder. A manual/user choice does not prove automatic detection, but the already-decoded full calendar can independently yield a conservative supported-English fallback candidate when it is a complete 20-team/380-fixture or 24-team/552-fixture double round robin. Structural evidence validates or challenges a resolved league without rescanning the FM save.'
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
      c.competition.structural_calendar_evidence=structural;
      c.competition.independent_structural_candidate=out.independent_structural_candidate;
      c.competition.independent_structural_validation_proven=out.independent_structural_validation_proven;
      c.unresolved_capabilities=Array.isArray(c.unresolved_capabilities)?c.unresolved_capabilities:[];
      if(out.automatic_competition_detection_unproven&&!c.unresolved_capabilities.includes('automatic_current_season_competition_detection'))c.unresolved_capabilities.push('automatic_current_season_competition_detection');
      if(structuralConflicts&&!c.unresolved_capabilities.includes('competition_structural_conflict'))c.unresolved_capabilities.push('competition_structural_conflict');
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
window.fmInferCompetitionFromCalendar=structuralCalendarEvidence;
window.fmBuildCompetitionEvidence=build;
install();
})();
