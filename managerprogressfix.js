(()=>{
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  let busy=false,lastTarget=0,lastRun=0;

  async function finaliseOwnManagerProgress(){
    try{
      if(busy||typeof state==='undefined'||!state?.teamConfirmed)return false;
      const meta=window.META||{};
      const target=Number(meta.completed_gameweek||0);
      const done=Number(state.completedGameweek||0);
      if(!target)return false;
      if(done>=target&&state.firstGameweekPlayed)return false;
      const fn=typeof window.syncManagerProgressFromHistory==='function'
        ? window.syncManagerProgressFromHistory
        : (typeof syncManagerProgressFromHistory==='function'?syncManagerProgressFromHistory:null);
      if(!fn)return false;
      busy=true;
      const before={done,total:Number(state.totalPoints||0),first:!!state.firstGameweekPlayed};
      fn();
      await sleep(20);
      const afterDone=Number(state.completedGameweek||0);
      if(afterDone>before.done||(!before.first&&state.firstGameweekPlayed)){
        if(typeof save==='function')save();
        if(typeof renderAll==='function')renderAll();
        if(typeof renderLeagues==='function')renderLeagues();
        window.dispatchEvent(new CustomEvent('fmmanagerprogressfinalised',{detail:{from:before.done,to:afterDone,total:Number(state.totalPoints||0)}}));
      }
      lastTarget=target;lastRun=Date.now();
      return afterDone>=target;
    }catch(e){console.warn('Manager progress finalisation failed',e);return false}
    finally{busy=false}
  }

  window.fmFinaliseOwnManagerProgress=finaliseOwnManagerProgress;
  const kick=()=>setTimeout(finaliseOwnManagerProgress,150);
  window.addEventListener('fmcloudready',kick);
  window.addEventListener('focus',kick);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)kick()});
  setTimeout(finaliseOwnManagerProgress,500);
  setInterval(()=>{
    const target=Number((window.META||{}).completed_gameweek||0);
    const done=typeof state!=='undefined'?Number(state.completedGameweek||0):0;
    if(target>done||((typeof state!=='undefined')&&state.teamConfirmed&&!state.firstGameweekPlayed))finaliseOwnManagerProgress();
  },2000);
})();
