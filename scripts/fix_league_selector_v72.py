from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
marker='let FM_PENDING_SEASON_LEAGUE=null;'
if 'fmFantasySeasonLeaguePreferenceV72' not in html:
    if marker not in html: raise RuntimeError('pending league marker missing')
    inject="""let FM_PENDING_SEASON_LEAGUE=null;
const FM_LEAGUE_PREF_KEY='fmFantasySeasonLeaguePreferenceV72';
function fmNormaliseLeaguePreference(v){return v==='Premier League'||v==='EFL Championship'?v:null}
function fmRememberLeaguePreference(v){const p=fmNormaliseLeaguePreference(v);try{if(p)sessionStorage.setItem(FM_LEAGUE_PREF_KEY,p);else sessionStorage.removeItem(FM_LEAGUE_PREF_KEY)}catch(_){}return p}
function fmCurrentLeaguePreference(){const ui=fmNormaliseLeaguePreference($('leagueImportPreference')?.value);if(ui)return ui;const pending=fmNormaliseLeaguePreference(FM_PENDING_SEASON_LEAGUE);if(pending)return pending;try{return fmNormaliseLeaguePreference(sessionStorage.getItem(FM_LEAGUE_PREF_KEY))}catch(_){return null}}
try{const sel=$('leagueImportPreference'),saved=fmNormaliseLeaguePreference(sessionStorage.getItem(FM_LEAGUE_PREF_KEY));if(sel&&saved&&!sel.value)sel.value=saved;if(sel)sel.onchange=()=>{FM_PENDING_SEASON_LEAGUE=fmRememberLeaguePreference(sel.value)}}catch(_){}
"""
    html=html.replace(marker,inject,1)

old="(explicitPreference!==undefined?explicitPreference:(FM_PENDING_SEASON_LEAGUE!==null?FM_PENDING_SEASON_LEAGUE:($('leagueImportPreference')?.value||null)))"
new="(explicitPreference!==undefined?fmNormaliseLeaguePreference(explicitPreference):fmCurrentLeaguePreference())"
if old in html: html=html.replace(old,new,1)
elif new not in html: raise RuntimeError('preferredLeague expression missing')

oldcond="if(mode==='season'&&!autoRetry&&!($('leagueImportPreference')?.value)&&msg.includes('Multiple supported English league seasons')){"
newcond="const fmLeagueAmbiguity=/Multiple supported English league seasons|contains both supported English leagues/i.test(msg);if(mode==='season'&&!autoRetry&&!fmNormaliseLeaguePreference(explicitPreference)&&!fmCurrentLeaguePreference()&&fmLeagueAmbiguity){"
if oldcond in html: html=html.replace(oldcond,newcond,1)
elif newcond not in html: raise RuntimeError('ambiguity catch condition missing')

oldchosen="const chosen=isPrem?'Premier League':'EFL Championship';$('leagueImportPreference').value=chosen;"
newchosen="const chosen=isPrem?'Premier League':'EFL Championship';FM_PENDING_SEASON_LEAGUE=fmRememberLeaguePreference(chosen);$('leagueImportPreference').value=chosen;"
if oldchosen in html: html=html.replace(oldchosen,newchosen,1)
elif newchosen not in html: raise RuntimeError('prompt chosen marker missing')

oldbtn="$('seasonImportBtn').onclick=()=>{FM_PENDING_SEASON_LEAGUE=$('leagueImportPreference')?.value||null;$('seasonImportFile').click()};"
newbtn="$('seasonImportBtn').onclick=()=>{const ui=fmNormaliseLeaguePreference($('leagueImportPreference')?.value);if(ui)FM_PENDING_SEASON_LEAGUE=fmRememberLeaguePreference(ui);$('seasonImportFile').click()};"
if oldbtn in html: html=html.replace(oldbtn,newbtn,1)
elif newbtn not in html: raise RuntimeError('season import button handler missing')

# Runtime invariants for this regression.
for token in [
    "fmFantasySeasonLeaguePreferenceV72",
    "contains both supported English leagues",
    "fmLeagueAmbiguity",
    "fmCurrentLeaguePreference()",
    "FM_PENDING_SEASON_LEAGUE=fmRememberLeaguePreference(chosen)",
    "sendFMImport(file,mode,true,chosen)",
]:
    if token not in html: raise RuntimeError('missing V72 invariant '+token)
if oldcond in html: raise RuntimeError('old ambiguity-only catch remains')

repack(html)
assert reconstruct()==html
print('v72: auto ambiguity prompt restored and manual league choice is sticky through file selection')
