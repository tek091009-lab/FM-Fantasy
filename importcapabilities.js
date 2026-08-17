(()=>{
'use strict';
const own=(o,k)=>!!o&&Object.prototype.hasOwnProperty.call(o,k);
const nonempty=v=>v!==null&&v!==undefined&&v!=='';
const arr=v=>Array.isArray(v)?v:[];
const uniq=a=>[...new Set(a)];
function g(name,fallback){try{return typeof window[name]!=='undefined'?window[name]:fallback}catch(_){return fallback}}
function fieldCoverage(rows,keys){const out={};for(const k of keys){let n=0;for(const r of rows)if(r&&own(r,k)&&nonempty(r[k]))n++;out[k]=n}return out}
function signature(rows,keys){const seen=[];for(const k of keys){let n=0;for(const r of rows)if(r&&own(r,k)&&nonempty(r[k]))n++;if(n)seen.push(`${k}:${n}`)}return seen}
function build(){
 const players=arr(g('PLAYERS',[])), fixtures=arr(g('SEASON_FIXTURES',[])), matches=arr(g('MATCHES',[]));
 const meta=g('META',{})||{};
 const visible=players.filter(p=>p&&p.visible!==false);
 const clubs=uniq(visible.map(p=>p.club_id??p.club).filter(nonempty));
 const played=fixtures.filter(f=>f&&(f.status==='played'||Number.isFinite(Number(f.home_score))&&Number.isFinite(Number(f.away_score))));
 const richHistoryPlayers=visible.filter(p=>arr(p.history).length>0);
 const richRows=richHistoryPlayers.reduce((n,p)=>n+arr(p.history).length,0);
 const namingKeys=['legal_name','legal_full','legal_full_name','full_name','first','first_name','forename','surname_family','surname_name','football_surname','surname','family_name','last_name','common_known_as','common_name','known_as','preferred_name','nickname','shirt_name','preferred_short_name','public_name','canonical_display_name','football_display_name','display_name','name','first_pool_id','surname_pool_id','common_pool_id','name_component_evidence','name_resolution_evidence'];
 const identityKeys=['id','pid','player_id','uid','person_id','club_id','club','pos','position','price','value'];
 const availabilityKeys=['injury_status','injury_name','injury_type','injury_detail','expected_return_date','injury_return_date','injured_until','injury_days_remaining','suspension_status','suspension_remaining','suspension_games_remaining','ban_remaining','ban_games','banned_until','suspension_detail','availability_evidence'];
 const formKeys=['form','form_points','weekly_points','history','retained_history_evidence','discipline_evidence','form_evidence'];
 const fixtureKeys=['fixture_id','id','home_id','away_id','home','away','date','kickoff','gameweek','round','home_score','away_score','status','match_id'];
 const matchKeys=['id','fixture_id','gameweek','date','home','away','home_id','away_id','home_score','away_score','players','home_players','away_players'];
 const nameCov=fieldCoverage(visible,namingKeys), identityCov=fieldCoverage(visible,identityKeys), availabilityCov=fieldCoverage(visible,availabilityKeys), formCov=fieldCoverage(visible,formKeys);
 const fixtureCov=fieldCoverage(fixtures,fixtureKeys), matchCov=fieldCoverage(matches,matchKeys);
 const commonSurnameValidated=visible.filter(p=>p?.name_component_evidence?.common_plus_surname_is_validated_by_display||p?.name_resolution_evidence?.common_plus_surname_is_validated_by_display).length;
 const availabilityKnown=visible.filter(p=>['injured','suspended','clear','conflict'].includes(p?.availability_evidence?.overall_state)).length;
 const availabilityUnknown=visible.length-availabilityKnown;
 const injuryKnown=visible.filter(p=>['injured','clear','conflict'].includes(p?.availability_evidence?.injury?.state||p?.availability_evidence?.injury_state)).length;
 const suspensionKnown=visible.filter(p=>['suspended','clear','conflict'].includes(p?.availability_evidence?.suspension?.state||p?.availability_evidence?.suspension_state)).length;
 const retainedEvidencePlayers=visible.filter(p=>p?.retained_history_evidence&&typeof p.retained_history_evidence==='object').length;
 const partialHistoryPlayers=visible.filter(p=>p?.retained_history_evidence?.history_is_partial_or_unknown||p?.retained_history_evidence?.historical_coverage_may_be_partial).length;
 const disciplinePlayers=visible.filter(p=>p?.discipline_evidence&&typeof p.discipline_evidence==='object').length;
 const trustedFormPlayers=visible.filter(p=>p?.form_evidence?.safe_for_absolute_historical_comparison===true).length;
 const currentComp=meta.competition||meta.competition_name||meta.league||meta.league_name||null;
 const compId=meta.competition_id??meta.competition_fixture_id??meta.competition_uid??null;
 const season=meta.season??meta.season_id??meta.season_start_year??null;
 const humanClub=meta.human_club||meta.human_club_name||meta.manager_club||meta.user_club||null;
 const capabilities={
   version:2,
   generated_from_existing_import_pass:true,
   no_additional_fm_scan:true,
   population:{players:visible.length,clubs:clubs.length,fixtures:fixtures.length,played_fixtures:played.length,rich_matches:matches.length,players_with_rich_history:richHistoryPlayers.length,rich_history_rows:richRows},
   competition:{resolved:!!currentComp||nonempty(compId),name:currentComp,id:compId,season,human_club:humanClub,fixture_calendar_present:fixtures.length>0,played_results_present:played.length>0},
   current_database:{players_present:visible.length>0,clubs_present:clubs.length>0,identity_fields:identityCov},
   historical_detail:{rich_matches_present:matches.length>0,player_history_present:richRows>0,retained_evidence_players:retainedEvidencePlayers,partial_or_unknown_players:partialHistoryPlayers},
   availability:{explicit_evidence_players:availabilityKnown,unknown_players:availabilityUnknown,injury_known_players:injuryKnown,suspension_known_players:suspensionKnown,discipline_history_players:disciplinePlayers,field_coverage:availabilityCov},
   naming:{field_coverage:nameCov,common_plus_surname_validated:commonSurnameValidated,canonical_component_players:visible.filter(p=>p?.name_component_evidence&&typeof p.name_component_evidence==='object').length},
   form:{field_coverage:formCov,trusted_absolute_history_players:trustedFormPlayers},
   fixture_schema:{field_coverage:fixtureCov},
   rich_match_schema:{field_coverage:matchCov},
   schema_fingerprint:{
     player_fields:signature(visible,[...identityKeys,...namingKeys,...availabilityKeys,...formKeys]),
     fixture_fields:signature(fixtures,fixtureKeys),
     rich_match_fields:signature(matches,matchKeys)
   }
 };
 const gaps=[];
 if(!capabilities.competition.resolved)gaps.push('competition_identity');
 if(!fixtures.length)gaps.push('fixture_calendar');
 if(fixtures.length&&!played.length)gaps.push('played_results');
 if(!visible.length)gaps.push('player_database');
 if(played.length&&!matches.length&&!richRows)gaps.push('retained_player_match_history');
 if(visible.length&&!injuryKnown)gaps.push('current_injury_state');
 if(visible.length&&!suspensionKnown)gaps.push('current_suspension_state');
 if(!Object.values(nameCov).some(Number))gaps.push('name_components');
 if(played.length&&!trustedFormPlayers)gaps.push('trusted_historical_form');
 capabilities.unresolved_capabilities=gaps;
 capabilities.reusable_decoder_policy='Preserve successful paths. Missing capability is unknown, never zero/clear. Reuse this fingerprint when selecting additional decoders before considering another full-save scan.';
 try{window.FM_IMPORT_CAPABILITIES=capabilities}catch(_){ }
 try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.importCapabilities=capabilities;FM_DEBUG.importCapabilityFingerprint=capabilities.schema_fingerprint}}catch(_){ }
 return capabilities;
}
function install(){let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}if(original&&!original.__fmCapabilityWrapped){const wrapped=function(...args){const out=original.apply(this,args);try{if(typeof window.fmAnnotateImporterEvidence==='function')window.fmAnnotateImporterEvidence();if(typeof window.fmAnnotateFormEvidence==='function')window.fmAnnotateFormEvidence();build()}catch(e){console.warn('Import capability fingerprint failed',e)}return out};wrapped.__fmCapabilityWrapped=true;try{applyImportedPayload=wrapped}catch(_){}}try{build()}catch(_){}}
window.fmBuildImportCapabilities=build;install();
})();
