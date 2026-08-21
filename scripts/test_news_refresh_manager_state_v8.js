'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const source=fs.readFileSync('managerauthoritative.js','utf8');
assert(source.includes('manager-authoritative-v3-critical-state-integrity'));
assert(source.includes("out.news=clone(state.news)"));
assert(source.includes("out.activeStatuses=clone(state.activeStatuses)"));
assert(source.includes('restoreWorldDerivedState(worldDerived)'));
assert(source.includes("FMNewsPersistence?.restore?.('manager authoritative restore')"));

(async()=>{
  const locked=Array.from({length:15},(_,i)=>`p${i+1}`);
  const remoteManager={
    squad:[...locked],lockedSquad:[...locked],lockedBank:0,
    starters:Array.from({length:11},(_,i)=>`p${i+1}`),
    bench:Array.from({length:4},(_,i)=>`p${i+12}`),
    currentGameweek:6,completedGameweek:5,pointsHistory:[{gw:5,net:30}],totalPoints:30,
    freeTransfers:1,lastTransferRollGW:5,teamConfirmed:true,teamName:'HMS PISS THE LEAGUE',managerName:'Thomas Kelleher',
    chips:{first:{},second:{}}
  };
  const importedNews={initial:true,gameweek:6,injuries:[{pid:'inj1',name:'Injured Player'}],suspensions:[{pid:'sus1',name:'Suspended Player'}]};
  const importedStatuses={injuries:[{pid:'inj1',name:'Injured Player'}],suspensions:[{pid:'sus1',name:'Suspended Player'}]};
  const DEFAULT={squad:[],lockedSquad:[],starters:[],bench:[],news:[],activeStatuses:{},chips:{first:{},second:{}}};
  let renderNewsCalls=0,renderLeagueCalls=0;
  const chain={
    select(){return this},eq(){return this},
    async maybeSingle(){return {data:{state:remoteManager,updated_at:'2026-08-21T17:00:00Z'},error:null}}
  };
  const client={auth:{async getSession(){return {data:{session:{user:{id:'u1'}}}}}},from(){return chain}};
  const ctx={
    console,JSON,Object,Array,Promise,setTimeout,clearTimeout,
    requestAnimationFrame:fn=>fn(),
    document:{addEventListener(){},visibilityState:'visible'},
    FM_FANTASY_CONFIG:{supabaseUrl:'https://example.invalid',supabaseAnonKey:'anon'},
    supabase:{createClient(){return client}},
    DEFAULT,
    state:{...DEFAULT,lockedSquad:[],lockedBank:100,news:JSON.parse(JSON.stringify(importedNews)),activeStatuses:JSON.parse(JSON.stringify(importedStatuses))},
    renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},
    renderNews(){renderNewsCalls++},renderLeagues(){renderLeagueCalls++},
    FMCloud:{ready:()=>true,getWorld:()=>({id:'world1'}),normaliseManagerState:x=>x,managerState:null},
    FMNewsPersistence:{restore(){return true}},
    addEventListener(){}
  };
  ctx.window=ctx;
  vm.createContext(ctx);
  vm.runInContext(source,ctx,{filename:'managerauthoritative.js'});
  const ok=await ctx.FMManagerAuthoritative.restore();
  assert.strictEqual(ok,true);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.state.news)),importedNews,'manager refresh must preserve imported state.news');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.state.activeStatuses)),importedStatuses,'manager refresh must preserve imported activeStatuses');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.state.lockedSquad)),locked,'manager refresh must restore authoritative transfer baseline');
  assert.strictEqual(ctx.state.lockedBank,0,'authoritative locked bank must restore');
  assert.strictEqual(ctx.state.currentGameweek,6);
  assert.strictEqual(ctx.state.completedGameweek,5);
  assert.strictEqual(ctx.state.totalPoints,30);
  assert.strictEqual(ctx.state.freeTransfers,1);
  assert.strictEqual(ctx.state.lastTransferRollGW,5);
  assert.strictEqual(ctx.state.squad.length,15,'manager fields still hydrate from remote state');
  assert(renderNewsCalls>=1,'News is rerendered after manager hydrate');
  assert(renderLeagueCalls>=1,'Leagues are rerendered after manager hydrate');
  const renderedCount=(ctx.state.news.injuries||[]).length+(ctx.state.news.suspensions||[]).length+(ctx.state.activeStatuses.injuries||[]).length+(ctx.state.activeStatuses.suspensions||[]).length;
  assert(renderedCount>=4,'later renderAll would still have News/status data');
  assert.strictEqual(ctx.FMManagerAuthoritative.criticalHealthy(remoteManager),true,'rehydrated state must satisfy critical integrity check');
  console.log('news + manager critical-state regression passed');
})().catch(err=>{console.error(err);process.exit(1)});
