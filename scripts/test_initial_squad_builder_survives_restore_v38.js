const fs=require('fs');
const vm=require('vm');
function must(x,msg){if(!x)throw new Error(msg)}
const code=fs.readFileSync('managerauthoritative.js','utf8');
const clone=x=>JSON.parse(JSON.stringify(x));

function baseRemote(squad=[]){return {
  squad:[...squad],lockedSquad:[],starters:[],bench:[],captain:null,vice:null,
  bank:100-squad.length*6,lockedBank:100-squad.length*6,teamConfirmed:false,
  currentGameweek:5,completedGameweek:4,pointsHistory:[],totalPoints:0,
  freeTransfers:1,lastTransferRollGW:4,teamName:'HMS PISS THE LEAGUE',managerName:'Thomas Kelleher',chips:{},__stamp:'a'
}}
function contextFor(local,remote,serverSnapshot=null){
  const supabase={createClient:()=>({
    auth:{getSession:async()=>({data:{session:{user:{id:'u'}}}})},
    from:()=>({select:()=>({eq:()=>({eq:()=>({maybeSingle:async()=>({data:{state:remote,updated_at:String(remote.__stamp)},error:null})})})})})
  })};
  const ctx={console,JSON,Object,Array,Promise,setTimeout:(fn)=>{fn();return 1},requestAnimationFrame:fn=>fn(),
    document:{addEventListener(){},visibilityState:'visible'},supabase,
    window:{FM_FANTASY_CONFIG:{supabaseUrl:'x',supabaseAnonKey:'y'},supabase,
      FMCloud:{ready:()=>true,getWorld:()=>({id:'w'}),normaliseManagerState:x=>x,managerState:serverSnapshot?clone(serverSnapshot):null},addEventListener(){}},
    DEFAULT:{squad:[],lockedSquad:[],starters:[],bench:[],bank:100,lockedBank:100,chips:{}},state:local,
    renderTransferPitch(){},renderTransferSummary(){},renderMarket(){},renderTeam(){},renderSidebar(){},renderNews(){},renderLeagues(){}};
  ctx.window.window=ctx.window;ctx.window.state=ctx.state;vm.createContext(ctx);vm.runInContext(code,ctx);return ctx;
}

(async()=>{
  // First page hydrate: empty browser must accept the nine-player server draft.
  const remote=baseRemote(['1','2','3','4','5','6','7','8','9']);
  const empty=baseRemote([]);empty.bank=100;
  const c=contextFor(empty,remote,null);
  await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.length===9,'initial remote squad did not hydrate into empty browser');
  must(!c.window.FMManagerAuthoritative.hasInitialSquadDraft(c.state),'server-hydrated squad falsely marked dirty');

  // User clicks player 10 while delayed server restores still return the nine-player snapshot.
  c.state.squad.push('10');c.state.bank=40;
  must(c.window.FMManagerAuthoritative.hasInitialSquadDraft(c.state),'10th-player local edit not detected');
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.join('|')==='1|2|3|4|5|6|7|8|9|10','repeated stale manager restores erased the 10th player');
  must(Number(c.state.bank)===40,'repeated stale manager restores erased builder bank');

  // Server catches up to the saved 10-player draft; it becomes the new clean baseline.
  remote.squad=['1','2','3','4','5','6','7','8','9','10'];remote.bank=40;remote.lockedBank=40;remote.__stamp='b';
  await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.length===10,'server catch-up changed the current draft');
  must(!c.window.FMManagerAuthoritative.hasInitialSquadDraft(c.state),'caught-up server draft stayed falsely dirty');

  // The very next click must also survive immediately — no "add it three times" behaviour.
  c.state.squad.push('11');c.state.bank=34;
  await c.window.fmRestoreManagerFromCloud();await c.window.fmRestoreManagerFromCloud();
  must(c.state.squad.at(-1)==='11'&&c.state.squad.length===11,'next player click was erased before server save caught up');
  must(Number(c.state.bank)===34,'next player bank edit was erased');
  must(c.state.teamConfirmed===false,'initial squad draft was incorrectly confirmed');
  must((c.state.lockedSquad||[]).length===0,'initial squad builder fabricated a locked baseline');
  console.log('PASS initial squad additions survive repeated stale manager restores on the first click');
})().catch(e=>{console.error(e);process.exit(1)});
