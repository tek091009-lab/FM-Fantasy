(()=>{
 const cfg=window.FM_FANTASY_CONFIG||{}, hasCfg=!!(cfg.supabaseUrl&&cfg.supabaseAnonKey&&!/YOUR_/.test(cfg.supabaseUrl+cfg.supabaseAnonKey));
 let client=null,session=null,profile=null,world=null,saveTimer=null;
 const synthetic=u=>`${String(u||'').trim().toLowerCase().replace(/[^a-z0-9._-]/g,'')}@users.fmfantasy.invalid`;
 const msg=t=>{const e=document.getElementById('authMsg');if(e)e.textContent=t||''};
 const gate=()=>document.getElementById('authGate');
 const setRoleUI=()=>{document.body.dataset.role=profile?.role||'user';const b=document.getElementById('cloudBadge'),u=document.getElementById('cloudUser');if(b)b.classList.toggle('online',!!session);if(u)u.textContent=profile?`${profile.username} · ${profile.role==='creator'?'Creator':'Manager'}`:'Offline'};
 async function bootstrap(){
   if(!hasCfg){msg('Cloud setup is not connected yet.');return}
   if(!window.supabase){msg('Login service failed to load. Refresh the page.');return}
   client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
   const {data}=await client.auth.getSession();session=data.session; if(session)await hydrate(); else showGate();
   client.auth.onAuthStateChange(async(_e,s)=>{session=s;if(s)await hydrate();else showGate()});
 }
 function showGate(){gate()?.classList.remove('hidden');profile=world=null;setRoleUI()}
 async function hydrate(){
   const uid=session.user.id;
   const {data:p,error}=await client.from('profiles').select('*').eq('user_id',uid).single();if(error||!p){msg('Account profile could not be loaded.');showGate();return}
   profile=p;
   const {data:w,error:we}=await client.from('world_members').select('world_id, worlds(*)').eq('user_id',uid).limit(1).maybeSingle();if(we){msg(we.message);showGate();return}world=w?.worlds||null;
   const {data:ms}=world?await client.from('manager_states').select('state').eq('world_id',world.id).eq('user_id',uid).maybeSingle():{data:null};
   window.FMCloud.managerState=ms?.state||null;gate()?.classList.add('hidden');setRoleUI();window.dispatchEvent(new Event('fmcloudready'));
 }
 async function login(){const u=document.getElementById('authUsername').value.trim(),p=document.getElementById('authPassword').value;if(!u||!p)return msg('Enter your username and password.');msg('Logging in…');const {error}=await client.auth.signInWithPassword({email:synthetic(u),password:p});if(error)msg(error.message)}
 async function signup(){
   const username=document.getElementById('authUsername').value.trim(),password=document.getElementById('authPassword').value,role=document.getElementById('roleCreator').classList.contains('active')?'creator':'user';if(username.length<3||password.length<6)return msg('Use a username of at least 3 characters and a password of at least 6 characters.');
   const code=document.getElementById('authWorldCode').value.trim().toUpperCase(),worldName=document.getElementById('authWorldName').value.trim()||`${username}'s FM Fantasy`;if(role==='user'&&!code)return msg('Enter the creator code.');
   msg('Creating account…');const {data,error}=await client.auth.signUp({email:synthetic(username),password});if(error)return msg(error.message);if(!data.session)return msg('Account created but automatic login is disabled in Supabase.');
   session=data.session;const {data:worldId,error:rpcErr}=await client.rpc('fmfantasy_finish_signup',{p_username:username,p_role:role,p_world_name:worldName,p_join_code:code||null});if(rpcErr){await client.auth.signOut();return msg(rpcErr.message)}await hydrate();if(role==='creator'&&worldId){const {data:w}=await client.from('worlds').select('join_code').eq('id',worldId).single();if(w?.join_code)alert(`Creator account ready. Your join code is ${w.join_code}`)}
 }
 let signupMode=false;function setMode(signup){signupMode=signup;document.getElementById('authSignupFields').style.display=signup?'block':'none';document.getElementById('authLoginTab').classList.toggle('active',!signup);document.getElementById('authSignupTab').classList.toggle('active',signup);document.getElementById('authSubmit').textContent=signup?'Create Account':'Log In';msg('')}
 function setRole(role){document.getElementById('roleUser').classList.toggle('active',role==='user');document.getElementById('roleCreator').classList.toggle('active',role==='creator');document.getElementById('worldCodeField').style.display=role==='user'?'block':'none';document.getElementById('worldNameField').style.display=role==='creator'?'block':'none'}
 window.FMCloud={managerState:null,ready:()=>!!(client&&session&&profile&&world),isCreator:()=>profile?.role==='creator',publishWorld:async payload=>{if(!profile||profile.role!=='creator'||!world)return;const {error}=await client.from('worlds').update({payload,updated_at:new Date().toISOString()}).eq('id',world.id);if(error)throw error;world.payload=payload},loadWorld:async()=>{if(!world)return null;const {data,error}=await client.from('worlds').select('payload').eq('id',world.id).single();if(error)throw error;return data?.payload||null},queueManagerSave:st=>{if(!client||!session||!world)return;clearTimeout(saveTimer);saveTimer=setTimeout(async()=>{const {error}=await client.from('manager_states').upsert({world_id:world.id,user_id:session.user.id,state:st,updated_at:new Date().toISOString()},{onConflict:'world_id,user_id'});if(error)console.warn('Manager cloud save failed',error)},650)},logout:()=>client?.auth.signOut(),getWorld:()=>world,getProfile:()=>profile};
 document.getElementById('authLoginTab')?.addEventListener('click',()=>setMode(false));document.getElementById('authSignupTab')?.addEventListener('click',()=>setMode(true));document.getElementById('roleUser')?.addEventListener('click',()=>setRole('user'));document.getElementById('roleCreator')?.addEventListener('click',()=>setRole('creator'));document.getElementById('authSubmit')?.addEventListener('click',()=>signupMode?signup():login());document.getElementById('authPassword')?.addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('authSubmit').click()});
 bootstrap().catch(e=>msg(String(e.message||e)));
})();