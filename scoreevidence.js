(()=>{
'use strict';
const own=(o,k)=>!!o&&Object.prototype.hasOwnProperty.call(o,k);
const nonblank=v=>v!==null&&v!==undefined&&String(v).trim()!=='';
const norm=v=>String(v??'').trim().toLowerCase();
const finiteScore=v=>nonblank(v)&&Number.isFinite(Number(v));
const futureStates=new Set(['future','upcoming','scheduled','not_played','unplayed','postponed','cancelled','canceled']);
const playedStates=new Set(['played','finished','complete','completed','result']);
function fixtureIsPlayed(f){
 if(!f)return false;
 const st=norm(f.status);
 if(futureStates.has(st))return false;
 if(playedStates.has(st))return true;
 if(st==='undecoded')return finiteScore(f.home_score)&&finiteScore(f.away_score);
 return finiteScore(f.home_score)&&finiteScore(f.away_score);
}
function sameScore(a,b){return finiteScore(a?.home_score)&&finiteScore(a?.away_score)&&finiteScore(b?.home_score)&&finiteScore(b?.away_score)&&Number(a.home_score)===Number(b.home_score)&&Number(a.away_score)===Number(b.away_score)}
function fixtureCovered(f,matches){
 if(!f)return false;
 const mid=f.match_id;
 if(nonblank(mid)&&matches.some(m=>nonblank(m?.id)&&String(m.id)===String(mid)))return true;
 const fid=f.fixture_id??f.id;
 if(nonblank(fid)&&matches.some(m=>nonblank(m?.fixture_id)&&String(m.fixture_id)===String(fid)))return true;
 const fh=nonblank(f.home_id)?String(f.home_id):norm(f.home),fa=nonblank(f.away_id)?String(f.away_id):norm(f.away);
 const fd=String(f.date??f.kickoff??'').slice(0,10),fgw=Number(f.gameweek??f.round??0)||0;
 return matches.some(m=>{
  const mh=nonblank(m?.home_id)?String(m.home_id):norm(m?.home),ma=nonblank(m?.away_id)?String(m.away_id):norm(m?.away);
  if(!fh||!fa||fh!==mh||fa!==ma||!sameScore(f,m))return false;
  const md=String(m?.date??'').slice(0,10),mgw=Number(m?.gameweek??m?.round??0)||0;
  if(fd&&md)return fd===md;
  if(fgw&&mgw)return fgw===mgw;
  return false;
 });
}
function build(){
 const fixtures=Array.isArray(window.SEASON_FIXTURES)?window.SEASON_FIXTURES:[];
 const matches=Array.isArray(window.MATCHES)?window.MATCHES:[];
 const strictPlayed=fixtures.filter(fixtureIsPlayed);
 const legacyNumericCandidates=fixtures.filter(f=>Number.isFinite(Number(f?.home_score))&&Number.isFinite(Number(f?.away_score)));
 const blankScoreFalsePositives=fixtures.filter(f=>!nonblank(f?.home_score)||!nonblank(f?.away_score)).filter(f=>Number.isFinite(Number(f?.home_score))&&Number.isFinite(Number(f?.away_score)));
 const futureNumericRejected=fixtures.filter(f=>futureStates.has(norm(f?.status))&&finiteScore(f?.home_score)&&finiteScore(f?.away_score));
 const covered=strictPlayed.filter(f=>fixtureCovered(f,matches));
 const uncovered=Math.max(0,strictPlayed.length-covered.length);
 const ratio=strictPlayed.length?covered.length/strictPlayed.length:null;
 const out={version:1,no_additional_fm_scan:true,strict_played_fixtures:strictPlayed.length,strict_rich_covered_played_fixtures:covered.length,strict_rich_uncovered_played_fixtures:uncovered,strict_rich_coverage_ratio:ratio,strict_rich_coverage_complete:strictPlayed.length>0&&uncovered===0,legacy_numeric_score_candidates:legacyNumericCandidates.length,blank_or_null_score_false_positive_risk:blankScoreFalsePositives.length,future_numeric_score_rows_rejected:futureNumericRejected.length,policy:'Blank/null score fields are never results. Explicit future/upcoming/scheduled states cannot become played merely because a schema stores numeric placeholders such as 0-0. Undecoded rows count as played only when both score fields are genuinely present. Existing recovered rich matches remain preserved.'};
 try{window.FM_SCORE_EVIDENCE=out}catch(_){ }
 try{const c=window.FM_IMPORT_CAPABILITIES;if(c){c.score_evidence=out;c.population=c.population||{};c.population.played_fixtures=strictPlayed.length;c.historical_detail=c.historical_detail||{};Object.assign(c.historical_detail,{played_fixtures_with_rich_detail:covered.length,played_fixtures_without_rich_detail:uncovered,played_fixture_detail_coverage_ratio:ratio,played_fixture_detail_coverage_complete:out.strict_rich_coverage_complete,played_fixture_classification:'strict_nonblank_score_or_explicit_played_state'});c.unresolved_capabilities=Array.isArray(c.unresolved_capabilities)?c.unresolved_capabilities:[];c.unresolved_capabilities=c.unresolved_capabilities.filter(x=>x!=='retained_player_match_history_complete'&&x!=='played_results');if(strictPlayed.length===0&&fixtures.length)c.unresolved_capabilities.push('played_results');if(strictPlayed.length&&!out.strict_rich_coverage_complete)c.unresolved_capabilities.push('retained_player_match_history_complete');c.unresolved_capabilities=[...new Set(c.unresolved_capabilities)];}}
 catch(_){ }
 try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.scoreClassificationEvidence=out;FM_DEBUG.retainedHistoryCoverage={covered_played_fixtures:covered.length,uncovered_played_fixtures:uncovered,coverage_ratio:ratio,complete:out.strict_rich_coverage_complete,classification:'strict'}}}catch(_){ }
 return out;
}
function install(){let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}if(original&&!original.__fmScoreEvidenceWrapped){const wrapped=function(...args){const out=original.apply(this,args);try{setTimeout(build,0)}catch(_){ }return out};wrapped.__fmScoreEvidenceWrapped=true;try{applyImportedPayload=wrapped}catch(_){ }}try{setTimeout(build,0)}catch(_){ }}
window.fmFixtureIsStrictlyPlayed=fixtureIsPlayed;window.fmBuildScoreEvidence=build;install();
})();
