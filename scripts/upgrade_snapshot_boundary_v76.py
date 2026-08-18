from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
def reconstruct(): return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode();step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))];chunks+=['']*(len(PARTS)-len(chunks));assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')
html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode()
fn='def browser_build_payload_from_fs('
start=py.find(fn)
if start<0:raise RuntimeError('browser_build_payload_from_fs missing')
head=py[:start];browser=py[start:]
anchor="availability_diag=_structural_availability_from_fs(players,fixtures)"
block="""availability_diag=_structural_availability_from_fs(players,fixtures)\n    # V76: every accepted browser import carries a dated historical boundary.  This is\n    # a data cutoff, never the browser clock.  Supabase freezes accepted history behind\n    # the previous boundary while current-state fields continue to refresh.\n    snapshot_date=availability_diag.get('save_date')\n    snapshot_date_source='structural_save_or_fixture_floor_v1' if snapshot_date else None\n    if not snapshot_date:\n        played_dates=[]\n        for _f in fixtures:\n            if _f.get('status')!='played' or not _f.get('date'):continue\n            try:played_dates.append(dt.date.fromisoformat(str(_f['date'])[:10]))\n            except Exception:pass\n        if played_dates:\n            snapshot_date=max(played_dates).isoformat();snapshot_date_source='latest_played_league_fixture'\n    if not snapshot_date:snapshot_date_source='preseason_undated'\n"""
if 'historical_freeze_policy' not in browser:
    if browser.count(anchor)!=1:raise RuntimeError(f'expected one browser availability anchor, got {browser.count(anchor)}')
    browser=browser.replace(anchor,block,1)
    meta_anchor="'availability_decoder':'structural-v1',"
    meta_insert="'snapshot_date':snapshot_date,'snapshot_date_source':snapshot_date_source,'snapshot_date_semantics':'FM data boundary; not browser time','historical_freeze_policy':'append-only-by-snapshot-date-v1',"+meta_anchor
    if browser.count(meta_anchor)!=1:raise RuntimeError(f'expected one browser meta anchor, got {browser.count(meta_anchor)}')
    browser=browser.replace(meta_anchor,meta_insert,1)
py=head+browser
browser=py[py.find(fn):]
for t in ["'snapshot_date':snapshot_date","append-only-by-snapshot-date-v1","snapshot_date_source='latest_played_league_fixture'","snapshot_date_semantics","v75-current-db-structural-senior-resolution-no-history"]:
    assert t in browser or (t.startswith('v75-') and t in py),t
assert browser.count("availability_diag=_structural_availability_from_fs(players,fixtures)")==1
compile(py,'fm_importer_v76.py','exec')
html=html[:m.start(1)]+base64.b64encode(py.encode()).decode()+html[m.end(1):];repack(html);assert reconstruct()==html
print('V76 browser snapshot boundary metadata applied')
