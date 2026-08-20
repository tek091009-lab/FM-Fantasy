const fs=require('fs'),vm=require('vm');
function loadGuard(){
  const window={addEventListener:()=>{}};
  const ctx={window,console,setInterval:()=>0,clearInterval:()=>{},structuredClone:global.structuredClone};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('updateguard.js','utf8'),ctx);
  if(!window.FMWorldUpdateGuard)throw new Error('guard did not expose validator');
  return window.FMWorldUpdateGuard;
}
function buildPayload(mode='season'){
  const clubs=[];const players=[];
  for(let c=1;c<=24;c++){
    const name=`Club ${c}`;clubs.push({eid:c,name,short_name:name});
    for(let i=1;i<=12;i++)players.push({pid:`${c}-${i}`,id:`${c}-${i}`,club:name,club_eid:c,pos:i===1?'GK':'DEF',available:true,history:[]});
  }
  const fixtures=[];const matches=[];
  for(let i=1;i<=50;i++){
    const gw=1+Math.floor((i-1)/13),home=((i-1)%24)+1,away=(i%24)+1;
    fixtures.push({fixture_id:i,gameweek:gw,status:'played',home_score:i<=33?1:0,away_score:0});
    if(i<=33){
      const hp=Array.from({length:11},(_,j)=>({player_id:`${home}-${j+1}`,goals:j===0?1:0,own_goals:0}));
      const ap=Array.from({length:11},(_,j)=>({player_id:`${away}-${j+1}`,goals:0,own_goals:0}));
      matches.push({fixture_id:i,home_score:1,away_score:0,home_players:hp,away_players:ap});
    }
  }
  return {meta:{import_mode:mode,competition:'EFL Championship',competition_code:'eng_champ',completed_gameweek:4,current_gameweek:5,next_gameweek:5,latest_gameweek_with_result:4,played_results:50,rich_matches:33,rich_matches_missing:17,history_coverage_status:'partial'},clubs,players,fixtures,matches};
}
function validRows(club,scoreHome,scoreAway,venue,home,away,date,gw){
  return Array.from({length:12},(_,j)=>({player_id:`${club}-${j+1}`,club:`Club ${club}`,home,away,date,gameweek:gw,venue,minutes:j<11?90:0,goals:venue==='H'?(j<scoreHome?1:0):(j<scoreAway?1:0),own_goals:0,assists:0,fpl_points:j<11?2:0}));
}
function firstWeekPayload(includeUnrecoverable=false){
  const clubs=[];const players=[];
  for(let c=1;c<=8;c++){
    const name=`Club ${c}`;clubs.push({eid:c,name,short_name:name});
    for(let i=1;i<=12;i++)players.push({pid:`${c}-${i}`,id:`${c}-${i}`,club:name,club_eid:c,pos:i===1?'GK':'DEF',available:true,history:[]});
  }
  const oldFixture={fixture_id:1,gameweek:4,status:'played',home:'Club 1',away:'Club 2',date:'2025-08-30',home_score:1,away_score:0};
  const oldMatch={...oldFixture,home_players:validRows(1,1,0,'H','Club 1','Club 2','2025-08-30',4),away_players:validRows(2,1,0,'A','Club 1','Club 2','2025-08-30',4)};
  const old={meta:{import_mode:'update',competition:'EFL Championship',competition_code:'eng_champ',completed_gameweek:4,current_gameweek:5,next_gameweek:5,latest_gameweek_with_result:4,played_results:1,rich_matches:1,rich_matches_missing:0,history_coverage_status:'complete'},clubs,players:JSON.parse(JSON.stringify(players)),fixtures:[oldFixture],matches:[oldMatch]};
  const f2={fixture_id:2,gameweek:5,status:'played',home:'Club 3',away:'Club 4',date:'2025-09-06',home_score:2,away_score:1};
  const f3={fixture_id:3,gameweek:5,status:'played',home:'Club 5',away:'Club 6',date:'2025-09-06',home_score:1,away_score:0};
  const fixtures=[oldFixture,f2,f3];if(includeUnrecoverable)fixtures.push({fixture_id:4,gameweek:5,status:'played',home:'Club 7',away:'Club 8',date:'2025-09-06',home_score:1,away_score:1});
  const nextPlayers=JSON.parse(JSON.stringify(players));
  const addHist=rows=>{for(const r of rows){const p=nextPlayers.find(x=>x.pid===r.player_id);p.history.push({...r});delete p.history[p.history.length-1].player_id}}
  addHist(validRows(3,2,1,'H','Club 3','Club 4','2025-09-06',5));addHist(validRows(4,2,1,'A','Club 3','Club 4','2025-09-06',5));
  addHist(validRows(5,1,0,'H','Club 5','Club 6','2025-09-06',5));addHist(validRows(6,1,0,'A','Club 5','Club 6','2025-09-06',5));
  const broken={...f2,home_players:[...validRows(3,2,1,'H','Club 3','Club 4','2025-09-06',5).slice(0,10),{...validRows(4,2,1,'A','Club 3','Club 4','2025-09-06',5)[0]}],away_players:validRows(4,2,1,'A','Club 3','Club 4','2025-09-06',5)};
  const next={meta:{import_mode:'update',competition:'EFL Championship',competition_code:'eng_champ',completed_gameweek:5,current_gameweek:6,next_gameweek:6,latest_gameweek_with_result:5,played_results:fixtures.length,rich_matches:2,rich_matches_missing:fixtures.length-2,history_coverage_status:'partial'},clubs,players:nextPlayers,fixtures,matches:[oldMatch,broken]};
  return {old,next};
}
function addCaseyStyleCollision(next){
 const fakeHome=validRows(7,1,1,'H','Club 7','Club 8','2025-09-06',5);
 const fakeAway=validRows(8,1,1,'A','Club 7','Club 8','2025-09-06',5);
 for(let j=0;j<12;j++){
   const hp=next.players.find(p=>p.pid===`1-${j+1}`),ap=next.players.find(p=>p.pid===`2-${j+1}`);
   const hr={...fakeHome[j]};delete hr.player_id;hp.history.push(hr);
   const ar={...fakeAway[j]};delete ar.player_id;ap.history.push(ar);
 }
}
const guard=loadGuard();
if(guard.version!=='world-update-guard-v11-club-matched-history-repair')throw new Error(`wrong guard ${guard.version}`);

// A clean season/database import may publish recovered partial historical detail.
const season=buildPayload('season');
const seasonResult=guard.validate(season,null);
if(!seasonResult.ok)throw new Error(`clean season partial import blocked: ${seasonResult.errors.join(' | ')}`);
if(!seasonResult.warnings.some(x=>x.includes('clean season import may publish partial history')))throw new Error('clean season partial warning missing');

// A weekly update must still contain player detail for genuinely unrecoverable newly completed fixtures.
const old=buildPayload('update');
old.meta.completed_gameweek=3;old.meta.current_gameweek=4;old.meta.latest_gameweek_with_result=3;
old.fixtures=old.fixtures.filter(f=>f.gameweek<=3);
old.matches=old.matches.filter(m=>m.fixture_id<=33);
old.meta.played_results=39;old.meta.rich_matches=33;old.meta.rich_matches_missing=0;old.meta.history_coverage_status='complete';
const update=buildPayload('update');
const updateResult=guard.validate(update,old);
if(updateResult.ok)throw new Error('gameweek update with missing newly-completed detail was not blocked');
if(!updateResult.errors.some(x=>x.includes('newly completed fixtures have no validated player-level match detail')))throw new Error('incremental protection error missing');
if(updateResult.summary.trusted_historical_matches<33)throw new Error(`historical match trust regression: ${updateResult.summary.trusted_historical_matches}`);

// First weekly import: a malformed rich row and a missing rich row are rebuilt from club-matched decoded player histories.
const repairCase=firstWeekPayload(false);
const repairMeta=guard.repairWeeklyMatchDetail(repairCase.next,repairCase.old);
if(repairMeta.repaired_invalid!==1)throw new Error(`expected one invalid match repair, got ${repairMeta.repaired_invalid}`);
if(repairMeta.added_missing!==1)throw new Error(`expected one missing match recovery, got ${repairMeta.added_missing}`);
const repairedResult=guard.validate(repairCase.next,repairCase.old);
if(!repairedResult.ok)throw new Error(`recoverable first weekly import still blocked: ${repairedResult.errors.join(' | ')}`);

// No guessing: if neither rich detail nor trustworthy player-history detail exists, the update must remain blocked.
const hardCase=firstWeekPayload(true);
const hardMeta=guard.repairWeeklyMatchDetail(hardCase.next,hardCase.old);
if(hardMeta.unrepaired_missing!==1)throw new Error(`expected one genuinely unrecoverable fixture, got ${hardMeta.unrepaired_missing}`);
const hardResult=guard.validate(hardCase.next,hardCase.old);
if(hardResult.ok)throw new Error('unrecoverable first-week fixture incorrectly passed');

// Casey regression: wrong-club history must not repair a fixture even when it provides 24 unique players and the exact official score.
const collisionCase=firstWeekPayload(true);addCaseyStyleCollision(collisionCase.next);
const collisionMeta=guard.repairWeeklyMatchDetail(collisionCase.next,collisionCase.old);
if(collisionMeta.added_missing!==1)throw new Error(`wrong-club history repaired an extra fixture: ${collisionMeta.added_missing}`);
if(collisionMeta.unrepaired_missing!==1)throw new Error('Casey-style wrong-club fixture did not remain unrecoverable');
if((collisionMeta.history_identity?.skipped_club_mismatch||0)<24)throw new Error(`expected >=24 wrong-club history rows to be rejected, got ${collisionMeta.history_identity?.skipped_club_mismatch||0}`);
const collisionResult=guard.validate(collisionCase.next,collisionCase.old);
if(collisionResult.ok)throw new Error('Casey-style wrong-club history incorrectly passed weekly validation');

console.log(JSON.stringify({guard:guard.version,clean_season_partial_publishes:seasonResult.ok,gameweek_missing_detail_blocked:!updateResult.ok,trusted_history:updateResult.summary.trusted_historical_matches,first_week_repaired_invalid:repairMeta.repaired_invalid,first_week_added_missing:repairMeta.added_missing,first_week_recoverable_passes:repairedResult.ok,unrecoverable_still_blocked:!hardResult.ok,wrong_club_rows_rejected:collisionMeta.history_identity.skipped_club_mismatch,casey_style_collision_blocked:!collisionResult.ok}));