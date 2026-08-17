(()=>{
  'use strict';

  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const has=(o,k)=>o&&Object.prototype.hasOwnProperty.call(o,k)&&o[k]!==null&&o[k]!==undefined&&o[k]!=='';

  function injuryEvidence(p){
    const explicitKeys=['injury_status','injury_name','injury_type','injury_detail','expected_return_date','injury_return_date','injured_until','injury_days_remaining'];
    const observed=explicitKeys.some(k=>has(p,k));
    const rawStatus=clean(p.injury_status).toLowerCase();
    const named=clean(p.injury_name||p.injury_type||p.injury_detail);
    const returnDate=clean(p.expected_return_date||p.injury_return_date||p.injured_until);
    const days=num(p.injury_days_remaining);
    let state='unknown';
    if(observed){
      if(named||returnDate||(days!==null&&days>0)||/(injur|out|unavailable|rehab)/.test(rawStatus))state='injured';
      else if(/^(fit|healthy|available|none|clear|0|false)$/.test(rawStatus)||(days!==null&&days<=0))state='clear';
      else state='observed_unknown';
    }
    return {
      state,
      observed,
      source:observed?'fm_importer_explicit':'not_decoded',
      detail:named||null,
      expected_return:returnDate||null,
      days_remaining:days,
      safe_to_treat_as_clear:state==='clear'
    };
  }

  function suspensionEvidence(p){
    const explicitKeys=['suspension_status','suspension_remaining','suspension_games_remaining','ban_remaining','ban_games','banned_until','suspension_detail'];
    const observed=explicitKeys.some(k=>has(p,k));
    const rawStatus=clean(p.suspension_status).toLowerCase();
    const remaining=[p.suspension_remaining,p.suspension_games_remaining,p.ban_remaining,p.ban_games].map(num).find(v=>v!==null)??null;
    const until=clean(p.banned_until);
    const detail=clean(p.suspension_detail);
    let state='unknown';
    if(observed){
      if((remaining!==null&&remaining>0)||until||detail||/(suspend|ban|unavailable)/.test(rawStatus))state='suspended';
      else if(/^(clear|available|none|0|false)$/.test(rawStatus)||(remaining!==null&&remaining<=0))state='clear';
      else state='observed_unknown';
    }
    const discipline=p.discipline_evidence&&typeof p.discipline_evidence==='object'?p.discipline_evidence:null;
    return {
      state,
      observed,
      source:observed?'fm_importer_explicit':discipline?'decoded_match_cards_only':'not_decoded',
      games_remaining:remaining,
      until:until||null,
      detail:detail||null,
      card_history_available:!!discipline,
      card_history_does_not_imply_active_ban:!!discipline&&!observed,
      safe_to_treat_as_clear:state==='clear'
    };
  }

  function namingEvidence(p){
    const existing=p.name_component_evidence&&typeof p.name_component_evidence==='object'?p.name_component_evidence:{};
    const legal=clean(p.legal_name||p.legal_full_name||p.full_name||existing.legal_name);
    const first=clean(p.first_name||p.forename||existing.first_name);
    const surname=clean(p.surname_name||p.football_surname||p.surname||p.family_name||p.last_name||existing.surname_name);
    const common=clean(p.common_name||p.known_as||p.preferred_name||existing.common_name);
    const display=clean(p.public_name||p.canonical_display_name||p.football_display_name||p.display_name||p.name);
    return {
      legal_name:legal||null,
      first_name:first||null,
      surname_name:surname||null,
      common_name:common||null,
      nickname:clean(p.nickname||existing.nickname)||null,
      shirt_name:clean(p.shirt_name||existing.shirt_name)||null,
      preferred_short_name:clean(p.preferred_short_name||existing.preferred_short_name)||null,
      resolved_display_name:display||null,
      component_pool_ids:existing.component_pool_ids||{
        first_name:p.first_name_pool_id??null,
        surname:p.surname_pool_id??p.surname_name_pool_id??null,
        common_name:p.common_name_pool_id??null
      },
      preserves_legal_identity_separately:!!legal&&!!display,
      common_plus_surname_candidate:common&&surname&&common.toLowerCase()!==surname.toLowerCase()?`${common} ${surname}`:null
    };
  }

  function annotatePlayers(){
    let players;
    try{players=typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)?PLAYERS:null}catch(_){players=null}
    if(!players)return {players:0,injuryObserved:0,suspensionObserved:0,availabilityUnknown:0,nameEvidence:0};
    const stats={players:0,injuryObserved:0,suspensionObserved:0,availabilityUnknown:0,nameEvidence:0};
    for(const p of players){
      if(!p||typeof p!=='object')continue;
      const injury=injuryEvidence(p),suspension=suspensionEvidence(p);
      p.availability_evidence={
        injury,
        suspension,
        overall_state:injury.state==='injured'?'injured':suspension.state==='suspended'?'suspended':injury.state==='clear'&&suspension.state==='clear'?'clear':'unknown',
        unknown_is_not_available:true,
        generated_from_existing_import_pass:true
      };
      p.name_component_evidence=Object.assign({},p.name_component_evidence||{},namingEvidence(p));
      stats.players++;
      if(injury.observed)stats.injuryObserved++;
      if(suspension.observed)stats.suspensionObserved++;
      if(p.availability_evidence.overall_state==='unknown')stats.availabilityUnknown++;
      if(p.name_component_evidence.resolved_display_name)stats.nameEvidence++;
    }
    try{
      if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){
        FM_DEBUG.availabilityEvidence=stats;
        FM_DEBUG.availabilityEvidencePolicy='Unknown injury/ban state is preserved as unknown; decoded card history alone never creates an active suspension.';
        FM_DEBUG.nameEvidencePolicy='Legal/full identity remains separate from football display identity; common/known-as + surname is evidence only, not an unconditional display rewrite.';
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
