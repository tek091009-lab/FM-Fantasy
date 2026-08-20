from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    if len(chunks)<len(PARTS):chunks+=['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

HELPER="""def _rich_is_retained_match_member(name:str):
    # Only isolated retained match files are safe input for unlabelled player-side recovery.
    # Aggregate databases such as news.dat/play_fixture_manager.dat contain repeated copies of
    # the same 214-byte-looking structures and create hundreds of false lineup windows.
    return Path(str(name or '')).suffix.lower() in ('.scm','.apm','.pkm')


"""
if 'def _rich_is_retained_match_member(' not in py:
    anchor='def recover_unlabelled_rich_members('
    at=py.find(anchor)
    if at<0:raise RuntimeError('recover_unlabelled_rich_members missing')
    py=py[:at]+HELPER+py[at:]

old_diag="        'same_lineup_distinct_regions_preserved':0\n"
new_diag="        'same_lineup_distinct_regions_preserved':0,'non_retained_members_skipped':0,'non_retained_member_names':[]\n"
if new_diag not in py:
    if old_diag not in py:raise RuntimeError('rich diagnostics anchor missing')
    py=py.replace(old_diag,new_diag,1)

old_loop="""    for i,name in enumerate(rich_names):
        path=Path(f'/tmp/rich_{i}.bin')
        if not path.exists():continue
        diagnostics['members_scanned']+=1
        buf=path.read_bytes()
"""
new_loop="""    for i,name in enumerate(rich_names):
        path=Path(f'/tmp/rich_{i}.bin')
        if not path.exists():continue
        if not _rich_is_retained_match_member(name):
            diagnostics['non_retained_members_skipped']+=1
            if len(diagnostics['non_retained_member_names'])<20:diagnostics['non_retained_member_names'].append(str(name))
            continue
        diagnostics['members_scanned']+=1
        buf=path.read_bytes()
"""
if new_loop not in py:
    if old_loop not in py:raise RuntimeError('rich member loop anchor missing')
    py=py.replace(old_loop,new_loop,1)

needle="'unlabelled_rich_members_scanned':member_rich_diag.get('members_scanned',0),"
extra=needle+"'unlabelled_rich_non_retained_members_skipped':member_rich_diag.get('non_retained_members_skipped',0),'unlabelled_rich_non_retained_member_names':member_rich_diag.get('non_retained_member_names',[]),"
if 'unlabelled_rich_non_retained_members_skipped' not in py:
    if needle not in py:raise RuntimeError('rich diagnostics export anchor missing')
    py=py.replace(needle,extra,1)

compile(py,'fm_importer_v98.py','exec')
assert "('.scm','.apm','.pkm')" in py
assert "non_retained_members_skipped" in py
assert "unlabelled_rich_non_retained_member_names" in py
new_b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]

for old in [
    "payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation + grounded-fixture retention-v86 + retained-member-min36-v92';",
    "payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation + grounded-fixture retention-v86';"
]:
    if old in html:
        new=old[:-2]+" + retained-source-scope-v98';"
        html=html.replace(old,new,1)
        break

repack(html)
assert reconstruct()==html
print('v98: unlabelled rich recovery scoped to isolated .scm/.apm/.pkm retained match members')
# explicit apply-workflow trigger 2026-08-20
