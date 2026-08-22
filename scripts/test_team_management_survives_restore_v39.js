const fs=require('fs');
const vm=require('vm');
function must(x,msg){if(!x)throw new Error(msg)}
const code=fs.readFileSync('managerauthoritative.js','utf8');
const authority=fs.readFileSync('managerstateauthorityv1.js','utf8');
const clone=x=>JSON.parse(JSON.stringify(x));

const squad=Array.from({length:15},(_,i)=>String(i+1));
function remoteBase(){return {
  squad:[...squad],lockedSquad:[...squad],
  starters:squad.slice(0,11),bench:squad.slice(11),captain:'1',vice:'2',
  bank:5,lockedBank:5,teamConfirmed:true,currentGameweek:6,completedGameweek:5,
  pointsHistory:[{gw:5,net:30}],totalPoints:30,freeTransfers:1,lastTransferRollGW:5,
  teamName:'HMS PISS THE LEAGUE',managerName:'Thomas Kelleher',chips:{},__stamp:'a'
}}
function contextFor(local,remote,serverSnapshot=null){
  const supabase={createClient:()=>({
    auth:{getSession:async()=>({data:{session:{user:{id:'u'}}}})},
    from:()=>({select:()=>({eq:()=>({eq:()=>({maybeSingle:async()=>({data:{state:remote,updated_at:String(remote.__stamp)},error:null})})})})})
  })};
  const ctx={console,JSON,Object,Array,Promise,Set,
    setTimeout:(fn)=>{fn();return 1},requestAnimationFrame:fn=>fn(),
    document:{addEventListener(){},visibilityState:'visible'},supabase,
    window:{FM_FANTASY_CONFIG:{supabaseUrl:'x',supabaseAnonKey:'y'},supabase,
      FMCloud:{ready:()=>true,getWorld:()=>({id:'w'}),normaliseManagerState:x=>x,managerState:serverSnapshot?clone(serverSnapshot):null},addEventListener(){}},
    DEFAULT:{squad:[],lockedSquad:[],starters:[],bench:[],bank:100,lockedBank:100,chips:{}},state:local,
    renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},renderNews(){},renderLeagues(){}};
  ctx.window.window=ctx.window;ctx.window.state=ctx.state;
  vm.createContext(ctx);vm.runInContext(code,ctx);return ctx;
}

(async()=>{
  const remote=remoteBase();
  const c=contextFor({squad:[],lockedSquad:[],starters:[],bench:[],bank:100,lockedBank:100,chips:{}},remote,null);
  await c.window.fmRestoreManagerFromCloud();
  must(c.state.captain==='1'&&c.state.vice==='2','confirmed manager did not hydrate cleanly');
  must(!c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'clean confirmed team falsely marked dirty');

  // Captain + vice must survive repeated stale authoritative reads immediately.
  c.state.captain='3';c.state.vice='4';
  must(c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'captain/vice edit not detected as pending manager draft');
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.captain==='3'&&c.state.vice==='4','stale restore erased captain/vice selection');
  must(c.state.freeTransfers===1&&c.state.totalPoints===30,'draft preservation changed server-authoritative progress');

  // Server catches up: that exact selection becomes the new clean baseline.
  remote.captain='3';remote.vice='4';remote.__stamp='b';
  await c.window.fmRestoreManagerFromCloud();
  must(!c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'saved captain/vice remained falsely dirty after server catch-up');

  // XI/bench swap must also survive on the first attempt.
  c.state.starters=squad.slice(0,10).concat('12');
  c.state.bench=['11','13','14','15'];
  must(c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'XI/bench swap not detected');
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.starters.includes('12')&&!c.state.starters.includes('11'),'stale restore reversed starter/bench swap');
  must(c.state.bench.join('|')==='11|13|14|15','stale restore reversed bench after lineup swap');

  remote.starters=[...c.state.starters];remote.bench=[...c.state.bench];remote.__stamp='c';
  await c.window.fmRestoreManagerFromCloud();
  must(!c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'saved XI/bench swap stayed falsely dirty');

  // Bench order alone is meaningful and must not get flattened by set comparison.
  c.state.bench=['13','11','14','15'];
  must(c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'bench-order-only edit not detected');
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.bench.join('|')==='13|11|14|15','bench order was erased by stale restore');

  remote.bench=[...c.state.bench];remote.__stamp='d';
  await c.window.fmRestoreManagerFromCloud();
  must(!c.window.FMManagerAuthoritative.hasConfirmedTeamManagementDraft(c.state),'saved bench order stayed falsely dirty');

  // A real server-side change while the browser is clean must still win.
  remote.captain='5';remote.vice='6';remote.__stamp='e';
  await c.window.fmRestoreManagerFromCloud();
  must(c.state.captain==='5'&&c.state.vice==='6','clean browser blocked a genuine server captain/vice change');

  // The progress guard must keep FMCloud.managerState as the pure server snapshot;
  // otherwise a scoring refresh can accidentally erase the draft protection baseline.
  must(authority.includes("manager-state-authority-v2-pure-server-draft-baseline"),'pure server baseline guard version missing');
  must(authority.includes('FMCloud.managerState=clone(serverSnapshot||merged)'),'progress merge can contaminate manager draft baseline');
  must(authority.includes('applyProgressToLive(merged,remote)'),'queue guard is not passing the pure server snapshot');

  console.log('PASS captain, vice-captain, XI/bench and bench-order edits survive stale manager restores first time');
})().catch(e=>{console.error(e);process.exit(1)});
