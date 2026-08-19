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
    for(let i=1;i<=12;i++)players.push({pid:`${c}-${i}`,id:`${c}-${i}`,club:name,club_eid:c,pos:i===1?'GK':'DEF',available:true});
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
const guard=loadGuard();
if(guard.version!=='world-update-guard-v9-history-aware-season-catchup')throw new Error(`wrong guard ${guard.version}`);

// A clean season/database import may publish recovered partial historical detail.
const season=buildPayload('season');
const seasonResult=guard.validate(season,null);
if(!seasonResult.ok)throw new Error(`clean season partial import blocked: ${seasonResult.errors.join(' | ')}`);
if(!seasonResult.warnings.some(x=>x.includes('clean season import may publish partial history')))throw new Error('clean season partial warning missing');

// A weekly update must still contain player detail for newly completed fixtures.
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

console.log(JSON.stringify({guard:guard.version,clean_season_partial_publishes:seasonResult.ok,season_warnings:seasonResult.warnings.length,gameweek_missing_detail_blocked:!updateResult.ok,trusted_history:updateResult.summary.trusted_historical_matches}));
