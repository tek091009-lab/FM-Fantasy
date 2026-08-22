'use strict';
const fs=require('fs');const vm=require('vm');
function must(x,msg){if(!x)throw new Error(msg)}
const source=fs.readFileSync('newstransferstabilityv40.js','utf8');
must(source.includes('news-transfer-stability-v41-content-signature-authority'),'V41 version missing');
must(source.includes('transferSig'),'transfer content signature missing');
must(source.includes('registrationSig'),'registration content signature missing');
must(source.includes('new MutationObserver'),'mutation guard missing');
must(source.includes('FMRegistrationNewsGuard'),'canonical renderer bridge missing');
must(source.includes('FMNewsAestheticV34?.apply?.()'),'same-frame aesthetic reconciliation missing');
let transferEvents=[{id:'1',old_club:'A',new_club:'B',date:'2025-09-13'},{id:'2',old_club:'C',new_club:'D',date:'2025-09-13'}],registrationEvents=[{id:'3',club:'B',kind:'registration',date:'2025-09-13'}];
const transferHost={dataset:{fmSig:'stale-but-same-count'},rowCount:2,empty:false,contains:n=>n&&n.canonical===true,querySelectorAll(sel){return sel==='.fmNewsTransferRow'?Array.from({length:this.rowCount},()=>({canonical:true})):[]},querySelector(sel){return sel==='.fmNewsCanonicalEmpty'&&this.empty?{}:null}};
const legacy={style:{},canonical:false};
const transferCard={querySelector(sel){return sel==='.fmCanonicalTransferRows'?transferHost:null},querySelectorAll(sel){return sel==='[data-news-text],.transfer'?[legacy,{style:{},canonical:true}]:[]}};
const regRows={dataset:{fmSig:'stale-but-same-count'},rowCount:1,empty:false,querySelectorAll(sel){return sel==='.newsRegRow'?Array.from({length:this.rowCount},()=>({})):[]},querySelector(sel){return sel==='.fmNewsCanonicalEmpty'&&this.empty?{}:null}};
const regCard={querySelector(sel){return sel==='.newsRegRows'?regRows:null}};
const document={documentElement:{},getElementById(id){return id==='newsTransfers'?transferCard:id==='newsRegistrations'?regCard:null},addEventListener(){}};
const window={FMCloud:{getWorld:()=>({payload:{meta:{transfer_news_guard:{events:transferEvents},registration_news:{events:registrationEvents}}}})},addEventListener(){}};
class MutationObserver{constructor(fn){this.fn=fn}observe(){}}
const ctx={console,window,document,MutationObserver,queueMicrotask:fn=>fn(),setTimeout(){},Array,Object,String,JSON};ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(source,ctx,{filename:'newstransferstabilityv40.js'});
const api=ctx.window.FMNewsTransferStabilityV40;
/* This is the exact V40 hole: row count can be correct while persisted content is stale. */
must(api.transferNeedsRepair(transferCard)===true,'same-count stale transfer content was not detected');
transferHost.dataset.fmSig=api.transferSig(transferEvents);must(api.transferNeedsRepair(transferCard)===false,'correct transfer signature falsely marked broken');
transferHost.rowCount=1;must(api.transferNeedsRepair(transferCard)===true,'missing populated transfer row was not detected');
transferHost.rowCount=2;
transferEvents=[];transferHost.rowCount=0;transferHost.dataset.fmSig=api.transferSig(transferEvents);transferHost.empty=true;must(api.transferNeedsRepair(transferCard)===false,'correct empty canonical transfer host falsely marked broken');
transferEvents=[{id:'1',old_club:'A',new_club:'B',date:'2025-09-13'}];api.hideLegacyTransferRows(transferCard);must(legacy.style.display==='none','legacy transfer renderer was not suppressed');
must(api.registrationNeedsRepair(regCard)===true,'same-count stale registration content was not detected');
regRows.dataset.fmSig=api.registrationSig(registrationEvents);must(api.registrationNeedsRepair(regCard)===false,'correct registration signature falsely marked broken');
console.log('PASS V41 canonical transfer/registration DOM signature authority');
