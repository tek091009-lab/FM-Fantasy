(()=>{
  'use strict';
  const clean=v=>String(v??'').trim();
  const parseDate=v=>{if(!v)return null;const d=new Date(v);return Number.isFinite(d.getTime())?d:null};
  const iso=d=>d?d.toISOString().slice(0,10):null;
  const isPlayed=f=>String(f?.status||'').toLowerCase()==='played'||Number.isFinite(Number(f?.home_score))&&Number.isFinite(Number(f?.away_score));

  function referenceDate(){
    const candidates=[];
    try{
      const m=typeof META!=='undefined'&&META?META:{};
      for(const k of ['save_date','snapshot_date','current_date','import_date','imported_save_date','game_date','today']){
        const d=parseDate(m[k]);if(d)candidates.push({date:d,source:`META.${k}`});
      }
    }catch(_){/* optional */}
    try{
      const fs=typeof SEASON_FIXTURES!=='undefined'&&Array.isArray(SEASON_FIXTURES)?SEASON_FIXTURES:[];
      for(const f of fs){if(!isPlayed(f))continue;const d=parseDate(f.date||f.match_date||f.kickoff||f.datetime);if(d)candidates.push({date:d,source:'latest_played_fixture'});}
    }catch(_){/* optional */}
    try{
      const ms=typeof MATCHES!=='undefined'&&Array.isArray(MATCHES)?MATCHES:[];
      for(const m of ms){const d=parseDate(m.date||m.match_date||m.kickoff||m.datetime);if(d)candidates.push({date:d,source:'latest_decoded_match'});}
    }catch(_){/* optional */}
    if(!candidates.length)return {date:null,source:null};
    candidates.sort((a,b)=>a.date-b.date);
    return candidates[candidates.length-1];
  }

  function liveStatusPositive(signals,kind){
    const s=new Set(signals||[]);
    return kind==='injury'?s.has('days_remaining_positive')||s.has('status_injured'):s.has('games_remaining_positive')||s.has('status_suspended');
  }

  function applyTemporalEvidence(ev,kind,ref){
    if(!ev||typeof ev!=='object')return ev;
    const dateText=kind==='injury'?ev.expected_return:ev.until;
    const dated=parseDate(dateText);
    const result=Object.assign({},ev,{reference_date:iso(ref.date),reference_date_source:ref.source||null,dated_record_expired:false,effective_state:ev.state,temporal_reason:null});
    if(!dated||!ref.date){result.temporal_reason=!dated?'no_dated_status_record':'no_save_reference_date';return result;}
    const expired=dated.getTime()<ref.date.getTime();
    result.dated_record_expired=expired;
    if(!expired){result.temporal_reason='dated_record_not_expired';return result;}
    if(liveStatusPositive(ev.positive_signals,kind)){
      result.temporal_reason='expired_date_but_independent_live_signal_present';
      return result;
    }
    if(ev.state==='injured'||ev.state==='suspended'){
      result.effective_state='stale_record_unknown';
      result.safe_to_treat_as_clear=false;
      result.temporal_reason='expired_date_without_independent_live_signal';
    }else result.temporal_reason='expired_date_nonpositive_state';
    return result;
  }

  function annotate(){
    let ps;try{ps=typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)?PLAYERS:[]}catch(_){ps=[]}
    const ref=referenceDate();
    const stats={players:0,referenceDate:iso(ref.date),referenceSource:ref.source,injuryExpired:0,suspensionExpired:0,injuryDowngradedStale:0,suspensionDowngradedStale:0};
    for(const p of ps){
      const a=p?.availability_evidence;if(!a)continue;
      a.injury=applyTemporalEvidence(a.injury,'injury',ref);
      a.suspension=applyTemporalEvidence(a.suspension,'suspension',ref);
      if(a.injury?.dated_record_expired)stats.injuryExpired++;
      if(a.suspension?.dated_record_expired)stats.suspensionExpired++;
      if(a.injury?.effective_state==='stale_record_unknown')stats.injuryDowngradedStale++;
      if(a.suspension?.effective_state==='stale_record_unknown')stats.suspensionDowngradedStale++;
      const ie=a.injury?.effective_state||a.injury?.state||'unknown',se=a.suspension?.effective_state||a.suspension?.state||'unknown';
      a.effective_overall_state=ie==='injured'?'injured':se==='suspended'?'suspended':ie==='conflict'||se==='conflict'?'conflict':ie==='clear'&&se==='clear'?'clear':ie==='stale_record_unknown'||se==='stale_record_unknown'?'unknown':'unknown';
      a.temporal_validation_applied=!!ref.date;
      stats.players++;
    }
    try{if(typeof FM_DEBUG!=='undefined'&&FM_DEBUG){FM_DEBUG.availabilityTemporalEvidence=stats;FM_DEBUG.availabilityTemporalPolicy='Expired injury-return/ban-until dates cannot by themselves prove a player is still unavailable. Without an independent live status or positive remaining-days/games signal they are downgraded to stale_record_unknown, never silently clear.';}}catch(_){/* optional */}
    return stats;
  }

  function install(){
    let original;try{original=typeof applyImportedPayload==='function'?applyImportedPayload:null}catch(_){original=null}
    if(original&&!original.__fmAvailabilityTemporalWrapped){
      const wrapped=function(...args){const out=original.apply(this,args);try{annotate()}catch(e){console.warn('Availability temporal annotation failed',e)}return out};
      wrapped.__fmAvailabilityTemporalWrapped=true;
      try{applyImportedPayload=wrapped}catch(_){/* immutable global */}
    }
    try{annotate()}catch(e){console.warn('Initial availability temporal annotation failed',e)}
  }
  window.fmAnnotateAvailabilityTemporalEvidence=annotate;
  install();
})();
