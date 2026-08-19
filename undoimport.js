(()=>{
'use strict';
const VERSION='undo-last-import-v1';
const ID='fmUndoLastImportBtn';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let busy=false;
function note(text,bad=false){const el=document.getElementById('fmCloudDbStatus');if(el){el.textContent=text;el.style.color=bad?'#ff7b9e':'#b8ffd9';}}
async function client(){
  const cfg=window.FM_FANTASY_CONFIG||{};
  if(!cfg.supabaseUrl||!cfg.supabaseAnonKey||!window.supabase)throw new Error('Cloud connection is not ready.');
  const c=window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
  const {data,error}=await c.auth.getSession();if(error||!data?.session)throw new Error('Creator session is not ready.');
  return c;
}
async function undoLastImport(){
  if(busy)return;busy=true;
  try{
    if(!window.FMCloud?.isCreator?.())throw new Error('Only the FPL Creator can undo an import.');
    const world=window.FMCloud?.getWorld?.();if(!world?.id)throw new Error('Shared world is not ready.');
    if(!confirm('Undo the most recent successful FM import? This restores the exact world from immediately before that import.'))return;
    note('Undoing last import…');
    const c=await client();
    const {error}=await c.rpc('fmfantasy_undo_last_import',{p_world_id:world.id});
    if(error)throw error;
    note('Last import undone. Reloading canonical world…');
    try{localStorage.removeItem(`fmFantasyWorldVersion:${world.id}`)}catch(_e){}
    location.reload();
  }catch(e){console.error('Undo Last Import failed',e);note(e?.message||'Could not undo the last import.',true);alert(e?.message||'Could not undo the last import.');}
  finally{busy=false;}
}
function mount(){
  if(document.getElementById(ID))return;
  const db=document.getElementById('fmCloudDbControls');
  if(!db){setTimeout(mount,250);return;}
  if(!window.FMCloud?.isCreator?.())return;
  const b=document.createElement('button');b.id=ID;b.type='button';b.className='syncBtn';b.textContent='Undo Last Import';b.style.cssText='border-color:#ff8aaa;color:#ffd7e3';b.onclick=undoLastImport;
  const status=document.getElementById('fmCloudDbStatus');db.insertBefore(b,status||null);
}
window.FMUndoLastImport={version:VERSION,run:undoLastImport};
window.addEventListener('fmcloudready',()=>setTimeout(mount,100));
let tries=0;const timer=setInterval(()=>{tries++;mount();if(document.getElementById(ID)||tries>50)clearInterval(timer)},200);
})();