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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v136: _v131_structural_headers intentionally records every plausible AWAY marker found within
# 512 bytes of one HOME header. Consequently several header candidates can share the exact same
# HOME offset q. v135's next-header delimiter iterator starts at hi+1 and could therefore inspect
# another candidate belonging to the SAME HOME header. If that alias happened to contain direct
# target IDs, v135 could return nq==q as the "next match", truncating the current payload to zero.
#
# A genuine next match header must begin after this match's proven player-payload start. Ignore all
# structural header aliases whose HOME offset is before payload_start. This is a delimiter/parser
# correction only: fixture attachment thresholds and every existing decoder remain unchanged.

for prereq in [
    'def _v135_next_safe_header(raw,headers,hi,payload_start):',
    'def _v131_structural_headers(raw):',
    'payload_start=q+span+12',
    "'header_anchored_prepayload_false_delimiters_skipped':0",
]:
    if prereq not in py:raise RuntimeError('v136 prerequisite missing: '+prereq)

# Add a dedicated diagnostic beside the v135 delimiter diagnostics.
diag_anchor="        'header_anchored_prepayload_false_delimiters_skipped':0\n"
diag_new=("        'header_anchored_prepayload_false_delimiters_skipped':0,\n"
          "        'header_anchored_same_header_aliases_skipped':0\n")
if "'header_anchored_same_header_aliases_skipped':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v136 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old="""        for hj in range(int(hi)+1,len(headers)):\n            nq=int(headers[hj][0]);home_id=int(headers[hj][1]);away_id=int(headers[hj][2])\n            if _v133_header_embedded_in_stat(raw,nq):\n"""
new="""        for hj in range(int(hi)+1,len(headers)):\n            nq=int(headers[hj][0]);home_id=int(headers[hj][1]);away_id=int(headers[hj][2])\n            # Several AWAY-marker interpretations can share one HOME q. None can delimit this\n            # match because the current player payload has not even started yet.\n            if nq<int(payload_start):\n                skipped+=1\n                diagnostics['header_anchored_same_header_aliases_skipped']+=1\n                continue\n            if _v133_header_embedded_in_stat(raw,nq):\n"""
if "diagnostics['header_anchored_same_header_aliases_skipped']+=1" not in py:
    if old not in py:raise RuntimeError('v136 delimiter loop anchor missing')
    py=py.replace(old,new,1)

handoff_anchor="'unlabelled_rich_header_anchored_prepayload_false_delimiters_skipped':member_rich_diag.get('header_anchored_prepayload_false_delimiters_skipped',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_same_header_aliases_skipped':member_rich_diag.get('header_anchored_same_header_aliases_skipped',0),")
if 'unlabelled_rich_header_anchored_same_header_aliases_skipped' not in py:
    if handoff_anchor not in py:raise RuntimeError('v136 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v135_next_safe_header(raw,headers,hi,payload_start):',
    'if nq<int(payload_start):',
    "diagnostics['header_anchored_same_header_aliases_skipped']+=1",
    'unlabelled_rich_header_anchored_same_header_aliases_skipped',
]:
    if token not in py:raise RuntimeError('v136 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'if nq<int(payload_start):' in cpy
assert 'header_anchored_same_header_aliases_skipped' in cpy
print('v136 ignores alternate AWAY-marker aliases from the same HOME header when selecting the next retained-match delimiter')
