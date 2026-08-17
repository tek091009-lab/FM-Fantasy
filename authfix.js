(()=>{
 const cfg=window.FM_FANTASY_CONFIG||{},hasCfg=!!(cfg.supabaseUrl&&cfg.supabaseAnonKey&&!/YOUR_/.test(cfg.supabaseUrl+cfg.supabaseAnonKey));
 let client=null,session=null,profile=null,world=null,saveTimer=null;
 const synthetic=u=>`${String(u||'').trim().toLowerCase().replace(/[^a-z0-9._-]/g,'')}@users.fmfantasy.app`;
 const msg=t=>{const e=document.getElementById('authMsg');if(e)e.textContent=t||''};const gate=()=>document.getElementById('authGate');
 const setRoleUI=()=>{document.body.dataset.role=profile?.role||'user';const b=document.getElementById('cloudBadge'),u=document.getElementById('cloudUser');if(b)b.classList.toggle('online',!!session);if(u)u.textContent=profile?`${profile.username} · ${profile.role==='creator'?'Creator':'Manager'}`:'Offline'};
 const cacheKey=id=>`fmFantasyWorldUpdatedAt:${id||''}`;
 function clearLegacyListeners(){['authLoginTab','authSignupTab','roleUser','roleCreator','authSubmit','authPassword'].forEach(id=>{const el=document.getElementById(id);if(!el||!el.parentNode)return;const c=el.cloneNode(true);el.parentNode.replaceChild(c,el)})}
 function normaliseManagerState(input){
  const out=JSON.parse(JSON.stringify(input||{}));
  const fallbackGw=Number(out.currentGameweek||out.entryGameweek||1)||1;
  let entry=Number(out.entryGameweek||fallbackGw)||fallbackGw;if(entry<1)entry=fallbackGw;
  out.entryGameweek=entry;
  const h=Array.isArray(out.pointsHistory)?out.pointsHistory:[];out.pointsHistory=h.filter(x=>(Number(x?.gw)||0)>=entry);
  const histDone=out.pointsHistory.length?Math.max(...out.pointsHistory.map(x=>Number(x?.gw)||0)):entry-1;
  out.completedGameweek=Math.max(entry-1,histDone);
  out.currentGameweek=Math.max(entry,out.completedGameweek+1);
  out.totalPoints=out.pointsHistory.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0);
  out.firstGameweekPlayed=out.pointsHistory.length>0;
  if(out.gameweekLineups&&typeof out.gameweekLineups==='object'&&!Array.isArray(out.gameweekLineups)){out.gameweekLineups=Object.fromEntries(Object.entries(out.gameweekLineups).filter(([k])=>(Number(k)||0)>=entry))}
  if(Array.isArray(out.leagues)){const uname=String(profile?.username||'').toLowerCase();for(const l of out.leagues){if(!Array.isArray(l?.members))continue;for(const m of l.members){if(m?.own||String(m?.name||'').toLowerCase()===uname){m.entryGameweek=entry;m.points=out.totalPoints;m.pointsHistory=[...out.pointsHistory];m.currentGameweek=out.currentGameweek}}}}
  return out;
 }
 async function bootstrap(){if(!hasCfg){msg('Cloud setup is not connected yet.');return}if(!window.supabase){msg('Login service failed to load. Refresh the page.');return}client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});const{data}=await client.auth.getSession();session=data.session;if(session)await hydrate();else showGate();client.auth.onAuthStateChange(async(_e,s)=>{session=s;if(s)await hydrate();else showGate()})}
 function showGate(){gate()?.classList.remove('hidden');profile=world=null;setRoleUI()}
 async function hydrate(){
  const uid=session.user.id;const{data:p,error}=await client.from('profiles').select('*').eq('user_id',uid).single();if(error||!p){msg('Account profile could not be loaded.');showGate();return}profile=p;
  const{data:m,error:me}=await client.from('world_members').select('world_id').eq('user_id',uid).limit(1).maybeSingle();if(me||!m?.world_id){msg(me?.message||'Shared FM world could not be loaded.');showGate();return}
  /* Do NOT select('*') here: payload is multi-megabyte and loadWorld handles it once/cached. */
  const{data:w,error:we}=await client.from('worlds').select('id,creator_id,name,join_code,updated_at').eq('id',m.world_id).single();if(we||!w){msg(we?.message||'Shared FM world could not be loaded.');showGate();return}world=w;
  const{data:ms}=await client.from('manager_states').select('state').eq('world_id',world.id).eq('user_id',uid).maybeSingle();const raw=ms?.state||{},clean=normaliseManagerState(raw);window.FMCloud.managerState=clean;
  if(JSON.stringify(raw)!==JSON.stringify(clean))await client.from('manager_states').upsert({world_id:world.id,user_id:uid,state:clean,updated_at:new Date().toISOString()},{onConflict:'world_id,user_id'});
  gate()?.classList.add('hidden');setRoleUI();
  try{if(window.FMCloud.managerState&&typeof state!=='undefined'){state=Object.assign({},DEFAULT,window.FMCloud.managerState);state.chips=state.chips||JSON.parse(JSON.stringify(DEFAULT.chips))}if(typeof loadServerImportState==='function')await loadServerImportState();if(typeof renderAll==='function')renderAll()}catch(e){console.error('Direct cloud database restore failed',e)}
  window.dispatchEvent(new Event('fmcloudready'));
 }
 async function login(){const u=document.getElementById('authUsername').value.trim(),p=document.getElementById('authPassword').value;if(!u||!p)return msg('Enter your username and password.');msg('Logging in…');const{error}=await client.auth.signInWithPassword({email:synthetic(u),password:p});if(error)msg(error.message)}
 async function signup(){const username=document.getElementById('authUsername').value.trim(),password=document.getElementById('authPassword').value,role=document.getElementById('roleCreator').classList.contains('active')?'creator':'user';if(username.length<3||password.length<6)return msg('Use a username of at least 3 characters and a password of at least 6 characters.');const code=document.getElementById('authWorldCode').value.trim().toUpperCase(),worldName=document.getElementById('authWorldName').value.trim()||`${username}'s FM Fantasy`;if(role==='user'&&!code)return msg('Enter the creator code.');msg('Creating account…');let payload;try{const r=await fetch(`${cfg.supabaseUrl}/functions/v1/fmfantasy-signup`,{method:'POST',headers:{'Content-Type':'application/json','apikey':cfg.supabaseAnonKey},body:JSON.stringify({username,password,role,worldName,joinCode:code||null})});payload=await r.json();if(!r.ok||payload?.error)return msg(payload?.error||'Could not create account.')}catch(e){return msg(e?.message||'Could not create account.')}const{data,error}=await client.auth.signInWithPassword({email:synthetic(username),password});if(error)return msg(error.message);session=data.session;await hydrate();if(role==='creator'&&payload?.joinCode)alert(`Creator account ready. Your join code is ${payload.joinCode}`)}
 let signupMode=false;function setMode(signup){signupMode=signup;document.getElementById('authSignupFields').style.display=signup?'block':'none';document.getElementById('authLoginTab').classList.toggle('active',!signup);document.getElementById('authSignupTab').classList.toggle('active',signup);document.getElementById('authSubmit').textContent=signup?'Create Account':'Log In';msg('')}
 function setRole(role){document.getElementById('roleUser').classList.toggle('active',role==='user');document.getElementById('roleCreator').classList.toggle('active',role==='creator');document.getElementById('worldCodeField').style.display=role==='user'?'block':'none';document.getElementById('worldNameField').style.display=role==='creator'?'block':'none'}
 async function refreshWorldStamp(){if(!client||!world?.id)return null;const{data,error}=await client.from('worlds').select('updated_at').eq('id',world.id).single();if(!error&&data?.updated_at){world.updated_at=data.updated_at;try{localStorage.setItem(cacheKey(world.id),String(data.updated_at))}catch(_){}}return world.updated_at||null}
 async function publishWorld(payload){if(!profile||profile.role!=='creator'||!world)return;const text=payload==null?null:JSON.stringify(payload);const{error}=await client.rpc('fmfantasy_publish_world',{p_world_id:world.id,p_payload_text:text});if(error)throw error;world.payload=payload;await refreshWorldStamp()}
 async function loadWorld(){
  if(!world)return null;
  const remoteStamp=String(world.updated_at||'');
  let localStamp='';try{localStamp=localStorage.getItem(cacheKey(world.id))||''}catch(_){}
  if(remoteStamp&&localStamp===remoteStamp&&typeof window.fmStoredGet==='function'){
    try{const local=await window.fmStoredGet();if(local&&Array.isArray(local.players)&&local.meta){world.payload=local;return local}}catch(_){}
  }
  const{data,error}=await client.from('worlds').select('payload,updated_at').eq('id',world.id).single();if(error)throw error;
  let payload=data?.payload||null;if(data?.updated_at)world.updated_at=data.updated_at;
  if(!payload&&profile?.role==='creator'&&typeof window.fmStoredGet==='function'){const local=await window.fmStoredGet();if(local){await publishWorld(local);payload=local}}
  if(payload){world.payload=payload;try{localStorage.setItem(cacheKey(world.id),String(world.updated_at||data?.updated_at||''))}catch(_){}}
  return payload
 }
 window.FMCloud={managerState:null,ready:()=>!!(client&&session&&profile&&world),isCreator:()=>profile?.role==='creator',publishWorld,loadWorld,queueManagerSave:st=>{if(!client||!session||!world)return;const clean=normaliseManagerState(st);clearTimeout(saveTimer);saveTimer=setTimeout(async()=>{const{error}=await client.from('manager_states').upsert({world_id:world.id,user_id:session.user.id,state:clean,updated_at:new Date().toISOString()},{onConflict:'world_id,user_id'});if(error)console.warn('Manager cloud save failed',error)},650)},logout:()=>client?.auth.signOut(),getWorld:()=>world,getProfile:()=>profile,normaliseManagerState};
 clearLegacyListeners();document.getElementById('authLoginTab')?.addEventListener('click',()=>setMode(false));document.getElementById('authSignupTab')?.addEventListener('click',()=>setMode(true));document.getElementById('roleUser')?.addEventListener('click',()=>setRole('user'));document.getElementById('roleCreator')?.addEventListener('click',()=>setRole('creator'));document.getElementById('authSubmit')?.addEventListener('click',()=>signupMode?signup():login());document.getElementById('authPassword')?.addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('authSubmit').click()});bootstrap().catch(e=>msg(String(e.message||e)));
})();