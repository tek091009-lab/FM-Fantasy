from __future__ import annotations
import base64,gzip,re,sys
from pathlib import Path

def load_html(path:Path|None=None):
    if path:
        return path.read_text(encoding='utf-8')
    root=Path(__file__).resolve().parents[1]
    parts=[root/'app'/f'part{i:02d}' for i in range(17)]+[root/'app'/f'fix{i}' for i in range(17,21)]
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts))).decode('utf-8')

root=Path(__file__).resolve().parents[1]
html=load_html(Path(sys.argv[1]) if len(sys.argv)>1 else None)
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
assert m,'embedded importer missing'
py=base64.b64decode(m.group(1)).decode('utf-8')
compile(py,'fm_importer_v76_assert.py','exec')
required=[
 'v75-current-db-structural-senior-resolution-no-history',
 '_choose_current_squad_option_v75',
 'paired_uid_v75',
 'current_person_senior_quality_v75',
 "'snapshot_date':snapshot_date",
 "snapshot_date_source='latest_played_league_fixture'",
 "'historical_freeze_policy':'append-only-by-snapshot-date-v1'",
 "'snapshot_date_semantics':'FM data boundary; not browser time'",
 'select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)',
 "FIXTURE_DB_HANDOFF_POLICY='loaded-game-db-bytes-v74'",
]
for t in required: assert t in py,'missing '+t
start=py.find('def browser_build_payload_from_fs(');assert start>=0
browser=py[start:]
assert browser.count('availability_diag=_structural_availability_from_fs(players,fixtures)')==1
for t in ["'snapshot_date':snapshot_date","append-only-by-snapshot-date-v1"]:assert t in browser
if len(sys.argv)==1:
    index=(root/'index.html').read_text()
    badge=(root/'snapshotdate.js').read_text()
    assert 'snapshotdate.js?v=1' in index
    assert "snapshot-date-v1" in badge and "FM data · " in badge
print('V75/V76 source assertion passed')
