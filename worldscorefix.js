(()=>{
 const cfg=window.FM_FANTASY_CONFIG||{};
 if(!window.supabase||!cfg.supabaseUrl||!cfg.supabaseAnonKey)return;
 const client=supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
 let busy=false,lastSig='';
 const clone=v=>JSON.parse(JSON.stringify(v||{}));
 const num=v=>Number(v||0)||0;
 const has=(o,k)=>Object.prototype.hasOwnProperty.call(o||{},String(k));
 const chip=v=>String(v||'').toLowerCase().replace(/[^a-z]/g,'');

 function pmap(payload){return new Map((payload?.players||[]).map(p=>[String(p.pid),p]));}
 function pts(map,id,gw){return num(map.get(String(id))?.weekly_points?.[String(gw)]);}
 function appeared(map,id,gw){const p=map.get(String(id));return !!p&&has(p.weekly_points||{},gw);}
 function pos(map,id){return String(map.get(String(id))?.pos||'');}
 function formation(map,ids){const c={GK:0,DEF:0,MID:0,FWD:0};for(const id of ids){const k=pos(map,id);if(k in c)c[k]++}return c;}
 function valid(c){return c.GK===1&&c.DEF>=3&&c.DEF<=5&&c.MID>=2&&c.MID<=5&&c.FWD>=1&&c.FWD<=3;}
 function fixtureGw(f){return num(f?.gameweek??f?.gw??f?.round_gameweek);}
 function fixturePlayed(f){return String(f?.status||'').toLowerCase()==='played'||(f?.home_score!==null&&f?.home_score!==undefined&&f?.away_score!==null&&f?.away_score!==undefined);}
 function resolvedCompletedGameweek(payload){
   const meta=payload?.meta||{};
   let done=num(meta.completed_gameweek),latest=Math.max(done,num(meta.latest_gameweek_with_result));
   if(latest<=done)return done;
   const fixtures=Array.isArray(payload?.fixtures)?payload.fixtures:[];
   for(let gw=done+1;gw<=latest;gw++){
     const rows=fixtures.filter(f=>fixtureGw(f)===gw);
     // A calendar Gameweek with no league fixtures is a valid blank Fantasy GW:
     // close it on zero points and continue to the next real scoring Gameweek.
     if(!rows.length){done=gw;continue}
     if(rows.every(fixturePlayed)){done=gw;continue}
     break;
   }
   return done;
 }
 function normaliseWorldProgress(payload,target){
   if(!payload?.meta||!target)return;
   const old=num(payload.meta.completed_gameweek);
   if(target<=old)return;
   payload.meta.completed_gameweek=target;
   payload.meta.current_gameweek=target+1;
   payload.meta.next_gameweek=target+1;
   payload.meta.blank_gameweek_progression_fixed=true;
   try{
     if(typeof META!=='undefined'&&META){META.completed_gameweek=target;META.current_gameweek=target+1;META.next_gameweek=target+1}
   }catch(_e){}
 }
 function doneGw(st){const entry=Math.max(1,num(st.entryGameweek)||1),h=Array.isArray(st.pointsHistory)?st.pointsHistory:[];return h.length?Math.max(entry-1,...h.map(x=>num(x?.gw))):entry-1;}
 function previousLineup(st,gw){
   const gl=st.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{};
   const ks=Object.keys(gl).map(Number).filter(n=>Number.isFinite(n)&&n<gw).sort((a,b)=>b-a);
   if(ks.length)return clone(gl[String(ks[0])]||gl[ks[0]]);
   const h=(Array.isArray(st.pointsHistory)?st.pointsHistory:[]).filter(x=>num(x?.gw)<gw&&Array.isArray(x?.starters)).sort((a,b)=>num(b.gw)-num(a.gw));
   return h.length?clone(h[0]):null;
 }
 function lineupFor(st,gw){
   const gl=st.gameweekLineups&&typeof st.gameweekLineups==='object'&&!Array.isArray(st.gameweekLineups)?st.gameweekLineups:{};
   const exact=gl[String(gw)]||gl[gw];
   if(exact&&Array.isArray(exact.starters)&&exact.starters.length===11)return clone(exact);
   if(Array.isArray(st.starters)&&st.starters.length===11)return {gw:Number(gw),squad:[...(st.squad||st.lockedSquad||[])],starters:[...st.starters],bench:[...(st.bench||[])],captain:st.captain||null,vice:st.vice||null,chip:st.activeChip||null,hit:num(st.transferHitThisGW)};
   const prior=previousLineup(st,gw);if(prior){prior.gw=Number(gw);return prior}
   return null;
 }
 function applyAutosubs(map,lineup,gw){
   const start=[...(lineup.starters||[])].map(String),bench=[...(lineup.bench||[])].map(String);
   const effective=start.filter(id=>appeared(map,id,gw)),missing=start.filter(id=>!appeared(map,id,gw));
   const autosubs=[];
   const gkOut=missing.find(id=>pos(map,id)==='GK');
   if(gkOut){const gkIn=bench.find(id=>pos(map,id)==='GK'&&appeared(map,id,gw));if(gkIn){effective.push(gkIn);autosubs.push({in:gkIn,out:gkOut,reason:'No appearance'});missing.splice(missing.indexOf(gkOut),1)}}
   for(const b of bench){
     if(pos(map,b)==='GK'||!appeared(map,b,gw)||autosubs.some(x=>x.in===b))continue;
     let picked=-1;
     for(let i=0;i<missing.length;i++){
       if(pos(map,missing[i])==='GK')continue;
       const candidate=[...effective,b];
       if(valid(formation(map,candidate))){picked=i;break}
     }
     if(picked>=0){const out=missing.splice(picked,1)[0];effective.push(b);autosubs.push({in:b,out,reason:'No appearance'})}
   }
   return {effective,autosubs};
 }
 function score(map,lineup,gw){
   const starters=[...(lineup.starters||[])].map(String),bench=[...(lineup.bench||[])].map(String),squad=[...(lineup.squad||[])].map(String);
   if(starters.length!==11)return null;
   const ch=chip(lineup.chip),benchBoost=ch.includes('benchboost'),triple=ch.includes('triplecaptain');
   let effective,autosubs;
   if(benchBoost){effective=[...starters,...bench];autosubs=[]}else({effective,autosubs}=applyAutosubs(map,lineup,gw));
   let captainApplied=null,captainMultiplier=1;
   const cap=String(lineup.captain||''),vice=String(lineup.vice||'');
   if(cap&&appeared(map,cap,gw)){captainApplied=cap;captainMultiplier=triple?3:2}
   else if(vice&&appeared(map,vice,gw)){captainApplied=vice;captainMultiplier=triple?3:2}
   const contributions={};for(const id of new Set([...squad,...starters,...bench]))contributions[String(id)]=0;
   let gross=0;
   for(const id of effective){const v=pts(map,id,gw);gross+=v;contributions[id]=(contributions[id]||0)+v}
   let captainRaw=0,captainBonus=0;
   if(captainApplied){captainRaw=pts(map,captainApplied,gw);captainBonus=captainRaw*(captainMultiplier-1);gross+=captainBonus;contributions[captainApplied]=(contributions[captainApplied]||0)+captainBonus}
   const hit=num(lineup.hit),net=gross-hit;
   return {gw:Number(gw),hit,net,chip:lineup.chip||null,vice:lineup.vice||null,bench,squad,captain:lineup.captain||null,starters,gross,autosubs,captainRaw,provisional:false,captainBonus,captainApplied,captainMultiplier,effectiveStarters:effective,playerContributions:contributions};
 }
 function applyResult(st,lineup,result,gw){
   if(!Array.isArray(st.pointsHistory))st.pointsHistory=[];
   st.pointsHistory=st.pointsHistory.filter(x=>num(x?.gw)!==gw);st.pointsHistory.push(result);st.pointsHistory.sort((a,b)=>num(a.gw)-num(b.gw));
   if(!st.gameweekLineups||typeof st.gameweekLineups!=='object'||Array.isArray(st.gameweekLineups))st.gameweekLineups={};
   st.gameweekLineups[String(gw)]={gw:Number(gw),squad:[...(lineup.squad||[])],starters:[...(lineup.starters||[])],bench:[...(lineup.bench||[])],captain:lineup.captain||null,vice:lineup.vice||null,chip:lineup.chip||null,hit:num(lineup.hit)};
   st.totalPoints=st.pointsHistory.reduce((n,x)=>n+num(x?.net??x?.gross),0);st.completedGameweek=gw;st.currentGameweek=gw+1;st.firstGameweekPlayed=true;
   if(num(st.lastTransferRollGW)<gw){st.freeTransfers=Math.min(5,Math.max(0,num(st.freeTransfers))+1);st.lastTransferRollGW=gw}
   st.transferHitThisGW=0;st.activeChip=null;
 }
 async function finaliseAll(force=false){
   try{
     if(busy||!window.FMCloud?.ready?.()||!window.FMCloud?.isCreator?.())return false;busy=true;
     const world=window.FMCloud.getWorld?.();if(!world?.id)return false;
     let payload=world.payload;if(force||!payload?.players)payload=await window.FMCloud.loadWorld?.();if(!payload?.players)return false;
     const target=resolvedCompletedGameweek(payload);if(!target)return false;
     normaliseWorldProgress(payload,target);
     const sig=`${world.id}|${target}|${world.updated_at||''}`;if(!force&&sig===lastSig)return true;
     const {data:rows,error}=await client.from('manager_states').select('user_id,state').eq('world_id',world.id);if(error)throw error;
     const map=pmap(payload);let changed=0;
     for(const row of rows||[]){
       const st=clone(row.state);if(!st.teamConfirmed)continue;
       const entry=Math.max(1,num(st.entryGameweek)||1);let done=doneGw(st);
       for(let gw=Math.max(entry,done+1);gw<=target;gw++){
         const lineup=lineupFor(st,gw);if(!lineup)break;
         const result=score(map,lineup,gw);if(!result)break;
         applyResult(st,lineup,result,gw);done=gw;
       }
       if(done>doneGw(row.state||{})){
         const {error:saveErr}=await client.rpc('fmfantasy_creator_save_manager_state',{p_world_id:world.id,p_user_id:row.user_id,p_state:st});if(saveErr)throw saveErr;changed++;
       }
     }
     lastSig=sig;
     if(changed){window.dispatchEvent(new CustomEvent('fmworldmanagersscored',{detail:{gameweek:target,managers:changed}}));setTimeout(()=>{if(typeof renderAll==='function')renderAll();if(typeof renderLeagues==='function')renderLeagues()},150)}
     return true;
   }catch(e){console.warn('Creator-wide manager scoring failed',e);return false}finally{busy=false}
 }
 window.fmCreatorFinaliseWorldManagers=()=>finaliseAll(true);
 window.addEventListener('fmcloudready',()=>setTimeout(()=>finaliseAll(false),900));
 window.addEventListener('focus',()=>setTimeout(()=>finaliseAll(false),300));
 window.addEventListener('fmmanagerprogressfinalised',()=>setTimeout(()=>finaliseAll(false),100));
 setInterval(()=>finaliseAll(false),5000);
})();
