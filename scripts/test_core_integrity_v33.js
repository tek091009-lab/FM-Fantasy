'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');

function basicCtx(){
  const listeners={};
  const ctx={
    console,JSON,Object,Array,Promise,Number,String,Math,Date,
    setTimeout:(fn)=>{fn();return 1},clearTimeout(){},setInterval:()=>1,clearInterval(){},
    requestAnimationFrame:fn=>fn(),
    CustomEvent:function(type,init){this.type=type;this.detail=init?.detail},
    MutationObserver:function(){this.observe=()=>{}},
    document:{readyState:'complete',documentElement:{},addEventListener(){},querySelectorAll(){return[]}},
    addEventListener(type,fn){(listeners[type]||(listeners[type]=[])).push(fn)},
    dispatchEvent(ev){for(const fn of listeners[ev.type]||[])fn(ev);return true}
  };
  ctx.window=ctx;
  return ctx;
}

function run(file,ctx){vm.createContext(ctx);vm.runInContext(fs.readFileSync(file,'utf8'),ctx,{filename:file});return ctx}

function transferBaselineRegression(){
  const original=Array.from({length:15},(_,i)=>`p${i+1}`),starters=original.slice(0,11),bench=original.slice(11);
  const ctx=basicCtx();
  ctx.state={teamConfirmed:true,squad:[...original],lockedSquad:[],bank:0,lockedBank:100,starters:[...starters],bench:[...bench],captain:'p1',vice:'p2'};
  ctx.FMCloud={managerState:null};
  ctx.transferSessionBase=()=>({squad:[],bank:100,starters:[],bench:[],captain:null,vice:null});
  ctx.renderTransferSummary=()=>{};ctx.renderTransferPitch=()=>{};
  run('transferintegrityguard.js',ctx);
  const base=ctx.transferSessionBase();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(ctx.state.lockedSquad)),original,'confirmed team must seed missing locked squad');
  assert.strictEqual(ctx.state.lockedBank,0,'confirmed team must seed locked bank from real bank, not stale £100');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(base.squad)),original,'opening Transfers must start from confirmed 15-player squad');
  assert.strictEqual(base.bank,0,'opening Transfers must start from confirmed bank');
  assert.strictEqual(base.starters.length,11,'reset baseline must retain valid XI');
  assert.strictEqual(base.bench.length,4,'reset baseline must retain valid bench');
  ctx.state.squad=[...original.slice(0,14),'new-player'];
  const pendingBase=ctx.transferSessionBase();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(pendingBase.squad)),original,'pending transfer must compare against locked pre-transfer squad');
  assert.strictEqual(pendingBase.bank,0);
  assert.strictEqual(ctx.FMTransferIntegrityGuard.status().locked,15);
}

function transferRolloverRegression(){
  const ctx=basicCtx();
  ctx.state={currentGameweek:6,lastTransferRollGW:5,freeTransfers:1};
  ctx.save=()=>{};
  ctx.confirmTransfers=function(){
    const gw=ctx.state.currentGameweek;
    if(Number(ctx.state.lastTransferRollGW||0)<gw){ctx.state.freeTransfers=Math.min(5,Number(ctx.state.freeTransfers||0)+1);ctx.state.lastTransferRollGW=gw}
    const changes=1;ctx.state.freeTransfers=Math.max(0,Number(ctx.state.freeTransfers||0)-changes);return true;
  };
  run('transferrolloverguard.js',ctx);
  assert(ctx.confirmTransfers.__fmTransferRolloverGuard,'legacy confirmTransfers must be guarded');
  ctx.confirmTransfers();
  assert.strictEqual(ctx.state.freeTransfers,0,'using the only GW6 FT must leave 0, not mint another FT');
  assert.strictEqual(ctx.state.lastTransferRollGW,5,'transfer confirmation must not advance rollover marker');
}

async function publishBarrierSuccessRegression(){
  const ctx=basicCtx(),calls=[];
  const world={id:'w1',payload:{meta:{completed_gameweek:4}}};
  ctx.FMCloud={
    async publishWorld(payload){calls.push('publish');world.payload=payload;return payload},
    isCreator:()=>true,getWorld:()=>world,async loadWorld(){calls.push('reload');return world.payload}
  };
  ctx.FMSessionRPC={async call(fn){calls.push(fn);if(fn==='fmfantasy_creator_score_world_managers')return {ok:true,target:5,managers:[{username:'A'}]};throw new Error('unexpected')}};
  ctx.FMManagerStateAuthority={async refreshOwnFromServer(){calls.push('refresh')}};
  run('publishscorebarrier.js',ctx);ctx.FMPublishScoreBarrier.install();
  const payload={meta:{completed_gameweek:5}};
  const out=await ctx.FMCloud.publishWorld(payload);
  assert.strictEqual(out,payload);
  assert.deepStrictEqual(calls.slice(0,3),['publish','fmfantasy_creator_score_world_managers','refresh'],'weekly publish must score managers before resolving');
  assert(!calls.includes('fmfantasy_undo_last_import'),'successful scoring must not rollback');
}

async function publishBarrierRollbackRegression(){
  const ctx=basicCtx(),calls=[];
  const oldPayload={meta:{completed_gameweek:4}},newPayload={meta:{completed_gameweek:5}},world={id:'w1',payload:oldPayload};
  let scoreAttempts=0;
  ctx.FMCloud={
    async publishWorld(payload){calls.push('publish');world.payload=payload;return payload},
    isCreator:()=>true,getWorld:()=>world,
    async loadWorld(force){calls.push(`reload:${!!force}`);return oldPayload}
  };
  ctx.FMSessionRPC={async call(fn){calls.push(fn);if(fn==='fmfantasy_creator_score_world_managers'){scoreAttempts++;throw new Error('score fail')}if(fn==='fmfantasy_undo_last_import')return {ok:true};throw new Error('unexpected')}};
  run('publishscorebarrier.js',ctx);ctx.FMPublishScoreBarrier.install();
  let threw=false;
  try{await ctx.FMCloud.publishWorld(newPayload)}catch(e){threw=true;assert(String(e.message).includes('rolled back safely'))}
  assert(threw,'failed manager scoring must reject import completion');
  assert.strictEqual(scoreAttempts,4,'scoring must retry before rollback');
  assert.strictEqual(calls.filter(x=>x==='fmfantasy_undo_last_import').length,1,'failed scoring must invoke one undo');
  assert(calls.includes('reload:true'),'successful server rollback must reload canonical world');
  assert.strictEqual(world.payload,oldPayload,'local world must be restored after rollback');
}

function packedBundleRegression(){
  const zlib=require('zlib'),parts=[...Array(17)].map((_,i)=>`app/part${String(i).padStart(2,'0')}`).concat(['app/fix17','app/fix18','app/fix19','app/fix20']);
  const html=zlib.gunzipSync(Buffer.from(parts.map(p=>fs.readFileSync(p,'utf8').trim()).join(''),'base64')).toString('utf8');
  const start=html.indexOf('function confirmTransfers()');assert(start>=0,'production bundle confirmTransfers missing');
  const end=html.indexOf('\nfunction ',start+20);const fn=html.slice(start,end>start?end:start+8000);
  assert(fn.includes('state.lockedSquad=[...state.squad]'),'confirmed transfer must lock the new squad');
  assert(fn.includes('state.lockedBank=Number(state.bank||0)'),'confirmed transfer must lock the new bank');
  assert(html.includes('function transferSessionBase()'),'production bundle transfer baseline function missing');
}

(async()=>{
  transferBaselineRegression();
  transferRolloverRegression();
  await publishBarrierSuccessRegression();
  await publishBarrierRollbackRegression();
  packedBundleRegression();
  console.log('V33 core integrity regressions passed');
})().catch(err=>{console.error(err);process.exit(1)});
