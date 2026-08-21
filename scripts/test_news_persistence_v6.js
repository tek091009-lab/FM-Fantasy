'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const source=fs.readFileSync('newspersistencev4.js','utf8');

assert(!/fmStoredSet\s*=/.test(source),'News persistence must never wrap fmStoredSet');
assert(!/queueManagerSave\s*=/.test(source),'News persistence must never wrap queueManagerSave');
assert(source.includes("const VERSION='news-persistence-v6-import-snapshot-authority'"));
assert(source.includes('if(restoring||!armed())return false;'),'passive snapshot save must remain allowed while import mode is active');
assert(source.includes('if(restoring||importMode()||armed())return false;'),'restore must remain blocked during a live import/capture window');
assert(!/return \[[^\n]*payload_version/.test(source),'snapshot identity must not depend on refresh-time payload_version');

let clock=1_700_000_000_000;
class FakeDate extends Date{constructor(...args){super(...(args.length?args:[clock]));}static now(){return clock;}}
const storage=new Map();
const localStorage={getItem:k=>storage.has(k)?storage.get(k):null,setItem:(k,v)=>storage.set(k,String(v)),removeItem:k=>storage.delete(k)};
const world={id:'world-test',payload_version:7,payload:{meta:{fingerprint:'fp-1',snapshot_date:'2025-08-30',completed_gameweek:4,played_results:50},players:[{pid:'1'},{pid:'2'}]}};
const context={
 console,JSON,Math,Object,Array,String,Number,Boolean,RegExp,Date:FakeDate,localStorage,
 state:{news:{injuries:[{pid:'10'}],suspensions:[{pid:'11'}]}},
 MutationObserver:class{observe(){}},
 setTimeout:()=>0,setInterval:()=>0,clearInterval:()=>{},
 renderAll:()=>{context.renderCount++},renderCount:0,
 document:{hidden:false,documentElement:{},getElementById:()=>null,addEventListener:()=>{}},
 window:{__FM_IMPORT_MODE_ACTIVE:'season',NEWS:[{type:'injury',pid:'10'}],FMCloud:{getWorld:()=>world,managerState:{news:{}}},FMRegistrationNewsGuard:{refresh:()=>{}},FMNewsClubFilter:{install:()=>{}},addEventListener:()=>{},dispatchEvent:()=>{}}
};
context.globalThis=context;vm.createContext(context);vm.runInContext(source,context,{filename:'newspersistencev4.js'});
const api=context.window.FMNewsPersistence;assert(api);

// 1) Critical real-world case: News is already visible while import mode still says season.
api.startCapture('season import visible News',5000);
assert.strictEqual(api.saveCandidate('visible before import flag cleared'),true,'visible News must be saved even while import mode is still active');
assert.strictEqual(storage.size,1);
let saved=JSON.parse([...storage.values()][0]);
assert.strictEqual(saved.state_news.injuries[0].pid,'10');
assert.strictEqual(saved.global_news[0].pid,'10');

// 2) Refresh changes payload_version and native state, but the imported News snapshot remains authoritative.
context.window.__FM_IMPORT_MODE_ACTIVE='';
world.payload_version=99;
context.state.news={injuries:[{pid:'99'}]};
context.window.NEWS=[{type:'injury',pid:'99'}];
context.window.FMCloud.managerState.news={};
clock+=6000;
assert.strictEqual(api.restore('refresh'),true,'same imported database must restore even when payload_version changes');
assert.strictEqual(context.state.news.injuries[0].pid,'10','refresh must not replace imported News');
assert.strictEqual(context.window.NEWS[0].pid,'10','global News must be restored from the imported snapshot');

// 3) The next import is the only event allowed to replace the snapshot.
context.window.__FM_IMPORT_MODE_ACTIVE='update';
world.payload.meta.fingerprint='fp-2';world.payload.meta.snapshot_date='2025-09-06';world.payload.meta.completed_gameweek=5;world.payload.meta.played_results=62;world.payload.players.push({pid:'3'});
context.state.news={injuries:[{pid:'20'}],suspensions:[]};
context.window.NEWS=[{type:'injury',pid:'20'}];
api.startCapture('next import',5000);
assert.strictEqual(api.saveCandidate('next import visible News'),true,'next import must replace the prior snapshot');
saved=JSON.parse([...storage.values()][0]);assert.strictEqual(saved.fingerprint,'fp-2');assert.strictEqual(saved.state_news.injuries[0].pid,'20');

context.window.__FM_IMPORT_MODE_ACTIVE='';clock+=6000;context.state.news={};context.window.NEWS.length=0;
assert.strictEqual(api.restore('post update refresh'),true);
assert.strictEqual(context.state.news.injuries[0].pid,'20');
assert.strictEqual(context.window.NEWS[0].pid,'20');

console.log('news persistence v6 regression passed');