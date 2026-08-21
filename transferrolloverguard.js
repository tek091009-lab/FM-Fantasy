(()=>{
  const VERSION='transfer-rollover-guard-v1-boundary-only';
  let source=null,wrapped=null;
  const stateRef=()=>{try{return window.state||state||null}catch(_){return window.state||null}};
  const saveNow=()=>{try{if(typeof window.save==='function')return window.save();if(typeof save==='function')return save()}catch(_){}};
  const gwOf=s=>Number(s?.currentGameweek||window.META?.current_gameweek||0);

  function wrap(fn){
    const guard=function(...args){
      const s=stateRef();
      if(!s)return fn.apply(this,args);
      const gw=gwOf(s),previousRoll=Number(s.lastTransferRollGW||0);
      const suppressClientRollover=gw>0&&previousRoll<gw;
      if(suppressClientRollover)s.lastTransferRollGW=gw;
      try{
        return fn.apply(this,args);
      }finally{
        if(suppressClientRollover){
          // confirmTransfers must spend the persisted balance, never create the
          // current Gameweek's allowance. Restore the boundary marker so the
          // server scorer can award the next Gameweek correctly.
          s.lastTransferRollGW=previousRoll;
          saveNow();
        }
      }
    };
    guard.__fmTransferRolloverGuard=true;
    guard.__fmOriginalConfirmTransfers=fn;
    return guard;
  }

  function install(){
    const current=window.confirmTransfers;
    if(typeof current!=='function')return false;
    if(current.__fmTransferRolloverGuard){wrapped=current;source=current.__fmOriginalConfirmTransfers||source}
    else if(current!==source){source=current;wrapped=wrap(current);window.confirmTransfers=wrapped}
    if(!source||!wrapped)return false;
    document.querySelectorAll('*').forEach(el=>{if(el.onclick===source)el.onclick=wrapped});
    return true;
  }

  const observer=new MutationObserver(()=>install());
  const start=()=>{install();observer.observe(document.documentElement,{childList:true,subtree:true});[50,150,400,1000,2500].forEach(ms=>setTimeout(install,ms))};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.FMTransferRolloverGuard={version:VERSION,install,status:()=>({version:VERSION,installed:!!wrapped,source:!!source})};
})();
