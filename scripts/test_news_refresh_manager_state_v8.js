'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const source=fs.readFileSync('managerauthoritative.js','utf8');
assert(source.includes('manager-authoritative-v2-preserve-world-derived-news'));
assert(source.includes("out.news=JSON.parse(JSON.stringify(state.news))"));
assert(source.includes("out.activeStatuses=JSON.parse(JSON.stringify(state.activeStatuses))"));
assert(source.includes('restoreWorldDerivedState(worldDerived)'));
assert(source.includes("FMNewsPersistence?.restore?.('manager authoritative restore')"));

(async()=>{
  const remoteManager={
    squad:Array.from({length:15},(_,i)=>`p${i+1}`),
    starters:Array.from({length:11},(_,i)=>`p${i+1}`),
    bench:Array.from({length:4},(_,i)=>`p${i+12}`),
    currentGameweek:5,
    chips:{first:{},second:{}}
  };
  const importedNews={initial:true,gameweek:5,injuries:[{pid:'inj1',name:'Injured Player'}],suspensions:[{pid:'sus1',name:'Suspended Player'}]};
  const importedStatuses={injuries:[{pid:'inj1',name:'Injured Player'}],suspensions:[{pid:'sus1',name:'Suspended Player'}]};
  const DEFAULT={squad:[],starters:[],bench:[],news:[],activeStatuses:{},chips:{first:{},second:{}}};
  let renderNewsCalls=0;
  const chain={
    select(){return this},eq(){return this},
    async maybeSingle(){return {data:{state:remoteManager,updated_at:'2026-08-21T15:00:00Z'},error:null}}
  };
  const client={auth:{async getSession(){return {data:{session:{user:{id:'u1'}}}}}},from(){return chain}};
  const ctx={
    console,JSON,Object,Array,Promise,setTimeout,clearTimeout,
    requestAnimationFrame:fn=>fn(),
    document:{addEventListener(){},visibilityState:'visible'},
    FM_FANTASY_CONFIG:{supabaseUrl:'https://example.invalid',supabaseAnonKey:'anon'},
    supabase:{createClient(){return client}},
    DEFAULT,
    state:{...DEFAULT,news:JSON.parse(JSON.stringify(importedNews)),activeStatuses:JSON.parse(JSON.stringify(importedStatuses))},
    renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},
    renderNews(){renderNewsCalls++},
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
  assert.strictEqual(ctx.state.squad.length,15,'manager fields still hydrate from remote state');
  assert(renderNewsCalls>=1,'News is rerendered after manager hydrate');
  // Simulate the server scorer calling renderAll after the manager refresh. The world-derived News must still exist.
  const renderedCount=(ctx.state.news.injuries||[]).length+(ctx.state.news.suspensions||[]).length+(ctx.state.activeStatuses.injuries||[]).length+(ctx.state.activeStatuses.suspensions||[]).length;
  assert(renderedCount>=4,'later renderAll would still have News/status data');
  console.log('news manager-refresh v8 regression passed');
})().catch(err=>{console.error(err);process.exit(1)});
