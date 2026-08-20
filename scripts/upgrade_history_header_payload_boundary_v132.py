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

# v132: v131 correctly inverted the old-match recovery flow (header -> stats -> candidate),
# but its forward stat scan begins at q, the HOME header start. The proven header includes binary
# metadata and the AWAY sub-header before the player payload. Scanning that prefix with the generic
# 214-byte stat parser can manufacture false player rows/segmentations and cause the deliberately
# conservative v131 uniqueness gate to reject a real match as ambiguous. The exact AWAY marker is
# already known as q+span; its team ID occupies through +12. Begin the player-record scan only after
# that proven structural header boundary. Existing candidate-first and header-first paths remain.

for prereq in [
    'def direct_header_anchored_candidate_pass_v131():',
    'def _v131_structural_headers(raw):',
    'def _v131_scan_stats(raw,start,end):',
    'for hi,(q,home_id,away_id,span) in enumerate(headers):',
    'stats=_v131_scan_stats(raw,q,end)',
    "'header_anchored_fixture_matches':0",
]:
    if prereq not in py:raise RuntimeError('v132 prerequisite missing: '+prereq)

# Diagnostics distinguish true payload scanning from v131's old header-inclusive scan.
diag_anchor="        'header_anchored_duplicate_pairs_skipped':0\n"
diag_new=("        'header_anchored_duplicate_pairs_skipped':0,\n"
          "        'header_anchored_header_prefix_bytes_skipped':0,\n"
          "        'header_anchored_payload_boundary_scans':0\n")
if "'header_anchored_payload_boundary_scans':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v132 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old="                stats=_v131_scan_stats(raw,q,end)\n"
new=("                # v132: q+span is the proven AWAY sub-header marker. Its team-id field\n"
     "                # ends at +12, so bytes before that point are header/metadata, not player rows.\n"
     "                payload_start=q+span+12\n"
     "                if payload_start>=end:\n"
     "                    diagnostics['header_anchored_headers_without_pairs']+=1;continue\n"
     "                diagnostics['header_anchored_header_prefix_bytes_skipped']+=max(0,payload_start-q)\n"
     "                diagnostics['header_anchored_payload_boundary_scans']+=1\n"
     "                stats=_v131_scan_stats(raw,payload_start,end)\n")
if 'stats=_v131_scan_stats(raw,payload_start,end)' not in py:
    if old not in py:raise RuntimeError('v132 v131 scan anchor missing')
    py=py.replace(old,new,1)

handoff_anchor="'unlabelled_rich_header_anchored_duplicate_pairs_skipped':member_rich_diag.get('header_anchored_duplicate_pairs_skipped',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_header_prefix_bytes_skipped':member_rich_diag.get('header_anchored_header_prefix_bytes_skipped',0),"+
    "'unlabelled_rich_header_anchored_payload_boundary_scans':member_rich_diag.get('header_anchored_payload_boundary_scans',0),")
if 'unlabelled_rich_header_anchored_payload_boundary_scans' not in py:
    if handoff_anchor not in py:raise RuntimeError('v132 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'payload_start=q+span+12',
    'stats=_v131_scan_stats(raw,payload_start,end)',
    'header_anchored_header_prefix_bytes_skipped',
    'header_anchored_payload_boundary_scans',
    'unlabelled_rich_header_anchored_payload_boundary_scans',
    'def direct_header_anchored_candidate_pass_v131():',
]:
    if token not in py:raise RuntimeError('v132 token missing: '+token)
if 'stats=_v131_scan_stats(raw,q,end)' in py:
    raise RuntimeError('v132 unsafe header-inclusive v131 scan still present')

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'payload_start=q+span+12' in cpy
assert 'stats=_v131_scan_stats(raw,payload_start,end)' in cpy
assert 'stats=_v131_scan_stats(raw,q,end)' not in cpy
print('v132 header-anchored scan now begins after the proven AWAY team-id sub-header')