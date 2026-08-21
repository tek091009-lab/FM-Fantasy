const fs=require('fs');
const vm=require('vm');

function must(x,msg){if(!x)throw new Error(msg)}

const code=fs.readFileSync('managerauthoritative.js','utf8');

const locked=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15'];
const draft=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','99'];
const remote={
  squad:[...locked],lockedSquad:[...locked],starters:locked.slice(0,11),bench:locked.slice(11),
  captain:'1',vice:'2',bank:5,lockedBank:5,teamConfirmed:true,currentGameweek:5,completedGameweek:4,
  pointsHistory:[],totalPoints:0,freeTransfers:1,lastTransferRollGW:4,teamName:'TEST',managerName:'Tester',chips:{}
};

const context={
  console,
  setTimeout:(fn)=>{fn();return 1},
  requestAnimationFrame:(fn)=>fn(),
  document:{addEventListener(){},visibilityState:'visible'},
  window:{
    FM_FANTASY_CONFIG:{supabaseUrl:'x',supabaseAnonKey:'y'},
    supabase:{createClient:()=>({auth:{getSession:async()=>({data:{session:{user:{id:'u'}}}})},from:()=>({select:()=>({eq:()=>({eq:()=>({maybeSingle:async()=>({data:{state:remote,updated_at:'2026-08-21T18:00:00Z'},error:null})})})})})})},
    FMCloud:{ready:()=>true,getWorld:()=>({id:'w'}),normaliseManagerState:x=>x,managerState:null},
    addEventListener(){},
  },
  DEFAULT:{squad:[],lockedSquad:[],starters:[],bench:[],bank:100,lockedBank:100,chips:{}},
  state:{...JSON.parse(JSON.stringify(remote)),squad:[...draft],bank:2.5,starters:['1','2','3','4','5','6','7','8','9','10','99'],bench:['12','13','14','15']},
  renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},renderNews(){},renderLeagues(){},
};
context.window.window=context.window;
context.window.state=context.state;
vm.createContext(context);
vm.runInContext(code,context);

(async()=>{
  must(context.window.FMManagerAuthoritative,'manager authority missing');
  must(context.window.FMManagerAuthoritative.hasTransferDraft(context.state),'draft not detected');
  await context.window.fmRestoreManagerFromCloud();
  must(context.state.squad.join('|')===draft.join('|'),'server restore erased pending transfer squad');
  must(Number(context.state.bank)===2.5,'server restore erased pending transfer bank');
  must(context.state.starters.includes('99'),'server restore erased pending transfer XI');
  must(context.state.lockedSquad.join('|')===locked.join('|'),'locked transfer baseline was mutated');
  must(Number(context.state.freeTransfers)===1,'server-authoritative FT balance not retained');
  console.log('PASS transfer draft survives authoritative manager restore');
})();
