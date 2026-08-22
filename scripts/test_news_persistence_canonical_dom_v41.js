'use strict';
const fs=require('fs');const vm=require('vm');
function must(x,msg){if(!x)throw new Error(msg)}
const source=fs.readFileSync('newspersistencev5.js','utf8');
must(source.includes('news-persistence-v8-canonical-transfer-dom-authority'),'V41 persistence version missing');
must(source.includes("CANONICAL_DOM_IDS=new Set(['newsTransfers','newsRegistrations'])"),'canonical DOM ownership set missing');
must(source.includes('if(CANONICAL_DOM_IDS.has(id))continue'),'saved DOM is still allowed to repaint canonical cards');
must(source.includes('FMNewsTransferStabilityV40?.stabilise?.()'),'canonical reconciliation after persistence restore missing');
const make=(html)=>({innerHTML:html,dataset:{},querySelectorAll(){return[]}});
const els={newsTransfers:make('<canonical-transfers>'),newsRegistrations:make('<canonical-registrations>'),newsPriceUp:make('<current-price-up>')};
const document={
  hidden:false,documentElement:{},
  getElementById(id){return els[id]||null},
  addEventListener(){}
};
class MutationObserver{constructor(fn){this.fn=fn}observe(){}}
const localStorage={getItem(){return null},setItem(){},removeItem(){}};
const sessionStorage={removeItem(){}};
const window={addEventListener(){},FMNewsClubFilter:{install(){}}};
const ctx={console,window,document,MutationObserver,localStorage,sessionStorage,JSON,Object,Array,String,Number,Math,Date,Set,setTimeout(){},setInterval(){return 1},clearInterval(){}};ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(source,ctx,{filename:'newspersistencev5.js'});
const changed=ctx.window.FMNewsPersistence.restoreDom({sections:{
  newsTransfers:{html:'<stale-transfer-dom>',cleared:''},
  newsRegistrations:{html:'<stale-registration-dom>',cleared:''},
  newsPriceUp:{html:'<persisted-price-up>',cleared:''}
}});
must(changed===true,'non-canonical persisted section did not restore');
must(els.newsTransfers.innerHTML==='<canonical-transfers>','persistence repainted canonical transfers');
must(els.newsRegistrations.innerHTML==='<canonical-registrations>','persistence repainted canonical registrations');
must(els.newsPriceUp.innerHTML==='<persisted-price-up>','ordinary News persistence was broken');
must(ctx.window.FMNewsPersistence.canonicalDomIds.join('|')==='newsTransfers|newsRegistrations','canonical ownership metadata wrong');
console.log('PASS V41 persistence cannot repaint canonical transfer or registration cards');
