'use strict';
const fs=require('fs');const vm=require('vm');
function must(x,msg){if(!x)throw new Error(msg)}
const source=fs.readFileSync('newstransferstabilityv40.js','utf8');
must(source.includes('news-transfer-stability-v40-canonical-dom-authority'),'version missing');
must(source.includes("new MutationObserver"),'mutation guard missing');
must(source.includes("FMRegistrationNewsGuard"),'canonical renderer bridge missing');
must(source.includes("FMNewsAestheticV34?.apply?.()"),'same-frame aesthetic reconciliation missing');
let transferEvents=[{id:'1'},{id:'2'}],registrationEvents=[{id:'3'}];
const transferHost={dataset:{fmSig:'old'},rowCount:1,empty:false,contains:n=>n&&n.canonical===true,querySelectorAll(sel){return sel==='.fmNewsTransferRow'?Array.from({length:this.rowCount},()=>({canonical:true})):[]},querySelector(sel){return sel==='.fmNewsCanonicalEmpty'&&this.empty?{}:null}};
const legacy={style:{},canonical:false};
const transferCard={querySelector(sel){return sel==='.fmCanonicalTransferRows'?transferHost:null},querySelectorAll(sel){return sel==='[data-news-text],.transfer'?[legacy,{style:{},canonical:true}]:[]}};
const regRows={dataset:{fmSig:'old'},rowCount:0,empty:false,querySelectorAll(sel){return sel==='.newsRegRow'?Array.from({length:this.rowCount},()=>({})):[]},querySelector(sel){return sel==='.fmNewsCanonicalEmpty'&&this.empty?{}:null}};
const regCard={querySelector(sel){return sel==='.newsRegRows'?regRows:null}};
const document={documentElement:{},getElementById(id){return id==='newsTransfers'?transferCard:id==='newsRegistrations'?regCard:null},addEventListener(){}};
const window={FMCloud:{getWorld:()=>({payload:{meta:{transfer_news_guard:{events:transferEvents},registration_news:{events:registrationEvents}}}})},addEventListener(){}};
class MutationObserver{constructor(fn){this.fn=fn}observe(){}}
const ctx={console,window,document,MutationObserver,queueMicrotask:fn=>fn(),setTimeout(){},Array,Object,String};ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(source,ctx,{filename:'newstransferstabilityv40.js'});
const api=ctx.window.FMNewsTransferStabilityV40;
must(api.transferNeedsRepair(transferCard)===true,'populated transfer host with missing row was not detected');
transferHost.rowCount=2;must(api.transferNeedsRepair(transferCard)===false,'correct populated transfer host falsely marked broken');
transferEvents=[];transferHost.rowCount=0;transferHost.empty=true;must(api.transferNeedsRepair(transferCard)===false,'correct empty canonical transfer host falsely marked broken');
transferEvents=[{id:'1'}];api.hideLegacyTransferRows(transferCard);must(legacy.style.display==='none','legacy transfer renderer was not suppressed');
must(api.registrationNeedsRepair(regCard)===true,'populated registration host with missing row was not detected');
regRows.rowCount=1;must(api.registrationNeedsRepair(regCard)===false,'correct registration host falsely marked broken');
console.log('PASS V40 canonical populated transfer/registration DOM stability regression');
