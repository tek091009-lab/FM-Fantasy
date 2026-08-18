(()=>{
'use strict';
const VERSION='snapshot-date-v1';
const id='fmSnapshotDateBadge';
function worldPayload(){
  try{const w=window.FMCloud?.getWorld?.();if(w?.payload)return w.payload}catch(_){ }
  for(const k of ['FM_IMPORTED_PAYLOAD','FM_PAYLOAD','FM_DATA','IMPORT_PAYLOAD']){try{if(window[k]?.meta)return window[k]}catch(_){ }}
  return null;
}
function cleanDate(v){
  const s=String(v||'').trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(s)?s:null;
}
function fmt(s){
  try{return new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(s+'T12:00:00Z'))}catch(_){return s}
}
function ensure(){
  let el=document.getElementById(id);if(el)return el;
  el=document.createElement('div');el.id=id;
  Object.assign(el.style,{position:'fixed',right:'12px',top:'10px',zIndex:'2147483000',padding:'5px 8px',borderRadius:'9px',background:'rgba(17,10,43,.88)',border:'1px solid rgba(255,255,255,.14)',boxShadow:'0 4px 18px rgba(0,0,0,.22)',color:'#d9d4ee',font:'800 10px/1.15 Inter,system-ui,sans-serif',letterSpacing:'.02em',pointerEvents:'none',backdropFilter:'blur(8px)'});
  document.body.appendChild(el);return el;
}
function render(){
  const p=worldPayload(),m=p?.meta||{};
  const d=cleanDate(m.snapshot_date)||cleanDate(m.availability_save_date)||cleanDate(m.availability_source_save_date);
  const el=ensure();
  if(d){el.textContent='FM data · '+fmt(d);el.title='Accepted FM snapshot data through '+d;el.style.display='block'}
  else if(p&&Array.isArray(p.players)&&p.players.length){el.textContent='FM data · Pre-season';el.title='This accepted base snapshot has no proven dated league history yet.';el.style.display='block'}
  else el.style.display='none';
}
let last='';function tick(){
  const p=worldPayload(),m=p?.meta||{};const sig=[m.snapshot_date,m.availability_save_date,m.availability_source_save_date,m.payload_version,p?.players?.length].join('|');
  if(sig!==last){last=sig;render()}
}
setInterval(tick,750);window.addEventListener('fmcloudready',()=>setTimeout(render,0));document.addEventListener('DOMContentLoaded',render);
window.FMSnapshotDate={version:VERSION,render};
})();
