(()=>{
'use strict';
const g=(n,f)=>{try{return typeof window[n]!=='undefined'?window[n]:f}catch(_){return f}};
const norm=v=>String(v??'').trim().toLowerCase();
const MANUAL_SOURCES=new Set(['user_preference','manual','manual_override','user_override','user_selection','prompt_choice']);
const uniq=a=>[...new Set(a.filter(v=>v!==null&&v!==undefined&&v!==''))];
const clubKey=v=>String(v??'').trim();
function structuralCalendarEvidence(calendar){
  const rows=Array.isArray(calendar)?calendar.filter(Boolean):[];
  const clubs=uniq(rows.flatMap(f=>[f?.home_id??f?.home,f?.away_id??f?.away]));
  const n=clubs.length,total=rows.length,expected=n>1?n*(n-1):0;
  const directed=new Map(),undirected=new Map(),appearances=new Map();
  let invalidSelfFixtures=0,missingSideFixtures=0;
  for(const f of rows){
    const h=clubKey(f?.home_id??f?.home),a=clubKey(f?.away_id??f?.away);
    if(!h||!a){missingSideFixtures++;continue}
    if(h===a){invalidSelfFixtures++;continue}
    directed.set(`${h}>>${a}`,(directed.get(`${h}>>${a}`)||0)+1);
    const pair=h<a?`${h}<>${a}`:`${a}<>${h}`;
    undirected.set(pair,(undirected.get(pair)||0)+1);
    appearances.set(h,(appearances.get(h)||0)+1);appearances.set(a,(appearances.get(a)||0)+1);
  }
  const expectedPairs=n>1?n*(n-1)/2:0;
  const everyDirectedPairOnce=!!n&&directed.size===expected&&[...directed.values()].every(v=>v===1);
  const everyUnorderedPairTwice=!!n&&undirected.size===expectedPairs&&[...undirected.values()].every(v=>v===2);
  const expectedAppearances=n>1?2*(n-1):0;
  const balancedClubAppearances=!!n&&clubs.every(c=>(appearances.get(clubKey(c))||0)===expectedAppearances);
  const fullDoubleRoundRobin=!!expected&&total===expected&&invalidSelfFixtures===0&&missingSideFixtures===0&&everyDirectedPairOnce&&everyUnorderedPairTwice&&balancedClubAppearances;
  let candidate=null,confidence='none',reason='';
  if(fullDoubleRoundRobin&&n===20&&total===380){candidate='Premier League';confidence='strong';reason='20 clubs + 380 fixtures + every ordered home/away pairing exactly once';}
  else if(fullDoubleRoundRobin&&n===24&&total===552){candidate='EFL Championship';confidence='strong';reason='24 clubs + 552 fixtures + every ordered home/away pairing exactly once';}
  else if((n===20&&total===380)||(n===24&&total===552)){confidence='rejected_shape_only';reason='Club/fixture counts match a supported league, but pair-balance validation failed; do not use as automatic competition proof.';}
  return {club_count:n,fixture_count:total,expected_double_round_robin_fixtures:expected,expected_unique_pairs:expectedPairs,expected_appearances_per_club:expectedAppearances,invalid_self_fixtures:invalidSelfFixtures,missing_side_fixtures:missingSideFixtures,unique_directed_pairs:directed.size,unique_unordered_pairs:undirected.size,every_directed_pair_once:everyDirectedPairOnce,every_unordered_pair_twice:everyUnorderedPairTwice,balanced_club_appearances:balancedClubAppearances,full_double_round_robin:fullDoubleRoundRobin,supported_english_structural_candidate:candidate,confidence,reason};
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
  const resolvedNorm=norm(resolvedName),candidateNorm=norm(structural.supported_english_structural_candidate);
  const structuralAgrees=!!candidateNorm&&!!resolvedNorm&&(resolvedNorm.includes('premier')&&candidateNorm.includes('premier')||resolvedNorm.includes('champ')&&candidateNorm.includes('champ'));
  const structuralConflicts=!!candidateNorm&&!!resolvedNorm&&!structuralAgrees;
  const independentStructuralProof=structural.confidence==='strong'&&structuralAgrees;
  const humanClub=meta.human_club_id??meta.manager_club_id??meta.user_club_id??meta.human_club??meta.human_club_name??meta.manager_club??meta.user_club??null;
  const calendarClubKeys=new Set(calendar.flatMap(f=>[clubKey(f?.home_id??f?.home),clubKey(f?.away_id??f?.away)]).filter(Boolean));
  const humanClubInCalendar=humanClub!==null&&humanClub!==undefined&&calendarClubKeys.has(clubKey(humanClub));
  const out={version:3,competition_resolved:resolved,resolved_name:resolvedName,selection_source:source||'unknown',resolved_via_manual_override:manual,automatic_competition_detection_proven:resolved&&!manual&&source!=='unknown',automatic_competition_detection_unproven:resolved&&(manual||source==='unknown'),current_season_anchor_present:currentSeasonSupported,fixture_season_start:season,structural_calendar_evidence:structural,independent_structural_candidate:structural.supported_english_structural_candidate,independent_structural_candidate_agrees_with_resolved:structuralAgrees,independent_structural_candidate_conflicts_with_resolved:structuralConflicts,independent_structural_validation_proven:independentStructuralProof,human_managed_club_anchor:humanClub,human_managed_club_present_in_selected_calendar:humanClubInCalendar,reusable_fallback_candidate:structural.confidence==='strong'?structural.supported_english_structural_candidate:null,policy:'Preserve the existing competition decoder. A manual/user choice does not prove automatic detection. Calendar fallback is accepted only when the decoded schedule is a complete, balanced double round robin with every ordered home/away club pairing exactly once; count-only matches are rejected. Human-club membership is recorded as an additional current-season consistency check. No FM rescan is performed.'};
  try{window.FM_COMPETITION_EVIDENCE=out}catch(_){ }
  try{if(window.FM_IMPORT_CAPABILITIES){const c=window.FM_IMPORT_CAPABILITIES;c.competition_detection_evidence=out;c.competition=c.competition||{};c.competition.selection_source=out.selection_source;c.competition.automatic_detection_proven=out.automatic_competition_detection_proven;c.competition.resolved_via_manual_override=out.resolved_via_manual_override;c.competition.structural_calendar_evidence=structural;c.competition.independent_structural_candidate=out.independent_structural_candidate;c.competition.independent_structural_validation_proven=out.independent_structural_validation_proven;c.competition.human_managed_club_present_in_selected_calendar=humanClubInCalendar;c.unresolved_capabilities=Array.isArray(c.unresolved_capabilities)?c.unresolved_capabilities:[];if(out.automatic_competition_detection_unproven&&!c.unresolved_capabilities.includes('automatic_current_season_competition_detection'))c.unresolved_capabilities.push('automatic_current_season_competition_detection');if(structuralConflicts&&!c.unresolved_capabilities.includes('competition_structural_conflict'))c.unresolved_capabilities.push('competition_structural_conflict');if(structural.confidence==='rejected_shape_only'&&!c.unresolved_capabilities.includes('competition_calendar_pair_balance'))c.unresolved_capabilities.push('competition_calendar_pair_balance');if(humanClub!==null&&humanClub!==undefined&&!humanClubInCalendar&&!c.unresolved_capabilities.includes('human_club_current_season_calendar_mismatch'))c.unresolved_capabilities.push('human_club_current_season_calendar_mismatch');}}catch(_){ }
  try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.competitionDetectionEvidence=out}}catch(_){ }
  return out;
}
function install(){let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}if(original&&!original.__fmCompetitionEvidenceWrapped){const wrapped=function(...args){const out=original.apply(this,args);try{setTimeout(build,0)}catch(_){ }return out};wrapped.__fmCompetitionEvidenceWrapped=true;try{applyImportedPayload=wrapped}catch(_){ }}try{setTimeout(build,0)}catch(_){ }}
window.fmInferCompetitionFromCalendar=structuralCalendarEvidence;window.fmBuildCompetitionEvidence=build;install();
})();
