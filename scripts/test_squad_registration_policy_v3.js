const fs=require('fs'),vm=require('vm'),assert=require('assert');
function context(extra={}){const c={console,Date,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{},requestAnimationFrame:fn=>fn(),MutationObserver:function(){this.observe=()=>{}},...extra};c.window=c.window||{addEventListener:()=>{}};c.globalThis=c;return vm.createContext(c)}
{
 const c=context({fmApplyPostPayloadPricingCorrections:p=>p});
 vm.runInContext(fs.readFileSync('squadeligibilityfix.js','utf8'),c);
 const payload={meta:{unresolved_squad_eids:[],ambiguous_memberships:[{player_eid:9}]},fixtures:[{home:'A',away:'B'},{home:'C',away:'D'}],players:[
  {id:1,name:'Registered',club:'A',competition_eligible:true,registration_status:'competition_eligible',registration_evidence:{eligible:true},history:[],visible:true,available:true},
  {id:2,name:'Senior evidence',club:'A',competition_eligible:false,registration_status:'not_in_current_competition_cohort',registration_evidence:{eligible:false},history:[{date:'2025-08-30',gameweek:4,home:'A',away:'B',minutes:0}],visible:false,available:false},
  {id:3,name:'Reserve only',club:'A',competition_eligible:false,registration_status:'not_in_current_competition_cohort',registration_evidence:{eligible:false},history:[],visible:false,available:false},
  {id:4,name:'Casey shape',club:'A',competition_eligible:false,registration_status:'not_in_current_competition_cohort',registration_evidence:{eligible:false},history:[{date:'2025-08-16',gameweek:2,home:'C',away:'D',minutes:90,fpl_points:1}],visible:false,available:false},
  {id:9,name:'Ambiguous',club:'A',competition_eligible:true,registration_status:'competition_eligible',registration_evidence:{eligible:true},history:[{date:'2025-08-30',gameweek:4,home:'A',away:'B'}],visible:true,available:true}
 ]};
 c.window.FMSquadEligibilityFix.fix(payload);
 assert.equal(payload.players[0].visible,true);
 assert.equal(payload.players[0].available,true);
 assert.equal(payload.players[0].registration_evidence.cohort_eligible,true);
 assert.equal(payload.players[1].visible,true);
 assert.equal(payload.players[1].available,true);
 assert.equal(payload.players[1].registration_status,'senior_matchday_exception');
 assert.equal(payload.players[1].registration_evidence.cohort_eligible,false);
 assert.equal(payload.players[1].registration_evidence.senior_evidence_matching_rows,1);
 assert.equal(payload.players[2].visible,false);
 assert.equal(payload.players[2].available,false);
 assert.equal(payload.players[2].registration_status,'reserve_or_u21_no_senior_evidence');
 assert.equal(payload.players[3].visible,false);
 assert.equal(payload.players[3].available,false);
 assert.equal(payload.players[3].registration_status,'history_club_mismatch_no_valid_senior_evidence');
 assert.equal(payload.players[3].registration_evidence.senior_evidence_matching_rows,0);
 assert.equal(payload.players[3].registration_evidence.senior_evidence_mismatched_rows,1);
 assert.equal(payload.players[4].visible,false);
 assert.equal(payload.players[4].available,false);
 assert.equal(payload.players[4].registration_status,'quarantined_current_squad_identity');
 assert.equal(payload.meta.squad_eligibility_v5.history_club_mismatch_hidden,1);
 assert.equal(payload.meta.fantasy_player_pool_policy.includes('history from another club cannot promote a player'),true);
}
{
 const document={documentElement:{},addEventListener:()=>{},querySelector:()=>null,getElementById:()=>null,head:{appendChild:()=>{}},createElement:()=>({style:{},dataset:{},appendChild:()=>{},querySelector:()=>null,querySelectorAll:()=>[],insertAdjacentElement:()=>{}})};
 const c=context({document});c.window.FMCloud=null;c.window.__FM_IMPORT_MODE_ACTIVE='update';
 vm.runInContext(fs.readFileSync('registrationnewsguard.js','utf8'),c);
 const old={meta:{snapshot_date:'2025-08-30'},players:[
  {id:1,name:'Daniel Peretz',club:'Southampton',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:true},history:[{date:'2025-08-30',gameweek:4,match_id:1}]},
  {id:2,name:'Real Transfer',club:'A',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:true},history:[]},
  {id:3,name:'Hidden Player',club:'B',visible:false,competition_eligible:false,registration_evidence:{cohort_eligible:false},history:[]},
  {id:4,name:'U21 Player',club:'B',visible:false,competition_eligible:false,registration_evidence:{cohort_eligible:false},history:[]}
 ]};
 const next={meta:{snapshot_date:'2025-09-06',import_mode:'update'},players:[
  {id:1,name:'Daniel Peretz',club:'Southampton',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:true},history:[{date:'2025-08-30',gameweek:4,match_id:1},{date:'2025-09-06',gameweek:5,match_id:2}]},
  {id:2,name:'Real Transfer',club:'C',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:true},history:[{date:'2025-09-06',gameweek:5,match_id:3}]},
  {id:3,name:'Hidden Player',club:'B',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:true},history:[]},
  {id:4,name:'U21 Player',club:'B',visible:true,competition_eligible:true,registration_evidence:{cohort_eligible:false},history:[{date:'2025-09-06',gameweek:5,match_id:4}]}
 ]};
 const out=c.window.FMRegistrationNewsGuard.buildEvidence(next,old);
 assert.equal(out.transfers.some(x=>x.name==='Daniel Peretz'),false);
 assert.equal(out.transfers.length,1);
 assert.equal(out.transfers[0].name,'Real Transfer');
 assert.equal(out.registrationEvents.some(x=>x.name==='Hidden Player'&&x.kind==='registration'),true);
 assert.equal(out.registrationEvents.some(x=>x.name==='U21 Player'&&x.kind==='senior_matchday'),true);
 const season={meta:{snapshot_date:'2025-08-30',import_mode:'season'},players:next.players};
 const seasonOut=c.window.FMRegistrationNewsGuard.buildEvidence(season,null);
 assert.equal(seasonOut.transfers.length,0);assert.equal(seasonOut.registrationEvents.length,0);
}
console.log('squad/registration policy v5 regression tests passed');