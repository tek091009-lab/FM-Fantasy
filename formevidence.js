(()=>{
  'use strict';

  const clean=v=>String(v??'').trim();
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const uniqueSorted=arr=>[...new Set(arr.filter(v=>v!==null&&v!==undefined&&v!=='').map(v=>Number(v)).filter(Number.isFinite))].sort((a,b)=>a-b);

  function playerHistory(p){return Array.isArray(p?.history)?p.history.filter(x=>x&&typeof x==='object'):[]}

  function formEvidence(p){
    const history=playerHistory(p);
    const retained=p?.retained_history_evidence&&typeof p.retained_history_evidence==='object'?p.retained_history_evidence:null;
    // v63 canonical retained-history keys are decoded_rows / decoded_gameweeks /
    // history_is_partial_or_unknown. Keep the older aliases as fallbacks.
    const decodedGws=uniqueSorted([
      ...history.map(h=>h.gameweek),
      ...(Array.isArray(retained?.decoded_gameweeks)?retained.decoded_gameweeks:[])
    ]);
    const decodedMatches=history.length;
    const weekly=p&&p.weekly_points&&typeof p.weekly_points==='object'?p.weekly_points:{};
    const weeklyGws=uniqueSorted(Object.keys(weekly));
    const explicitForm=num(p?.form_points??p?.form);
    const declaredPartial=!!(retained?.history_is_partial_or_unknown??retained?.historical_coverage_may_be_partial);
    const recoveredRows=num(retained?.decoded_rows??retained?.decoded_rich_history_rows);
    const evidenceRows=recoveredRows!==null?recoveredRows:decodedMatches;
    const currentGw=(()=>{try{return Number(state?.currentGameweek||META?.current_gameweek||0)||null}catch(_){return null}})();
    const completedGw=(()=>{try{return Number(META?.completed_gameweek||0)||null}catch(_){return null}})();
    const expectedThrough=completedGw||currentGw;
    const gaps=[];
    if(expectedThrough&&decodedGws.length){
      const first=Math.max(1,Math.min(...decodedGws));
      for(let gw=first;gw<=expectedThrough;gw++)if(!decodedGws.includes(gw)&&!weeklyGws.includes(gw))gaps.push(gw);
    }
    const zeroHistory=evidenceRows===0;
    const partial=declaredPartial||gaps.length>0||zeroHistory;
    let state='unknown';
    if(evidenceRows>0&&!partial)state='complete_decoded_window';
    else if(evidenceRows>0)state='partial_decoded_window';
    else if(explicitForm!==null)state='numeric_without_decoded_history';
    return {
      state,
      explicit_form_value:explicitForm,
      decoded_match_rows:evidenceRows,
      decoded_gameweeks:decodedGws,
      weekly_points_gameweeks:weeklyGws,
      expected_through_gameweek:expectedThrough,
      apparent_missing_gameweeks:gaps,
      historical_coverage_may_be_partial:partial,
      safe_for_absolute_historical_comparison:state==='complete_decoded_window',
      safe_for_recent_form_display:state==='complete_decoded_window'||state==='partial_decoded_window',
      missing_history_is_not_zero_form:true,
      canonical_retained_evidence_consumed:!!retained&&(Object.prototype.hasOwnProperty.call(retained,'decoded_rows')||Object.prototype.hasOwnProperty.call(retained,'history_is_partial_or_unknown')),
      retained_first_decoded_date:retained?.first_decoded_date??null,
      retained_last_decoded_date:retained?.last_decoded_date??null,
      zero_stats_are_observed_only_within_decoded_rows:retained?.zero_stats_are_observed_only_within_decoded_rows!==false,
      source:'existing_import_payload_only'
    };
  }

  function tatyProbe(p){
    const pid=String(p?.pid??p?.player_id??'');
    const name=clean(p?.public_name||p?.canonical_display_name||p?.football_display_name||p?.display_name||p?.name);
    if(pid!=='24517'&&!/taty\s+castellanos/i.test(name))return null;
    const nc=p?.name_component_evidence&&typeof p.name_component_evidence==='object'?p.name_component_evidence:{};
    const common=clean(nc.common_name||nc.common_known_as||p?.common_name||p?.known_as||p?.preferred_name);
    const surname=clean(nc.surname_name||nc.surname_family||p?.surname_name||p?.football_surname||p?.surname||p?.family_name||p?.last_name);
    const legal=clean(nc.legal_name||nc.legal_full||p?.legal_name||p?.legal_full_name||p?.full_name);
    const first=clean(nc.first_name||nc.first||p?.first_name||p?.forename);
    const candidate=common&&surname?`${common} ${surname}`:'';
    return {
      player_id:pid||null,
      resolved_display:name||null,
      legal_name:legal||null,
      first_name_component:first||null,
      common_or_known_as:common||null,
      surname_component:surname||null,
      common_plus_surname_candidate:candidate||null,
      exact_target_display:name.toLocaleLowerCase()==='taty castellanos',
      common_plus_surname_validated:!!candidate&&name.toLocaleLowerCase()===candidate.toLocaleLowerCase(),
      rejects_common_only:!!common&&name.toLocaleLowerCase()!==common.toLocaleLowerCase(),
      keeps_legal_identity_separate:!!legal&&!!name&&legal.toLocaleLowerCase()!==name.toLocaleLowerCase(),
      canonical_importer_components_consumed:!!(nc.legal_full||nc.first||nc.surname_family||nc.common_known_as),
      source:'validation_probe_only_no_display_override'
    };
  }

  function annotate(){
    let players;try{players=typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)?PLAYERS:null}catch(_){players=null}
    if(!players)return {players:0,completeForm:0,partialForm:0,numericWithoutHistory:0,taty:null};
    const stats={players:0,completeForm:0,partialForm:0,numericWithoutHistory:0,unknownForm:0,canonicalRetainedEvidenceConsumed:0,taty:null};
    for(const p of players){
      if(!p||typeof p!=='object')continue;
      p.form_evidence=formEvidence(p);
      stats.players++;
      if(p.form_evidence.state==='complete_decoded_window')stats.completeForm++;
      else if(p.form_evidence.state==='partial_decoded_window')stats.partialForm++;
      else if(p.form_evidence.state==='numeric_without_decoded_history')stats.numericWithoutHistory++;
      else stats.unknownForm++;
      if(p.form_evidence.canonical_retained_evidence_consumed)stats.canonicalRetainedEvidenceConsumed++;
      const probe=tatyProbe(p);if(probe)stats.taty=probe;
    }
    try{
      if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){
        FM_DEBUG.formEvidence=stats;
        FM_DEBUG.formEvidencePolicy='Form consumes the canonical retained-history evidence when available; partial retained history stays partial and missing historical rows never count as zero form.';
        if(stats.taty)FM_DEBUG.tatyNameValidation=stats.taty;
      }
    }catch(_){/* debug optional */}
    return stats;
  }

  function install(){
    let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
    if(original&&!original.__fmFormEvidenceWrapped){
      const wrapped=function(...args){const out=original.apply(this,args);try{annotate()}catch(e){console.warn('Form evidence annotation failed',e)}return out};
      wrapped.__fmFormEvidenceWrapped=true;
      try{applyImportedPayload=wrapped}catch(_){/* immutable binding */}
    }
    try{annotate()}catch(e){console.warn('Initial form evidence annotation failed',e)}
  }

  window.fmAnnotateFormEvidence=annotate;
  install();
})();
