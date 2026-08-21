'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const source=fs.readFileSync('newspersistencev3.js','utf8');

// Persistence must remain passive: never replace import/storage or manager-save functions.
assert(!/fmStoredSet\s*=/.test(source),'News persistence must not wrap fmStoredSet');
assert(!/queueManagerSave\s*=/.test(source),'News persistence must not wrap queueManagerSave');
assert(source.includes('if(restoring||importMode()||Date.now()>captureUntil)return false;'),'snapshot writes must be blocked during imports');
assert(source.includes('if(nativeQuality()>0)return false;'),'native generated News must win over persistence');
assert(source.includes('const stateChanged=applyStateNews(snap.state_news);'),'state.news must restore independently');
assert(source.includes('const globalChanged=applyGlobalNews(snap.global_news);'),'global NEWS must restore independently');

let clock=1_700_000_000_000;
class FakeDate extends Date{
  constructor(...args){super(...(args.length?args:[clock]));}
  static now(){return clock;}
}
const storage=new Map();
const localStorage={
  getItem:k=>storage.has(k)?storage.get(k):null,
  setItem:(k,v)=>storage.set(k,String(v)),
  removeItem:k=>storage.delete(k)
};
const world={
  id:'world-test',payload_version:7,
  payload:{meta:{fingerprint:'fp-1',snapshot_date:'2025-08-30',completed_gameweek:4,played_results:50},players:[{pid:'1'},{pid:'2'}]}
};
const context={
  console,JSON,Math,Object,Array,String,Number,Boolean,RegExp,FakeDate,Date:FakeDate,localStorage,
  state:{news:{injuries:[{pid:'10'}],suspensions:[{pid:'11'}]}},
  MutationObserver:class{observe(){}},
  setTimeout:()=>0,setInterval:()=>0,clearInterval:()=>{},
  renderAll:()=>{context.renderCount++},renderCount:0,
  document:{hidden:false,documentElement:{},getElementById:()=>null,addEventListener:()=>{}},
  window:{
    __FM_IMPORT_MODE_ACTIVE:'season',
    NEWS:[{type:'injury',pid:'10'}],
    FMCloud:{getWorld:()=>world,managerState:{news:{}}},
    FMRegistrationNewsGuard:{refresh:()=>{}},
    FMNewsClubFilter:{install:()=>{}},
    addEventListener:()=>{},dispatchEvent:()=>{}
  }
};
context.globalThis=context;
vm.createContext(context);
vm.runInContext(source,context,{filename:'newspersistencev3.js'});
const api=context.window.FMNewsPersistence;
assert(api,'FMNewsPersistence API missing');

// 1) During a season import the persistence layer must neither save nor restore anything.
api.startCapture('season import',5000);
assert.strictEqual(api.saveCandidate('during import'),false,'must not save while import mode is active');
assert.strictEqual(storage.size,0,'no snapshot may be written during import');
assert.strictEqual(api.restore('during import'),false,'must not restore while import mode is active');

// 2) Once import mode ends, the generated News can be snapshotted.
context.window.__FM_IMPORT_MODE_ACTIVE='';
api.startCapture('post import',5000);
assert.strictEqual(api.saveCandidate('post import'),true,'meaningful generated News should save after import');
assert.strictEqual(storage.size,1,'one local News snapshot should exist');
const saved=JSON.parse([...storage.values()][0]);
assert(saved.quality>0,'saved snapshot must be meaningful');
assert.strictEqual(saved.state_news.injuries.length,1);
assert.strictEqual(saved.global_news.length,1);

// 3) Refresh scenario: native News is empty, so the saved snapshot is restored.
context.state.news={};
context.window.NEWS.length=0;
context.window.FMCloud.managerState.news={};
clock+=6000;
assert.strictEqual(api.nativeQuality(),0,'refresh fixture should start with empty native News');
assert.strictEqual(api.restore('refresh'),true,'empty refresh must restore saved News');
assert.strictEqual(context.state.news.injuries.length,1,'state.news injuries were not restored');
assert.strictEqual(context.window.NEWS.length,1,'global NEWS dataset was not restored');

// 4) Native generated News always wins; persistence must not overwrite it.
context.state.news={injuries:[{pid:'99'}]};
context.window.NEWS=[{type:'injury',pid:'99'}];
assert(api.nativeQuality()>0,'native News fixture should be meaningful');
assert.strictEqual(api.restore('native wins'),false,'persistence must not overwrite live generated News');
assert.strictEqual(context.state.news.injuries[0].pid,'99');
assert.strictEqual(context.window.NEWS[0].pid,'99');

console.log('news persistence v5 regression passed');
