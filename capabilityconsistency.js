(()=>{
'use strict';
const clean=v=>String(v??'').trim();
const norm=v=>clean(v).toLocaleLowerCase();
const nonblank=v=>v!==null&&v!==undefined&&clean(v)!=='';
const finite=v=>nonblank(v)&&Number.isFinite(Number(v));
const futureStates=new Set(['future','upcoming','scheduled','not_played','unplayed','postponed','cancelled','canceled']);
const playedStates=new Set(['played','finished','complete','completed','result']);
function strictPlayed(f){
 try{if(typeof window.fmFixtureIsStrictlyPlayed==='function')return !!window.fmFixtureIsStrictlyPlayed(f)}catch(_){}
 if(!f)return false;
 const st=norm(f.status);
 if(futureStates.has(st))return false;
 if(playedStates.has(st))return true;
 return finite(f.home_score)&&finite(f.away_score);
}
function sameScore(a,b){return finite(a?.home_score)&&finite(a?.away_score)&&finite(b?.home_score)&&finite(b?.away_score)&&Number(a.home_score)===Number(b.home_score)&&Number(a.away_score)===Number(b.away_score)}
function covered(f,matches){
 if(!f)return false;
 if(nonblank(f.match_id)&&matches.some(m=>nonblank(m?.id)&&String(m.id)===String(f.match_id)))return true;
 const fid=f.fixture_id??f.id;
 if(nonblank(fid)&&matches.some(m=>nonblank(m?.fixture_id)&&String(m.fixture_id)===String(fid)))return true;
 const fh=nonblank(f.home_id)?String(f.home_id):norm(f.home),fa=nonblank(f.away_id)?String(f.away_id):norm(f.away);
 const fd=clean(f.date??f.kickoff).slice(0,10),fgw=Number(f.gameweek??f.round??0)||0;
 return matches.some(m=>{
  const mh=nonblank(m?.home_id)?String(m.home_id):norm(m?.home),ma=nonblank(m?.away_id)?String(m.away_id):norm(m?.away);
  if(!fh||!fa||fh!==mh||fa!==ma||!sameScore(f,m))return false;
  const md=clean(m?.date).slice(0,10),mgw=Number(m?.gameweek??m?.round??0)||0;
  if(fd&&md)return fd===md;
  if(fgw&&mgw)return fgw===mgw;
  return false;
 });
}
function reconcile(){
 const fixtures=Array.isArray(window.SEASON_FIXTURES)?window.SEASON_FIXTURES:[];
 const matches=Array.isArray(window.MATCHES)?window.MATCHES:[];
 const players=(Array.isArray(window.PLAYERS)?window.PLAYERS:[]).filter(p=>p&&p.visible!==false);
 const played=fixtures.filter(strictPlayed),cov=played.filter(f=>covered(f,matches)),unc=Math.max(0,played.length-cov.length),ratio=played.length?cov.length/played.length:null,complete=played.length>0&&unc===0;
 let cap=window.FM_IMPORT_CAPABILITIES;
 if(!cap||typeof cap!=='object'){try{if(typeof window.fmBuildImportCapabilities==='function')cap=window.fmBuildImportCapabilities()}catch(_){}cap=window.FM_IMPORT_CAPABILITIES||{}}
 cap.version=Math.max(4,Number(cap.version)||0);
 cap.consistency_version=1;
 cap.generated_from_existing_import_pass=true;
 cap.no_additional_fm_scan=true;
 cap.population=cap.population||{};
 cap.population.played_fixtures=played.length;
 cap.historical_detail=cap.historical_detail||{};
 Object.assign(cap.historical_detail,{played_fixtures_with_rich_detail:cov.length,played_fixtures_without_rich_detail:unc,played_fixture_detail_coverage_ratio:ratio,played_fixture_detail_coverage_complete:complete,played_fixture_classification:'strict_nonblank_score_or_explicit_played_state',coverage_reconciled_after_all_evidence_layers:true});
 const gaps=Array.isArray(cap.unresolved_capabilities)?cap.unresolved_capabilities.filter(x=>x!=='played_results'&&x!=='retained_player_match_history_complete'):[];
 if(fixtures.length&&!played.length)gaps.push('played_results');
 if(played.length&&!complete)gaps.push('retained_player_match_history_complete');
 const ns=window.FM_NAME_SCHEMA_EVIDENCE&&typeof window.FM_NAME_SCHEMA_EVIDENCE==='object'?window.FM_NAME_SCHEMA_EVIDENCE:{};
 const perPlayerCross=players.filter(p=>p?.name_schema_evidence?.cross_source_common_plus_surname_validated===true).length;
 const rawComponentCounts={legal:0,first:0,surname_family:0,common_known_as:0,nickname:0,shirt_name:0,preferred_short_name:0};
 for(const p of players){const e=p?.name_component_evidence||{};if(nonblank(p.legal_full??p.legal_name??e.legal_full??e.legal_name))rawComponentCounts.legal++;if(nonblank(p.first??p.first_name??e.first??e.first_name))rawComponentCounts.first++;if(nonblank(p.surname_family??p.surname_name??p.football_surname??e.surname_family??e.surname_name))rawComponentCounts.surname_family++;if(nonblank(p.common_known_as??p.common_name??p.known_as??e.common_known_as??e.common_name))rawComponentCounts.common_known_as++;if(nonblank(p.nickname??e.nickname))rawComponentCounts.nickname++;if(nonblank(p.shirt_name??e.shirt_name))rawComponentCounts.shirt_name++;if(nonblank(p.preferred_short_name??e.preferred_short_name))rawComponentCounts.preferred_short_name++;}
 cap.naming=cap.naming||{};
 cap.naming.component_population=rawComponentCounts;
 cap.naming.cross_source_common_plus_surname_validated=Math.max(perPlayerCross,Number(ns.cross_source_common_surname_validated)||0);
 cap.naming.retained_alias_persons=Number(ns.retained_alias_persons)||0;
 cap.naming.retained_consensus_recommended=Number(ns.retained_consensus_recommended)||0;
 cap.naming.taty_validation_probe=ns.taty_probe||null;
 cap.naming.relationship_policy='Legal/full identity, first name, football surname/family component, common/known-as, nickname, shirt name and preferred short name remain separate. common/known-as + football surname is promoted only when an independent retained-match alias consensus or independently resolved FM display validates the same natural football name.';
 cap.unresolved_capabilities=[...new Set(gaps)];
 cap.reconciliation_policy='Final capability status is reconciled after score, naming and history evidence layers. Blank/null scores never create played fixtures; partial retained history remains unresolved without discarding recovered matches; naming relationships require independent evidence.';
 window.FM_IMPORT_CAPABILITIES=cap;
 const out={version:1,strict_played_fixtures:played.length,strict_rich_covered_played_fixtures:cov.length,strict_rich_uncovered_played_fixtures:unc,strict_rich_coverage_ratio:ratio,strict_rich_coverage_complete:complete,naming_component_population:rawComponentCounts,cross_source_common_plus_surname_validated:cap.naming.cross_source_common_plus_surname_validated,retained_alias_persons:cap.naming.retained_alias_persons,taty_validation_probe:cap.naming.taty_validation_probe,no_additional_fm_scan:true};
 window.FM_CAPABILITY_CONSISTENCY=out;
 try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.capabilityConsistency=out;FM_DEBUG.importCapabilities=cap;FM_DEBUG.retainedHistoryCoverage={covered_played_fixtures:cov.length,uncovered_played_fixtures:unc,coverage_ratio:ratio,complete,classification:'strict_reconciled'}}}catch(_){}
 return out;
}
function install(){let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}if(original&&!original.__fmCapabilityConsistencyWrapped){const wrapped=function(...args){const out=original.apply(this,args);try{setTimeout(reconcile,0)}catch(_){}return out};wrapped.__fmCapabilityConsistencyWrapped=true;try{applyImportedPayload=wrapped}catch(_){}}try{setTimeout(reconcile,0)}catch(_){}}
window.fmReconcileImportCapabilities=reconcile;install();
})();
