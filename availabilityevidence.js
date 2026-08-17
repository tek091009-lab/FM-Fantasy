(()=>{
  'use strict';

  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const has=(o,k)=>o&&Object.prototype.hasOwnProperty.call(o,k)&&o[k]!==null&&o[k]!==undefined&&o[k]!=='';
  const entries=(p,keys)=>keys.filter(k=>has(p,k)).map(k=>({field:k,value:p[k]}));

  function injuryEvidence(p){
    const explicitKeys=['injury_status','injury_name','injury_type','injury_detail','expected_return_date','injury_return_date','injured_until','injury_days_remaining'];
    const observedFields=entries(p,explicitKeys);
    const observed=observedFields.length>0;
    const rawStatus=clean(p.injury_status).toLowerCase();
    const named=clean(p.injury_name||p.injury_type||p.injury_detail);
    const returnDate=clean(p.expected_return_date||p.injury_return_date||p.injured_until);
    const days=num(p.injury_days_remaining);
    const positiveSignals=[];
    const clearSignals=[];
    if(named)positiveSignals.push('named_injury');
    if(returnDate)positiveSignals.push('return_date');
    if(days!==null&&days>0)positiveSignals.push('days_remaining_positive');
    if(/(injur|out|unavailable|rehab)/.test(rawStatus))positiveSignals.push('status_injured');
    if(/^(fit|healthy|available|none|clear|0|false)$/.test(rawStatus))clearSignals.push('status_clear');
    if(days!==null&&days<=0)clearSignals.push('days_remaining_zero');
    const conflict=positiveSignals.length>0&&clearSignals.length>0;
    let state='unknown';
    if(observed){
      if(conflict)state='conflict';
      else if(positiveSignals.length)state='injured';
      else if(clearSignals.length)state='clear';
      else state='observed_unknown';
    }
    return {
      state,
      observed,
      source:observed?'fm_importer_explicit':'not_decoded',
      detail:named||null,
      expected_return:returnDate||null,
      days_remaining:days,
      observed_fields:observedFields,
      positive_signals:positiveSignals,
      clear_signals:clearSignals,
      conflicting_evidence:conflict,
      safe_to_treat_as_clear:state==='clear'
    };
  }

  function suspensionEvidence(p){
    const explicitKeys=['suspension_status','suspension_remaining','suspension_games_remaining','ban_remaining','ban_games','banned_until','suspension_detail'];
    const observedFields=entries(p,explicitKeys);
    const observed=observedFields.length>0;
    const rawStatus=clean(p.suspension_status).toLowerCase();
    const remainingValues=['suspension_remaining','suspension_games_remaining','ban_remaining','ban_games'].filter(k=>has(p,k)).map(k=>({field:k,value:num(p[k])})).filter(x=>x.value!==null);
    const remaining=remainingValues.length?remainingValues[0].value:null;
    const until=clean(p.banned_until);
    const detail=clean(p.suspension_detail);
    const positiveSignals=[];
    const clearSignals=[];
    if(remainingValues.some(x=>x.value>0))positiveSignals.push('games_remaining_positive');
    if(until)positiveSignals.push('banned_until');
    if(detail)positiveSignals.push('suspension_detail');
    if(/(suspend|ban|unavailable)/.test(rawStatus))positiveSignals.push('status_suspended');
    if(/^(clear|available|none|0|false)$/.test(rawStatus))clearSignals.push('status_clear');
    if(remainingValues.length&&remainingValues.every(x=>x.value<=0))clearSignals.push('games_remaining_zero');
    const numericConflict=remainingValues.some(x=>x.value>0)&&remainingValues.some(x=>x.value<=0);
    const conflict=numericConflict||(positiveSignals.length>0&&clearSignals.length>0);
    let state='unknown';
    if(observed){
      if(conflict)state='conflict';
      else if(positiveSignals.length)state='suspended';
      else if(clearSignals.length)state='clear';
      else state='observed_unknown';
    }
    const discipline=p.discipline_evidence&&typeof p.discipline_evidence==='object'?p.discipline_evidence:null;
    return {
      state,
      observed,
      source:observed?'fm_importer_explicit':discipline?'decoded_match_cards_only':'not_decoded',
      games_remaining:remaining,
      games_remaining_sources:remainingValues,
      until:until||null,
      detail:detail||null,
      observed_fields:observedFields,
      positive_signals:positiveSignals,
      clear_signals:clearSignals,
      conflicting_evidence:conflict,
      card_history_available:!!discipline,
      card_history_does_not_imply_active_ban:!!discipline&&!observed,
      safe_to_treat_as_clear:state==='clear'
    };
  }

  function namingEvidence(p){
    const existing=p.name_component_evidence&&typeof p.name_component_evidence==='object'?p.name_component_evidence:{};
    // v63 Python canonical keys are legal_full/first/surname_family/common_known_as.
    // Retain compatibility with earlier evidence aliases rather than replacing them.
    const legal=clean(p.legal_name||p.legal_full_name||p.full_name||existing.legal_name||existing.legal_full);
    const first=clean(p.first_name||p.forename||existing.first_name||existing.first);
    const surname=clean(p.surname_name||p.football_surname||p.surname||p.family_name||p.last_name||existing.surname_name||existing.surname_family);
    const common=clean(p.common_name||p.known_as||p.preferred_name||existing.common_name||existing.common_known_as);
    const display=clean(p.public_name||p.canonical_display_name||p.football_display_name||p.display_name||p.name);
    const commonSurname=common&&surname&&common.toLowerCase()!==surname.toLowerCase()?`${common} ${surname}`:'';
    const lower=s=>clean(s).toLocaleLowerCase();
    const relation={
      display_equals_legal:!!display&&!!legal&&lower(display)===lower(legal),
      display_equals_first_surname:!!display&&!!first&&!!surname&&lower(display)===lower(`${first} ${surname}`),
      display_equals_common:!!display&&!!common&&lower(display)===lower(common),
      display_equals_common_surname:!!display&&!!commonSurname&&lower(display)===lower(commonSurname),
      display_contains_common:!!display&&!!common&&lower(display).includes(lower(common)),
      display_contains_surname:!!display&&!!surname&&lower(display).includes(lower(surname))
    };
    let resolvedRelationship='unclassified';
    if(relation.display_equals_common_surname)resolvedRelationship='common_plus_surname_exact';
    else if(relation.display_equals_first_surname)resolvedRelationship='first_plus_surname_exact';
    else if(relation.display_equals_legal)resolvedRelationship='legal_exact';
    else if(relation.display_equals_common)resolvedRelationship='common_only_exact';
    else if(relation.display_contains_common&&relation.display_contains_surname)resolvedRelationship='common_and_surname_present';
    const existingPoolIds=existing.component_pool_ids&&typeof existing.component_pool_ids==='object'?existing.component_pool_ids:{};
    return {
      legal_name:legal||null,
      first_name:first||null,
      surname_name:surname||null,
      common_name:common||null,
      nickname:clean(p.nickname||existing.nickname)||null,
      shirt_name:clean(p.shirt_name||existing.shirt_name)||null,
      preferred_short_name:clean(p.preferred_short_name||existing.preferred_short_name)||null,
      resolved_display_name:display||null,
      component_pool_ids:{
        first_name:p.first_name_pool_id??p.first_name_id??existingPoolIds.first_name??existing.first_pool_id??null,
        surname:p.surname_pool_id??p.surname_name_pool_id??p.surname_name_id??existingPoolIds.surname??existing.surname_pool_id??null,
        common_name:p.common_name_pool_id??p.common_name_id??existingPoolIds.common_name??existing.common_pool_id??null
      },
      preserves_legal_identity_separately:!!legal&&!!display,
      common_plus_surname_candidate:commonSurname||null,
      relationship_evidence:relation,
      resolved_relationship:resolvedRelationship,
      common_plus_surname_is_validated_by_display:resolvedRelationship==='common_plus_surname_exact',
      canonical_importer_components_consumed:!!(existing.legal_full||existing.first||existing.surname_family||existing.common_known_as),
      schema:existing.schema||'compatible_name_evidence_v2'
    };
  }

  function annotatePlayers(){
    let players;
    try{players=typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)?PLAYERS:null}catch(_){players=null}
    if(!players)return {players:0,injuryObserved:0,suspensionObserved:0,availabilityUnknown:0,availabilityConflicts:0,nameEvidence:0,commonSurnameValidated:0,canonicalNameComponentsConsumed:0};
    const stats={players:0,injuryObserved:0,suspensionObserved:0,availabilityUnknown:0,availabilityConflicts:0,nameEvidence:0,commonSurnameValidated:0,canonicalNameComponentsConsumed:0};
    for(const p of players){
      if(!p||typeof p!=='object')continue;
      const injury=injuryEvidence(p),suspension=suspensionEvidence(p);
      const overall=injury.state==='injured'?'injured':suspension.state==='suspended'?'suspended':injury.state==='conflict'||suspension.state==='conflict'?'conflict':injury.state==='clear'&&suspension.state==='clear'?'clear':'unknown';
      p.availability_evidence={
        injury,
        suspension,
        overall_state:overall,
        unknown_is_not_available:true,
        conflicting_evidence_is_not_clear:true,
        generated_from_existing_import_pass:true
      };
      p.name_component_evidence=Object.assign({},p.name_component_evidence||{},namingEvidence(p));
      stats.players++;
      if(injury.observed)stats.injuryObserved++;
      if(suspension.observed)stats.suspensionObserved++;
      if(overall==='unknown')stats.availabilityUnknown++;
      if(overall==='conflict')stats.availabilityConflicts++;
      if(p.name_component_evidence.resolved_display_name)stats.nameEvidence++;
      if(p.name_component_evidence.common_plus_surname_is_validated_by_display)stats.commonSurnameValidated++;
      if(p.name_component_evidence.canonical_importer_components_consumed)stats.canonicalNameComponentsConsumed++;
    }
    try{
      if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){
        FM_DEBUG.availabilityEvidence=stats;
        FM_DEBUG.availabilityEvidencePolicy='Unknown injury/ban state stays unknown; conflicting explicit fields stay conflict; decoded card history alone never creates an active suspension.';
        FM_DEBUG.nameEvidencePolicy='Legal identity remains separate from football display identity; v63 canonical name components are consumed when present; common/known-as + surname is only marked validated when the resolved display exactly confirms it.';
      }
    }catch(_){/* debug is optional */}
    return stats;
  }

  function install(){
    let original;
    try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
    if(original&&!original.__fmAvailabilityEvidenceWrapped){
      const wrapped=function(...args){const out=original.apply(this,args);try{annotatePlayers()}catch(e){console.warn('Availability evidence annotation failed',e)}return out};
      wrapped.__fmAvailabilityEvidenceWrapped=true;
      try{applyImportedPayload=wrapped}catch(_){/* global binding may be immutable */}
    }
    try{annotatePlayers()}catch(e){console.warn('Initial availability evidence annotation failed',e)}
  }

  window.fmAnnotateImporterEvidence=annotatePlayers;
  install();
})();
