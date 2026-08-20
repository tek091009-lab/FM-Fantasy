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

# v137: the header-first scanner parses a structurally validated 214-byte player-stat record,
# then advances only 140 bytes. That deliberately re-enters the final 74 bytes of the record and
# asks the stat parser whether another player record begins inside an already validated record.
# A serialized fixed-width record cannot legitimately begin inside itself. Embedded bytes can,
# however, accidentally satisfy the parser and create extra rows/side segmentations, causing the
# conservative header-first uniqueness gate to reject an otherwise real historical match.
# Once a 214-byte record is accepted, resume at its physical end. Existing byte-by-byte scanning
# between records is retained, so variable inter-record padding/gaps remain supported.

for prereq in [
    'def _v131_scan_stats(raw,start,end):',
    'rows.append(r);p+=140;continue',
    'def direct_header_anchored_candidate_pass_v131():',
    'payload_start=q+span+12',
]:
    if prereq not in py:raise RuntimeError('v137 prerequisite missing: '+prereq)

old='                    rows.append(r);p+=140;continue\n'
new=("                    # v137: r validated the complete 214-byte physical player record.\n"
     "                    # Never re-enter its trailing bytes looking for an overlapping record.\n"
     "                    rows.append(r);p+=214;continue\n")
if 'rows.append(r);p+=214;continue' not in py:
    if old not in py:raise RuntimeError('v137 header scan step anchor missing')
    py=py.replace(old,new,1)

# Record the policy in diagnostics so a hard-save rerun can prove which scanner build was used.
diag_anchor="        'header_anchored_same_header_aliases_skipped':0\n"
diag_new=("        'header_anchored_same_header_aliases_skipped':0,\n"
          "        'header_anchored_nonoverlap_record_scan_v137':1\n")
if "'header_anchored_nonoverlap_record_scan_v137':1" not in py:
    if diag_anchor not in py:raise RuntimeError('v137 diagnostics anchor missing; apply v136 first')
    py=py.replace(diag_anchor,diag_new,1)

handoff_anchor="'unlabelled_rich_header_anchored_same_header_aliases_skipped':member_rich_diag.get('header_anchored_same_header_aliases_skipped',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_nonoverlap_record_scan_v137':member_rich_diag.get('header_anchored_nonoverlap_record_scan_v137',0),")
if 'unlabelled_rich_header_anchored_nonoverlap_record_scan_v137' not in py:
    if handoff_anchor not in py:raise RuntimeError('v137 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v131_scan_stats(raw,start,end):',
    'rows.append(r);p+=214;continue',
    "'header_anchored_nonoverlap_record_scan_v137':1",
    'unlabelled_rich_header_anchored_nonoverlap_record_scan_v137',
    'def direct_header_anchored_candidate_pass_v131():',
]:
    if token not in py:raise RuntimeError('v137 token missing: '+token)
if 'rows.append(r);p+=140;continue' in py:
    raise RuntimeError('v137 unsafe overlapping header stat scan still present')

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'rows.append(r);p+=214;continue' in cpy
assert 'rows.append(r);p+=140;continue' not in cpy
print('v137 header-first stat scanning no longer reparses bytes inside an accepted 214-byte player record')
