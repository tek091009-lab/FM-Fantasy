const fs=require('fs');
const vm=require('vm');

function must(x,msg){if(!x)throw new Error(msg)}
const code=fs.readFileSync('managerauthoritative.js','utf8');
const locked=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15'];

function makeRemote(){return {
  squad:[...locked],lockedSquad:[...locked],starters:locked.slice(0,11),bench:locked.slice(11),
  captain:'1',vice:'2',bank:5,lockedBank:5,teamConfirmed:true,currentGameweek:5,completedGameweek:4,
  pointsHistory:[],totalPoints:0,freeTransfers:1,lastTransferRollGW:4,teamName:'TEST',managerName:'Tester',chips:{}
}}
function makeContext(localState,remote){
  const supabase={createClient:()=>({
    auth:{getSession:async()=>({data:{session:{user:{id:'u'}}}})},
    from:()=>({select:()=>({eq:()=>({eq:()=>({maybeSingle:async()=>({data:{state:remote,updated_at:String(remote.__stamp||'a')},error:null})})})})})
  })};
  const context={
    console,
    setTimeout:(fn)=>{fn();return 1},
    requestAnimationFrame:(fn)=>fn(),
    document:{addEventListener(){},visibilityState:'visible'},
    supabase,
    window:{
      FM_FANTASY_CONFIG:{supabaseUrl:'x',supabaseAnonKey:'y'},supabase,
      FMCloud:{ready:()=>true,getWorld:()=>({id:'w'}),normaliseManagerState:x=>x,managerState:null},
      addEventListener(){},
    },
    DEFAULT:{squad:[],lockedSquad:[],starters:[],bench:[],bank:100,lockedBank:100,chips:{}},
    state:localState,
    renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},renderNews(){},renderLeagues(){},
  };
  context.window.window=context.window;context.window.state=context.state;
  vm.createContext(context);vm.runInContext(code,context);return context;
}

async function replacementDraftSurvives(){
  const remote=makeRemote();
  const draft=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','99'];
  const local={...JSON.parse(JSON.stringify(remote)),squad:[...draft],bank:2.5,starters:['1','2','3','4','5','6','7','8','9','10','99'],bench:['12','13','14','15']};
  const c=makeContext(local,remote),a=c.window.FMManagerAuthoritative;
  must(a.hasTransferDraft(c.state),'replacement draft not detected');
  // Simulate the repeated startup/server restores that were wiping the first clicks.
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.join('|')===draft.join('|'),'repeated restore erased pending replacement');
  must(Number(c.state.bank)===2.5,'repeated restore erased draft bank');
  must(c.state.starters.includes('99'),'repeated restore erased draft XI');
  must(c.state.lockedSquad.join('|')===locked.join('|'),'locked baseline mutated by draft preservation');
}

async function removalDraftSurvivesAndProgressStillUpdates(){
  const remote=makeRemote();
  const partial=locked.slice(0,14);
  const local={...JSON.parse(JSON.stringify(remote)),squad:[...partial],bank:9.5,starters:locked.slice(0,10),bench:locked.slice(10,14)};
  const c=makeContext(local,remote),a=c.window.FMManagerAuthoritative;
  must(a.hasTransferDraft(c.state),'14-player transfer-out draft not detected');
  // Force an authoritative change while the user is mid-transfer.
  remote.totalPoints=42;remote.pointsHistory=[{gw:4,gross:42,net:42}];remote.completedGameweek=4;remote.currentGameweek=5;remote.__stamp='b';
  await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.join('|')===partial.join('|'),'server progress refresh re-added transferred-out player');
  must(Number(c.state.bank)===9.5,'server progress refresh erased pending-sale bank');
  must(Number(c.state.totalPoints)===42,'server-authoritative progress stopped updating during draft');
  must(c.state.pointsHistory.length===1,'server points history stopped updating during draft');
  must(c.state.lockedSquad.join('|')===locked.join('|'),'confirmed locked squad changed before transfer confirmation');
}

(async()=>{
  await replacementDraftSurvives();
  await removalDraftSurvivesAndProgressStillUpdates();
  console.log('PASS transfer drafts survive repeated authoritative restores while server progress still updates');
})().catch(e=>{console.error(e);process.exit(1)});
