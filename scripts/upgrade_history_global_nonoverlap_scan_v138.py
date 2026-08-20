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
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v138: v137 fixed the NEW header-first scanner so that, after accepting one complete 214-byte
# GAME_MATCH_PLAYER_STATS record, it resumes at the record's physical end rather than 140 bytes
# later. The ORIGINAL/global retained-stat scanner still contains the same +140 overlap step.
# That means the 24,389-row hard-save diagnostic can be inflated by false records whose starts are
# inside the trailing 74 bytes of an already validated record. Those false rows then poison side
# segmentation, PID cohorts, scores and candidate counts before any fixture matcher sees them.
#
# A fixed 214-byte serialized record cannot contain the beginning of another independent record.
# Preserve byte-by-byte scanning BETWEEN accepted records, but once a record is proven valid skip
# all 214 bytes before looking for the next one. This changes record collection only; no match
# acceptance threshold, club inference or fixture uniqueness rule is relaxed.

for prereq in [
    "globals()['_RICH_UNRATED_INACTIVE_ROWS']",
    "p+=140;continue",
    'def _v131_scan_stats(raw,start,end):',
    'rows.append(r);p+=214;continue',
]:
    if prereq not in py:raise RuntimeError('v138 prerequisite missing: '+prereq)

# Target the legacy/global scanner specifically via the v125 diagnostic block. Do not touch any
# unrelated +140 arithmetic elsewhere in the importer.
old="""            if r:
                out.append(r)
                if r.get('unrated_inactive_candidate'):
                    globals()['_RICH_UNRATED_INACTIVE_ROWS']=int(globals().get('_RICH_UNRATED_INACTIVE_ROWS',0))+1
                p+=140;continue
"""
new="""            if r:
                out.append(r)
                if r.get('unrated_inactive_candidate'):
                    globals()['_RICH_UNRATED_INACTIVE_ROWS']=int(globals().get('_RICH_UNRATED_INACTIVE_ROWS',0))+1
                # v138: this is a complete validated 214-byte physical record. Do not search for
                # another record start inside its trailing 74 bytes. Padding/gaps after the record
                # remain byte-scanned normally on the next loop iterations.
                globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1
                p+=214;continue
"""
if "_RICH_GLOBAL_NONOVERLAP_SCAN_V138" not in py:
    if old not in py:raise RuntimeError('v138 global retained scanner anchor missing')
    py=py.replace(old,new,1)

compile(py,'fm_importer.py','exec')
for token in [
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
    'p+=214;continue',
    'rows.append(r);p+=214;continue',
    'def direct_header_anchored_candidate_pass_v131():',
]:
    if token not in py:raise RuntimeError('v138 token missing: '+token)
if old in py:
    raise RuntimeError('v138 unsafe overlapping global retained scanner still present')

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1" in cpy
assert old not in cpy
print('v138 global retained-stat scanner no longer reparses bytes inside an accepted 214-byte player record')
