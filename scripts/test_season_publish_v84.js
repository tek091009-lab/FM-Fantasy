const fs=require('fs'),vm=require('vm');
function loadGuard(){
  const window={addEventListener:()=>{}};
  const ctx={window,console,setInterval:()=>0,clearInterval:()=>{},structuredClone:global.structuredClone};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('updateguard.js','utf8'),ctx);
  if(!window.FMWorldUpdateGuard)throw new Error('guard did not expose validator');
  return window.FMWorldUpdateGuard;
}
function buildPayload(mode='season'){
  const clubs=[];const players=[];const mapped=[];
  for(let c=1;c<=24;c++){
    const name=`Club ${c}`;mapped.push(name);clubs.push({eid:c,name,short_name:name});
    for(let i=1;i<=12;i++)players.push({pid:`${c}-${i}`,id:`${c}-${i}`,club:name,club_eid:c,pos:i===1?'GK':'DEF',available:true});
  }
  const fixtures=[];const matches=[];
  for(let i=1;i<=50;i++){
    const gw=1+Math.floor((i-1)/13);const home=((i-1)%24)+1,away=(i%24)+1;
    fixtures.push({fixture_id:i,gameweek:gw,status:'played',home_score:i<=33?1:0,away_score:0});
    if(i<=33){
      const hp=Array.from({length:11},(_,j)=>({player_id:`${home}-${j+1}`,goals:j===0?1:0,own_goals:0}));
      const ap=Array.from({length:11},(_,j)=>({player_id:`${away}-${j+1}`,goals:0,own_goals:0}));
      matches.push({fixture_id:i,home_score:1,away_score:0,home_players:hp,away_players:ap});
    }
  }
  const proof={shift:132,competition_id:206,team_count:24,safe_squad_clubs:24,mapped_clubs:mapped,unsafe_squad_names:[],squad_policy:'strict_current_db_membership_only_v68',squad_resolution_policy:'v75-current-db-structural-senior-resolution-no-history',current_squad_size_policy:'strict-current-db-extended-12-60-v79',mapping_proof:'all-fixture-teams-map-to-English-clubs + current-db-roster-proof-v79'};
  return {meta:{import_mode:mode,competition:'EFL Championship',competition_code:'eng_champ',competition_fixture_id:206,fixture_to_club_shift:132,current_season_candidates:[proof],completed_gameweek:4,current_gameweek:5,next_gameweek:5,latest_gameweek_with_result:4,played_results:50,rich_matches:33,rich_matches_missing:17,history_coverage_status:'partial'},clubs,players,fixtures,matches};
}
const guard=loadGuard();
if(guard.version!=='world-update-guard-v7-explicit-season-partial')throw new Error(`wrong guard ${guard.version}`);
const old=buildPayload('update');old.meta.completed_gameweek=3;old.meta.latest_gameweek_with_result=3;old.fixtures=old.fixtures.filter(f=>f.gameweek<=3);old.matches=old.matches.filter(m=>m.fixture_id<=33);old.meta.rich_matches_missing=0;old.meta.history_coverage_status='complete';
const season=buildPayload('season');const seasonResult=guard.validate(season,old);
if(!seasonResult.ok)throw new Error(`season partial import blocked: ${seasonResult.errors.join(' | ')}`);
if(!seasonResult.warnings.some(x=>x.includes('season import may publish partial history')))throw new Error('season partial warning missing');
const update=buildPayload('update');const updateResult=guard.validate(update,old);
if(updateResult.ok)throw new Error('gameweek update with missing newly-completed detail was not blocked');
if(!updateResult.errors.some(x=>x.includes('newly completed fixtures have no validated player-level match detail')))throw new Error('incremental protection error missing');
console.log(JSON.stringify({guard:guard.version,season_partial_publishes:seasonResult.ok,season_warnings:seasonResult.warnings.length,gameweek_missing_detail_blocked:!updateResult.ok}));
