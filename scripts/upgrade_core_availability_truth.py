from pathlib import Path
import base64,gzip

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')

susp=html.find('function fmInferActiveSuspensions(payload){')
helper=html.find('function fmAvailabilityTruthDate(payload){')
start=helper if helper>=0 and (susp<0 or helper<susp) else susp
end=html.find('function fmBuildInitialNews(payload){',max(start,0)+1)
if start<0 or end<=start: raise SystemExit('core availability function boundary missing')

strict=r'''function fmAvailabilityTruthDate(payload){return String(payload?.meta?.availability_reference_date||payload?.meta?.availability_save_date||'')}
function fmAvailabilityTruthStale(payload){const v=payload?.meta?.availability_data_stale;return v===true||String(v).toLowerCase()==='true'}
function fmInferActiveSuspensions(payload){
 const out=[];if(fmAvailabilityTruthStale(payload))return out;const ref=fmAvailabilityTruthDate(payload);
 for(const p of payload?.players||[]){
  const ev=p?.suspension_evidence_structural||{};if(String(ev.source||'')!=='discipline.dat/active-ban-v1')continue;
  const remaining=Math.max(Number(p.suspension_remaining||0),Number(p.suspension_games_remaining||0),Number(p.ban_games_remaining||0),Number(ev.games_remaining||0));
  const until=String(ev.expiry||p.banned_until||p.suspension_until||'');if(remaining<=0||!until||(ref&&until<=ref))continue;
  out.push({pid:String(p.pid),name:playerName(p),club:p.club,pos:p.pos,detail:`Suspended · ${remaining} league match${remaining===1?'':'es'} remaining · until ${fmFmtStatusDate(until)}`});
 }
 return out
}
function fmInferActiveInjuries(payload){
 const out=[];if(fmAvailabilityTruthStale(payload))return out;const ref=fmAvailabilityTruthDate(payload);
 for(const p of payload?.players||[]){
  const ev=p?.injury_evidence||{},src=String(ev.source||'');if(!src.startsWith('injury_manager.dat/current-window'))continue;
  const back=String(p.injury_return_date||p.expected_return_date||p.injury_expected_back||p.injury_end_date||ev.expected_return||'');
  const days=Number(ev.days_remaining??p.injury_days_remaining??0);if(back&&ref&&back<=ref)continue;if(!back&&days<=0)continue;
  out.push({pid:String(p.pid),name:playerName(p),club:p.club,pos:p.pos,detail:`Injured${back?` · expected back ${fmFmtStatusDate(back)}`:''}`});
 }
 return out
}
'''
html=html[:start]+strict+html[end:]
block=html[html.find('function fmAvailabilityTruthDate'):html.find('function fmBuildInitialNews(payload){')]
for token in ['fmAvailabilityTruthStale','discipline.dat/active-ban-v1','injury_manager.dat/current-window']:
    if token not in block: raise SystemExit('missing '+token)
for forbidden in ['5 yellow cards','second-yellow red','fmClubPlayedAfter(payload,p.club,inc.date)']:
    if forbidden in block: raise SystemExit('heuristic suspension inference still present: '+forbidden)
for declaration in ['function fmAvailabilityTruthDate(payload){','function fmAvailabilityTruthStale(payload){','function fmInferActiveSuspensions(payload){','function fmInferActiveInjuries(payload){']:
    if html.count(declaration)!=1: raise SystemExit(f'expected exactly one {declaration}, got {html.count(declaration)}')

out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out: raise SystemExit('repack mismatch')
print('core direct-evidence availability truth applied idempotently')
