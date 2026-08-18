(()=>{
'use strict';
const VERSION='fixture-continuity-v89-stable-id-migration';
const arr=v=>Array.isArray(v)?v:[];
const norm=v=>String(v??'').trim().toLowerCase().replace(/\s+/g,' ');
const id=v=>String(v??'').trim();
const season=p=>String(p?.meta?.season_start??p?.meta?.season??'').trim();
const competition=p=>norm(p?.meta?.competition_code||p?.meta?.competition||'');
function sameWorld(a,b){
 if(!a||!b)return false;
 const ca=competition(a),cb=competition(b);if(ca&&cb&&ca!==cb)return false;
 const sa=season(a),sb=season(b);if(sa&&sb&&sa!==sb)return false;
 return !!(ca||sa);
}
function teamId(f,side){return id(f?.[side+'_tid']??f?.[side+'_team_id']??f?.[side+'_id']);}
function teamName(f,side){return norm(f?.[side]??f?.[side+'_team']??f?.[side+'_name']);}
function pairKey(f){
 const ht=teamId(f,'home'),at=teamId(f,'away');
 if(ht&&at)return `tid:${ht}>${at}`;
 const hn=teamName(f,'home'),an=teamName(f,'away');
 if(hn&&an)return `name:${hn}>${an}`;
 return '';
}
function fixtureId(f){return id(f?.fixture_id??f?.id);}
function uniqueByPair(fixtures){
 const m=new Map();
 for(const f of arr(fixtures)){const k=pairKey(f);if(!k)continue;if(!m.has(k))m.set(k,[]);m.get(k).push(f)}
 return m;
}
function reconcile(payload,oldPayload){
 const out={version:VERSION,policy:'same-season ordered-team-pair migration; unique pairs only; no date/GW guessing',same_world:false,old_fixtures:0,new_fixtures:0,unique_pairs_compared:0,fixture_id_aliases_created:0,match_references_rewritten:0,ambiguous_pairs_preserved:0,unmatched_pairs:0};
 if(!sameWorld(payload,oldPayload))return out;
 out.same_world=true;
 const oldF=arr(oldPayload?.fixtures),newF=arr(payload?.fixtures);out.old_fixtures=oldF.length;out.new_fixtures=newF.length;
 const om=uniqueByPair(oldF),nm=uniqueByPair(newF),aliases={},newIdByOld=new Map(),newByPair=new Map();
 for(const [k,rows] of nm)if(rows.length===1)newByPair.set(k,rows[0]);
 for(const [k,orows] of om){
  const nrows=nm.get(k)||[];
  if(orows.length!==1||nrows.length!==1){if(nrows.length)out.ambiguous_pairs_preserved++;else out.unmatched_pairs++;continue}
  out.unique_pairs_compared++;
  const of=orows[0],nf=nrows[0],oid=fixtureId(of),nid=fixtureId(nf);
  if(!oid||!nid||oid===nid)continue;
  aliases[oid]=nid;newIdByOld.set(oid,nid);out.fixture_id_aliases_created++;
  const legacy=new Set(arr(nf.legacy_fixture_ids).map(String));legacy.add(oid);nf.legacy_fixture_ids=[...legacy];
 }
 // Only rewrite an incoming rich-match reference when the match's own ordered
 // teams point to the same uniquely-mapped fixture. This prevents an old ID from
 // being globally reassigned if a schema reused IDs in another context.
 for(const m of arr(payload?.matches)){
  const oid=fixtureId(m),nid=newIdByOld.get(oid);if(!nid)continue;
  const k=pairKey(m),nf=k?newByPair.get(k):null;if(!nf||fixtureId(nf)!==nid)continue;
  m.legacy_fixture_id=oid;m.fixture_id=nid;out.match_references_rewritten++;
 }
 payload.meta=payload.meta||{};
 payload.meta.fixture_identity_continuity_v89={...out,aliases};
 payload.meta.fixture_id_aliases={...(payload.meta.fixture_id_aliases||{}),...aliases};
 return payload.meta.fixture_identity_continuity_v89;
}
function install(){
 const c=window.FMCloud;if(!c||c.__fixtureContinuityV89||typeof c.publishWorld!=='function')return false;
 c.__fixtureContinuityV89=true;const original=c.publishWorld.bind(c);
 c.publishWorld=async(payload,...args)=>{
  if(payload){const old=c.getWorld?.()?.payload||null;try{reconcile(payload,old)}catch(e){console.warn('Fixture continuity v89 evidence failed safely',e)}}
  return original(payload,...args);
 };
 return true;
}
window.FMFixtureContinuityV89={version:VERSION,reconcile,pairKey,sameWorld};
window.addEventListener('fmcloudready',install);let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer)},200);
})();
