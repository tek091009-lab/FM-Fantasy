const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
function load(path,ctx){vm.runInContext(fs.readFileSync(path,'utf8'),ctx,{filename:path})}
const timers=[];
const window={addEventListener(){},FMCloud:null};window.window=window;
const ctx=vm.createContext({window,globalThis:window,console,structuredClone,JSON,setInterval:(fn)=>{timers.push(fn);return timers.length},clearInterval(){},setTimeout:(fn)=>{fn();return 1}});
window.fmApplyPostPayloadPricingCorrections=(payload)=>payload;
load('disciplineguardv86pre.js',ctx);
assert(window.fmApplyPostPayloadPricingCorrections.__fmV86Pre,'pre wrapper missing');
const base=window.fmApplyPostPayloadPricingCorrections;
const v85=function(payload,...args){const out=base(payload,...args);for(const p of payload.players){for(const k of ['suspended','suspension_status','suspension_remaining','suspension_games_remaining','ban_games_remaining','banned_until','suspension_until','suspension_detail','suspension_evidence','suspension_evidence_structural'])delete p[k];p.suspended=true;p.suspension_status='suspended';p.suspension_remaining=1;p.suspension_evidence_structural={source:'selected_competition_history_v85',competition_scope:'selected_league_only',games_remaining:1,reason:'league yellow-card threshold'}}return out};v85.__fmV85Wrapped=true;window.fmApplyPostPayloadPricingCorrections=v85;
load('disciplineguardv86post.js',ctx);
assert(window.fmApplyPostPayloadPricingCorrections.__fmV86Post,'post wrapper missing');
assert.equal(window.FMDisciplineGuardV86Post.version,'discipline-guard-v87-selected-league-authority');
const direct={pid:1,suspended:true,suspension_status:'Suspended',ban_games_remaining:2,suspension_evidence_structural:{source:'discipline.dat/active-ban-v1',games_remaining:2}};
const derived={pid:2};const payload={players:[direct,derived],meta:{}};
window.fmApplyPostPayloadPricingCorrections(payload);
for(const p of [direct,derived]){
 assert.equal(p.suspended,true);
 assert.equal(p.suspension_evidence_structural.source,'selected_competition_history_v85');
 assert.equal(p.suspension_evidence_structural.competition_scope,'selected_league_only');
 assert.equal(p.suspension_remaining,1);
}
assert.equal(direct.discipline_derived_evidence.raw_current_ban_candidate.ban_games_remaining,2);
assert.equal(direct.discipline_derived_evidence.raw_current_ban_candidate.policy,'diagnostic_only_unscoped_competition_v87');
assert.equal(payload.meta.discipline_v86.selected_league_authoritative,2);
assert.equal(payload.meta.discipline_v86.raw_unscoped_bans_quarantined,0);
assert.equal(payload.meta.discipline_current_state_policy.includes('selected-competition history is authoritative'),true);
console.log('discipline guard v87 selected-league authority OK');
