(()=>{
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 const client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 let lastLeagueSig='';
 const pts=s=>Array.isArray(s?.pointsHistory)?s.pointsHistory.reduce((n,x)=>n+Number(x?.net??x?.gross??0),0):Number(s?.totalPoints||0);
 const memberFrom=(uid,s,p,selfUid)=>({own:uid===selfUid,name:p?.username||'Manager',team:s?.teamName||'My Team',points:pts(s),squad:[...(s?.squad||[])],starters:[...(s?.starters||[])],bench:[...(s?.bench||[])],captain:s?.captain||null,vice:s?.vice||null,entryGameweek:s?.entryGameweek||null,currentGameweek:s?.currentGameweek||null,teamConfirmed:!!s?.teamConfirmed,pointsHistory:[...(s?.pointsHistory||[])]});
 async function session(){return (await client.auth.getSession()).data.session}
 async function peerData(){
  const s=await session();if(!s||!window.FMCloud?.ready?.())return null;
  const world=window.FMCloud.getWorld?.();if(!world?.id)return null;
  const [{data:states,error:se},{data:profiles,error:pe}]=await Promise.all([client.from('manager_states').select('user_id,state').eq('world_id',world.id),client.from('profiles').select('user_id,username,role,created_at')]);
  if(se||pe){console.warn('Shared manager sync failed',se||pe);return null}
  return{s,world,states:states||[],profiles:new Map((profiles||[]).map(x=>[x.user_id,x]))};
 }
 async function syncNews(){
  try{
   const d=await peerData();if(!d||typeof state==='undefined')return;
   const creatorRow=d.states.find(x=>x.user_id===d.world.creator_id),creatorState=creatorRow?.state||{};
   let news=creatorState.news||null,active=creatorState.activeStatuses||null;
   const payload=await window.FMCloud.loadWorld?.();
   if(!news&&payload&&typeof fmBuildInitialNews==='function')news=fmBuildInitialNews(payload);
   if(!active&&news)active={injuries:news.injuries||[],suspensions:news.suspensions||[]};
   let changed=false;
   if(news&&JSON.stringify(state.news)!==JSON.stringify(news)){state.news=news;changed=true}
   if(active&&JSON.stringify(state.activeStatuses)!==JSON.stringify(active)){state.activeStatuses=active;changed=true}
   if(changed){if(typeof save==='function')save();if(typeof renderNews==='function')renderNews()}
  }catch(e){console.warn('Shared news sync failed',e)}
 }
 async function syncLeagues(){
  try{
   const d=await peerData();if(!d||typeof state==='undefined'||!Array.isArray(state.leagues))return;
   const all=[];
   for(const row of d.states){const st=row.state||{};for(const l of (st.leagues||[]))if(l?.code)all.push({uid:row.user_id,state:st,league:l,profile:d.profiles.get(row.user_id)})}
   const mine=state.leagues||[];let changed=false;
   for(const l of mine){if(!l?.code)continue;const code=String(l.code).toUpperCase(),matches=all.filter(x=>String(x.league.code).toUpperCase()===code);if(!matches.length)continue;
    const canonical=matches.map(x=>x.league?.name).find(n=>n&&!new RegExp('^League\\s+'+code+'$','i').test(n));if(canonical&&l.name!==canonical){l.name=canonical;changed=true}
    const seen=new Set(),members=[];for(const x of matches){if(seen.has(x.uid))continue;seen.add(x.uid);members.push(memberFrom(x.uid,x.state,x.profile,d.s.user.id))}
    members.sort((a,b)=>Number(b.points||0)-Number(a.points||0));
    const sig=JSON.stringify(members.map(m=>[m.name,m.team,m.points,m.own,m.entryGameweek]));if(JSON.stringify((l.members||[]).map(m=>[m.name,m.team,m.points,m.own,m.entryGameweek]))!==sig){l.members=members;changed=true}
   }
   const sig=JSON.stringify(mine.map(l=>[l.code,l.name,(l.members||[]).map(m=>[m.name,m.team,m.points,m.own])]));
   if(sig!==lastLeagueSig||changed){lastLeagueSig=sig;if(typeof renderLeagues==='function')renderLeagues();if(changed&&typeof save==='function')save()}
  }catch(e){console.warn('Shared league sync failed',e)}
 }
 function fixTeamView(){const page=document.getElementById('teamPage'),banner=document.getElementById('viewBanner');if(!page||!banner)return;page.classList.toggle('leagueReadOnly',banner.classList.contains('show'))}
 function addStyles(){
  if(document.getElementById('fmAccountFeatureStyles'))return;const s=document.createElement('style');s.id='fmAccountFeatureStyles';s.textContent=`
  #teamPage.leagueReadOnly .teamGrid{grid-template-columns:minmax(0,1180px)!important;max-width:1180px!important;justify-content:center!important}
  #teamPage.leagueReadOnly .pitchCard{width:100%!important;max-width:1180px!important;margin:0 auto!important}
  #teamPage.leagueReadOnly .summary,#teamPage.leagueReadOnly #viewBanner{max-width:1180px!important}
  #teamPage.leagueReadOnly .pitch{width:min(1050px,100%)!important}
  #fmSettingsModal{position:fixed;inset:0;z-index:100000;display:none;place-items:center;background:rgba(4,2,16,.72);backdrop-filter:blur(8px)}
  #fmSettingsModal.show{display:grid}#fmSettingsCard{width:min(440px,calc(100vw - 30px));padding:22px;border:1px solid rgba(255,255,255,.12);border-radius:20px;background:linear-gradient(180deg,#1a113c,#0e0a27);box-shadow:0 24px 70px rgba(0,0,0,.5);color:#fff}
  #fmSettingsCard h2{margin:0 0 4px;font-size:22px}#fmSettingsCard .sub{color:#9c93b3;font-size:12px;margin-bottom:18px}.fmSetRow{display:grid;gap:6px;margin:12px 0}.fmSetRow label{font-size:10px;color:#aaa0bf;text-transform:uppercase;letter-spacing:.06em}.fmSetRow input{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:#100b2a;color:#fff;outline:none}.fmSetMeta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.fmSetMeta div{padding:11px;border-radius:11px;background:#120c2d;border:1px solid rgba(255,255,255,.07)}.fmSetMeta small{display:block;color:#8f85a5;font-size:9px}.fmSetMeta b{display:block;margin-top:3px;font-size:12px;overflow:hidden;text-overflow:ellipsis}.fmSetActions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.fmSetBtn{border:0;border-radius:10px;padding:10px 13px;font-weight:900;cursor:pointer;color:#fff;background:#6f35ff}.fmSetBtn.dark{background:#21183f}.fmSetBtn.danger{background:#a9234e}.fmSetMsg{min-height:18px;margin-top:10px;color:#a9a1c6;font-size:11px}
  #accountSettingsBtn{margin-top:3px}
  `;document.head.appendChild(s)
 }
 function mountSettings(){
  if(document.getElementById('accountSettingsBtn'))return;addStyles();
  const nav=document.querySelector('.snav');if(nav){const b=document.createElement('button');b.id='accountSettingsBtn';b.className='nav';b.type='button';b.innerHTML='<span class="navIcon">⚙</span><span>Settings</span>';b.onclick=e=>{e.preventDefault();e.stopPropagation();openSettings()};nav.appendChild(b)}
  const modal=document.createElement('div');modal.id='fmSettingsModal';modal.innerHTML=`<div id="fmSettingsCard"><h2>Account Settings</h2><div class="sub">Manage your FM Fantasy account.</div><div class="fmSetMeta"><div><small>Username</small><b id="fmSetUsername">—</b></div><div><small>Account type</small><b id="fmSetRole">—</b></div></div><div class="fmSetMeta"><div><small>Shared world</small><b id="fmSetWorld">—</b></div><div><small>Join code</small><b id="fmSetCode">—</b></div></div><div class="fmSetRow"><label>New password</label><input id="fmSetPassword" type="password" minlength="6" placeholder="At least 6 characters"></div><div class="fmSetActions"><button id="fmChangePassword" class="fmSetBtn">Change Password</button><button id="fmLogout" class="fmSetBtn dark">Log Out</button><button id="fmDeleteAccount" class="fmSetBtn danger">Delete Account</button><button id="fmCloseSettings" class="fmSetBtn dark">Close</button></div><div id="fmSetMsg" class="fmSetMsg"></div></div>`;document.body.appendChild(modal);
  document.getElementById('fmCloseSettings').onclick=()=>modal.classList.remove('show');modal.addEventListener('click',e=>{if(e.target===modal)modal.classList.remove('show')});
  document.getElementById('fmChangePassword').onclick=changePassword;document.getElementById('fmLogout').onclick=async()=>{await client.auth.signOut();location.reload()};document.getElementById('fmDeleteAccount').onclick=deleteAccount;
 }
 async function openSettings(){
  mountSettings();const p=window.FMCloud?.getProfile?.(),w=window.FMCloud?.getWorld?.();document.getElementById('fmSetUsername').textContent=p?.username||'—';document.getElementById('fmSetRole').textContent=p?.role==='creator'?'FPL Creator':'FPL User';document.getElementById('fmSetWorld').textContent=w?.name||'—';document.getElementById('fmSetCode').textContent=w?.join_code||'—';document.getElementById('fmSetPassword').value='';document.getElementById('fmSetMsg').textContent='';document.getElementById('fmSettingsModal').classList.add('show')
 }
 async function changePassword(){const input=document.getElementById('fmSetPassword'),msg=document.getElementById('fmSetMsg'),pw=input.value;if(pw.length<6){msg.textContent='Password must be at least 6 characters.';return}msg.textContent='Updating password…';const {error}=await client.auth.updateUser({password:pw});msg.textContent=error?error.message:'Password changed successfully.';if(!error)input.value=''}
 async function deleteAccount(){
  const p=window.FMCloud?.getProfile?.();if(!confirm(`Delete account ${p?.username||''}? This cannot be undone.`))return;if(!confirm('Final confirmation: permanently delete this FM Fantasy account?'))return;
  const msg=document.getElementById('fmSetMsg');msg.textContent='Deleting account…';const s=await session();if(!s){msg.textContent='Please log in again.';return}
  try{const r=await fetch(`${cfg.supabaseUrl}/functions/v1/fmfantasy-delete-account`,{method:'POST',headers:{'Content-Type':'application/json','apikey':cfg.supabaseAnonKey,'Authorization':`Bearer ${s.access_token}`},body:'{}'});const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||'Could not delete account.');localStorage.clear();location.reload()}catch(e){msg.textContent=e?.message||String(e)}
 }
 async function boot(){
  for(let i=0;i<80&&!window.FMCloud?.ready?.();i++)await sleep(250);mountSettings();fixTeamView();await syncNews();await syncLeagues();
  const b=document.getElementById('viewBanner');if(b)new MutationObserver(fixTeamView).observe(b,{attributes:true,attributeFilter:['class']});
  document.addEventListener('click',e=>{if(e.target.closest('[data-page="leagues"],#createLeague,#confirmCreateLeague,#joinLeague,[data-league],[data-view-manager],[data-leave]'))setTimeout(()=>syncLeagues(),500);if(e.target.closest('[data-page="news"]'))setTimeout(()=>syncNews(),150)});
  setInterval(()=>{if(document.getElementById('leaguesPage')?.classList.contains('active'))syncLeagues();if(document.getElementById('newsPage')?.classList.contains('active'))syncNews()},5000);
 }
 window.addEventListener('fmcloudready',()=>{syncNews();syncLeagues();mountSettings()});boot().catch(console.warn);
})();
