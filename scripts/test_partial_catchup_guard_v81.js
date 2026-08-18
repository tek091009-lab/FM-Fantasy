const fs=require('fs'),vm=require('vm');
function loadGuard(){
  const window={addEventListener:()=>{}};
  const ctx={window,console,setInterval:()=>0,clearInterval:()=>{},structuredClone:global.structuredClone};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('updateguard.js','utf8'),ctx);
  if(!window.FMWorldUpdateGuard)throw new Error('guard did not expose validator');
  return window.FMWorldUpdateGuard;
}
function buildPayload(){
  const clubs=[{eid:1,name:'Alpha',short_name:'Alpha'},{eid:2,name:'Beta',short_name:'Beta'}];
  const players=[];
  for(const [club,eid,prefix] of [['Alpha',1,'a'],['Beta',2,'b']])for(let i=1;i<=12;i++)players.push({pid:`${prefix}${i}`,id:`${prefix}${i}`,club,club_eid:eid,pos:i===1?'GK':'DEF',available:true});
  const hp=Array.from({length:11},(_,i)=>({player_id:`a${i+1}`,goals:i===0?1:0,own_goals:0}));
  const ap=Array.from({length:11},(_,i)=>({player_id:`b${i+1}`,goals:0,own_goals:0}));
  const proof={shift:132,competition_id:206,team_count:2,safe_squad_clubs:2,mapped_clubs:['Alpha','Beta'],unsafe_squad_names:[],squad_policy:'strict_current_db_membership_only_v68',squad_resolution_policy:'v75-current-db-structural-senior-resolution-no-history',current_squad_size_policy:'strict-current-db-extended-12-60-v79',mapping_proof:'all-fixture-teams-map-to-English-clubs + current-db-roster-proof-v79'};
  return {meta:{competition:'EFL Championship',competition_code:'eng_champ',competition_fixture_id:206,fixture_to_club_shift:132,current_season_candidates:[proof],completed_gameweek:1,current_gameweek:2,next_gameweek:2,latest_gameweek_with_result:1,played_results:2,rich_matches:1,rich_matches_missing:1,history_coverage_status:'partial'},clubs,players,fixtures:[{fixture_id:1,gameweek:1,status:'played',home_score:1,away_score:0},{fixture_id:2,gameweek:1,status:'played',home_score:0,away_score:0}],matches:[{fixture_id:1,home_score:1,away_score:0,home_players:hp,away_players:ap}]};
}
const guard=loadGuard();
if(guard.version!=='world-update-guard-v6-structural-proof')throw new Error(`wrong guard ${guard.version}`);
const first=buildPayload(),catchup=guard.validate(first,null);
if(!catchup.ok)throw new Error(`catch-up partial payload blocked: ${catchup.errors.join(' | ')}`);
if(!catchup.warnings.some(x=>x.includes('catch-up fixtures still lack player-level detail')))throw new Error('catch-up partial warning missing');
const old=JSON.parse(JSON.stringify(first));old.meta.completed_gameweek=1;old.meta.latest_gameweek_with_result=1;old.meta.played_results=1;old.meta.rich_matches=1;old.meta.rich_matches_missing=0;old.meta.history_coverage_status='complete';old.fixtures=[old.fixtures[0]];
const next=buildPayload();next.meta.completed_gameweek=2;next.meta.current_gameweek=3;next.meta.next_gameweek=3;next.meta.latest_gameweek_with_result=2;next.fixtures=[{fixture_id:1,gameweek:1,status:'played',home_score:1,away_score:0},{fixture_id:2,gameweek:2,status:'played',home_score:0,away_score:0}];
const incremental=guard.validate(next,old);
if(incremental.ok)throw new Error('incremental missing-detail regression was not blocked');
if(!incremental.errors.some(x=>x.includes('newly completed fixtures have no validated player-level match detail')))throw new Error('incremental missing-detail error missing');

const runtime={richStatCount:(buf,limit=40)=>Math.min(Number(buf.count||0),Number(limit)||40)};
const cctx={FM_RUNTIME:runtime,window:{},console,setInterval:()=>0,clearInterval:()=>{}};vm.createContext(cctx);vm.runInContext(fs.readFileSync('importcompat.js','utf8'),cctx);
if(!cctx.window.FMImporterCompat?.installed)throw new Error('import compatibility hook did not install');
if(runtime.richStatCount({count:36},40)!==40)throw new Error('36-row retained member is still excluded');
if(runtime.richStatCount({count:35},40)!==35)throw new Error('compatibility hook widened below Python decoder floor');
console.log(JSON.stringify({guard:guard.version,catchup_partial_publishes:catchup.ok,catchup_warnings:catchup.warnings,incremental_missing_detail_blocked:!incremental.ok,compat:cctx.window.FMImporterCompat.version,rows36_included:true}));
