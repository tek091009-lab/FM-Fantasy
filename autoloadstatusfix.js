(()=>{
'use strict';
const VERSION='autoload-status-sync-v1';
function sync(){
  const world=window.FMCloud?.getWorld?.();
  const payload=world?.payload;
  if(!payload||!Array.isArray(payload.players))return false;
  const n=Number(payload?.meta?.players||payload.players.length||0);
  const syncBox=document.querySelector('.sidebar .syncbox')||document.querySelector('.syncbox');
  if(syncBox){
    for(const el of syncBox.querySelectorAll('*')){
      const t=String(el.textContent||'').trim();
      if(/^No FM save imported yet\.?$/i.test(t))el.textContent=n?`FM database loaded · ${n} players`:'FM database loaded';
    }
  }
  const cloud=document.getElementById('fmCloudDbStatus');
  if(cloud)cloud.textContent=n?`Loaded ${n} players from shared database.`:'Shared database loaded.';
  return true;
}
window.FMAutoLoadStatus={version:VERSION,sync};
window.addEventListener('fmcloudready',()=>setTimeout(sync,0));
if(window.FMCloud?.ready?.())setTimeout(sync,0);
})();
