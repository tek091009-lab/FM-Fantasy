from __future__ import annotations
import base64,gzip,re,subprocess,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
PATCH_B64=(ROOT/'scripts/importer_v88.patch.gz.b64').read_text().strip()
OLD_SHA='6d65d399c7e8515b20d42f0f61db0c484eec0b10a5226dfe96a5209df7280fbd'
NEW_SHA='134c6984a8f2f476797ed3124132ffc69f5d1520ef649c596e5a1156018718f9'

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]+['']*len(PARTS)
    chunks=chunks[:len(PARTS)]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

def replace_once(s,old,new,label):
    if new in s:return s
    if old not in s:raise RuntimeError(label+' anchor missing')
    return s.replace(old,new,1)

html=reconstruct()
# Browser extracts only compact rgman competition cohorts; Python chooses the cohort structurally.
old="""    const candidates=items.filter(m=>{if(!(m.plain>0&&m.plain<=64000000))return false;const n=m.name.toLowerCase();return m.name==='news.dat'||m.name==='play_fixture_manager.dat'||n.endsWith('.scm')||n.endsWith('.apm')||n.endsWith('.pkm')||n.includes('match')||n.includes('fixture')||n.includes('history')||n.includes('form')||n.includes('stat')});const richNames=[],richProbe=[];
"""
new="""    const compRosterCandidates=items.filter(m=>m.group==='rgman'&&/^comp_\d+\.dat$/i.test(m.name)&&m.plain>=100000&&m.plain<=2000000);const compRosterNames=[];
    for(let i=0;i<compRosterCandidates.length;i++){const m=compRosterCandidates[i];let out=get(m);const idx=compRosterNames.length;compRosterNames.push(m.name);py.FS.writeFile('/tmp/comp_roster_'+idx+'.bin',out);out=null}py.FS.writeFile('/tmp/comp_roster_names.json',this.te.encode(JSON.stringify(compRosterNames)));
    const candidates=items.filter(m=>{if(!(m.plain>0&&m.plain<=64000000))return false;const n=m.name.toLowerCase();return m.name==='news.dat'||m.name==='play_fixture_manager.dat'||n.endsWith('.scm')||n.endsWith('.apm')||n.endsWith('.pkm')||n.includes('match')||n.includes('fixture')||n.includes('history')||n.includes('form')||n.includes('stat')});const richNames=[],richProbe=[];
"""
html=replace_once(html,old,new,'competition cohort extraction')
html=html.replace("payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation';","payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation + grounded-fixture retention-v86';",1)

oldcss=".drawerSectionIntro{margin-bottom:10px;padding:4px 2px 10px;border-bottom:1px solid rgba(255,255,255,.08)}.drawerSectionIntro b{display:block;font-size:15px}.drawerSectionIntro span{display:block;margin-top:3px;color:#9384a6;font-size:8px}.drawerMatch,.drawerFixture{display:grid;align-items:center;gap:9px;margin-bottom:8px;padding:11px;border:1px solid rgba(183,102,224,.16);border-radius:12px;background:linear-gradient(145deg,#241744,#171033);cursor:pointer}.drawerMatch{grid-template-columns:45px minmax(0,1fr) 40px}.drawerFixture{grid-template-columns:45px 28px minmax(0,1fr) 32px}.drawerMatch:hover,.drawerFixture:hover{border-color:rgba(232,88,218,.42);background:#2b194f}.drawerMatchGW{display:grid;place-items:center;min-height:34px;border-radius:8px;color:#dcb8f3;background:#391d61;font-size:8px;font-weight:900}.drawerMatch b,.drawerFixture b{display:block;font-size:9px}.drawerMatch span,.drawerFixture span{display:block;margin-top:3px;color:#a89ab7;font-size:7px}.drawerMatch small{display:block;margin-top:4px;color:#746883;font-size:6px}.drawerMatch>strong{color:#78f5c1;font-size:18px;text-align:center}.drawerMatch>strong small{margin:0;color:#8c7e9c}.drawerFixture .clubCrest{position:static!important;width:26px!important;height:26px!important}.drawerFixture>.fdr{min-width:28px}.drawerEmpty{padding:35px 10px;color:#9283a4;text-align:center}"
newcss=".drawerSectionIntro{margin-bottom:10px;padding:4px 2px 10px;border-bottom:1px solid rgba(255,255,255,.08)}.drawerSectionIntro b{display:block;font-size:15px}.drawerSectionIntro span{display:block;margin-top:4px;color:#a99ab8;font-size:10px;line-height:1.35}.drawerMatch,.drawerFixture{display:grid;align-items:center;gap:12px;margin-bottom:9px;padding:13px;border:1px solid rgba(183,102,224,.16);border-radius:12px;background:linear-gradient(145deg,#241744,#171033);cursor:pointer}.drawerMatch{grid-template-columns:54px minmax(0,1fr) 54px}.drawerFixture{grid-template-columns:48px 30px minmax(0,1fr) 34px}.drawerMatch:hover,.drawerFixture:hover{border-color:rgba(232,88,218,.42);background:#2b194f}.drawerMatchGW{display:grid;place-items:center;min-height:39px;border-radius:8px;color:#e7c9fa;background:#391d61;font-size:10px;font-weight:900}.drawerMatch b{display:block;font-size:12px;line-height:1.25}.drawerFixture b{display:block;font-size:10px}.drawerMatch span{display:block;margin-top:4px;color:#c1b4cb;font-size:10px;line-height:1.35}.drawerFixture span{display:block;margin-top:3px;color:#b0a2bc;font-size:8.5px}.drawerMatch small{display:block;margin-top:5px;color:#93869f;font-size:9px;line-height:1.4}.drawerMatch>strong{color:#78f5c1;font-size:24px;line-height:1;text-align:center}.drawerMatch>strong small{margin-top:4px;color:#9c8daa;font-size:9px}.drawerFixture .clubCrest{position:static!important;width:26px!important;height:26px!important}.drawerFixture>.fdr{min-width:28px}.drawerEmpty{padding:35px 10px;color:#9283a4;text-align:center}"
html=replace_once(html,oldcss,newcss,'recent matches readability')
oldf="""  const fs=SEASON_FIXTURES.filter(f=>f.home===p.club||f.away===p.club).filter(f=>Number(f.gameweek)>=Math.max(1,gw-2)).sort((a,b)=>Number(a.gameweek)-Number(b.gameweek)).slice(0,12);$('drawerBody').innerHTML=`<div class="drawerSectionIntro"><b>Fixtures</b><span>Difficulty and schedule from the imported Fantasy calendar.</span></div>${fs.map(f=>{const home=f.home===p.club,opp=home?f.away:f.home,d=difficulty(opp),mid=f.match_id?` data-open-match="${f.match_id}"`:'';const result=f.status==='played'?`${f.home_score}-${f.away_score}`:fixtureKickoffTime(f);return `<div class="drawerFixture"${mid}><div class="drawerMatchGW">GW ${f.gameweek}</div>${clubBadge(opp)}<div><b>${esc(opp)} (${home?'H':'A'})</b><span>${f.date?esc(f.date)+' · ':''}${result}</span></div><span class="fdr fdr${Math.max(2,d)}">${d}</span></div>`}).join('')||'<div class="drawerEmpty">No fixtures available.</div>'}`;
"""
newf="""  const currentGW=Math.max(1,Number(state.currentGameweek||META.current_gameweek||gw||1));const fs=SEASON_FIXTURES.filter(f=>(f.home===p.club||f.away===p.club)&&f.status!=='played').filter(f=>Number(f.gameweek)>=currentGW).sort((a,b)=>Number(a.gameweek)-Number(b.gameweek)||String(a.date||'').localeCompare(String(b.date||''))).slice(0,12);$('drawerBody').innerHTML=`<div class="drawerSectionIntro"><b>Fixtures</b><span>Upcoming fixtures only · difficulty and schedule from the imported Fantasy calendar.</span></div>${fs.map(f=>{const home=f.home===p.club,opp=home?f.away:f.home,d=difficulty(opp);const result=fixtureKickoffTime(f);return `<div class="drawerFixture"><div class="drawerMatchGW">GW ${f.gameweek}</div>${clubBadge(opp)}<div><b>${esc(opp)} (${home?'H':'A'})</b><span>${f.date?esc(f.date)+' · ':''}${result}</span></div><span class="fdr fdr${Math.max(2,d)}">${d}</span></div>`}).join('')||'<div class="drawerEmpty">No upcoming fixtures available.</div>'}`;
"""
html=replace_once(html,oldf,newf,'future-only player fixtures')
oldme="""function matchEvents(m){const all=[...m.home_players,...m.away_players].filter(x=>x.minutes>0);return{goals:all.filter(x=>x.goals).map(x=>`${x.name} ×${x.goals}`),assists:all.filter(x=>x.assists).map(x=>`${x.name} ×${x.assists}`),cards:all.filter(x=>(x.yc??x.yellow_cards)||(x.rc??x.red_cards)).map(x=>{const yc=(x.yc??x.yellow_cards??0),rc=(x.rc??x.red_cards??0);return `${x.name}${yc?` · ${yc} YC`:''}${rc?` · ${rc} RC`:''}`}),saves:all.filter(x=>x.pos==='GK').map(x=>`${x.name} · ${x.saves} saves`),defcon:all.filter(x=>x.pos!=='GK').map(x=>`${x.name} · ${x.defcon_actions??'—'}`),bonus:all.filter(x=>x.bonus).sort((a,b)=>b.bonus-a.bonus).map(x=>`${x.name} · ${x.bonus} bonus · ${x.bps_proxy} BPS proxy`)}}
"""
newme="""function matchEvents(m){const all=[...(m.home_players||[]).map(x=>({...x,__club:m.home})),...(m.away_players||[]).map(x=>({...x,__club:m.away}))].filter(x=>Number(x.minutes||0)>0),label=x=>{const id=String(x.player_id??x.pid??x.id??''),p=PLAYERS.find(q=>String(q.pid??q.id??'')===id);return `${p?playerName(p):String(x.name||'Unknown')} (${clubCode(x.__club)})`};return{goals:all.filter(x=>x.goals).map(x=>`${label(x)} ×${x.goals}`),assists:all.filter(x=>x.assists).map(x=>`${label(x)} ×${x.assists}`),cards:all.filter(x=>(x.yc??x.yellow_cards)||(x.rc??x.red_cards)).map(x=>{const yc=(x.yc??x.yellow_cards??0),rc=(x.rc??x.red_cards??0);return `${label(x)}${yc?` · ${yc} YC`:''}${rc?` · ${rc} RC`:''}`}),saves:all.filter(x=>x.pos==='GK').sort((a,b)=>Number(b.saves||0)-Number(a.saves||0)).map(x=>`${label(x)} · ${x.saves} saves`),defcon:all.filter(x=>x.pos!=='GK').sort((a,b)=>Number(b.defcon_actions??-1)-Number(a.defcon_actions??-1)).map(x=>`${label(x)} · ${x.defcon_actions??'—'}`),bonus:all.filter(x=>x.bonus).sort((a,b)=>Number(b.bonus||0)-Number(a.bonus||0)||Number(b.bps_proxy||0)-Number(a.bps_proxy||0)).map(x=>`${label(x)} · ${x.bonus} bonus · ${x.bps_proxy} BPS proxy`)}}
"""
html=replace_once(html,oldme,newme,'fixture event canonical names')

m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')
required=['current-competition-cohort-v86','grounded_fixture_id','observed_midfield_usage_v64_lineup_slot','stable_fixture_key']
if not all(t in py for t in required):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); imp=td/'importer.py'; pat=td/'importer.patch';imp.write_text(py);pat.write_bytes(gzip.decompress(base64.b64decode(PATCH_B64)))
        r=subprocess.run(['patch','-N','-p0','-i',str(pat)],cwd=td,text=True,capture_output=True)
        py2=imp.read_text()
        if not all(t in py2 for t in required):
            raise RuntimeError('importer v88 patch failed: '+r.stdout+' '+r.stderr)
        py=py2
compile(py,'fm_importer_v88.py','exec')
newb64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+newb64+html[m.end(1):]
repack(html)

if not (ROOT/'importmodelv86.js').exists():raise RuntimeError('importmodelv86.js missing')
idx=ROOT/'index.html'; text=idx.read_text()
needle='<script src="./disciplineguardv86post.js?v=1"><\/script>'
insert=needle+'<script src="./importmodelv86.js?v=1"><\/script>'
if 'importmodelv86.js?v=1' not in text:
    if needle not in text:raise RuntimeError('index discipline post anchor missing')
    text=text.replace(needle,insert,1);idx.write_text(text)

# Final assertions catch any partial/no-op upgrade.
chk=reconstruct(); mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
p2=base64.b64decode(mm.group(1)).decode();compile(p2,'verified_v88.py','exec')
for t in required:assert t in p2,t
for t in ['compRosterCandidates','Upcoming fixtures only','const all=[...(m.home_players||[]).map','.drawerMatch>strong{color:#78f5c1;font-size:24px']:
    assert t in chk,t
assert 'importmodelv86.js?v=1' in idx.read_text()
print('v88 importer/UI/GK pricing upgrade applied')
