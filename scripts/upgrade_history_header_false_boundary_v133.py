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

# v133: v131 delimits a header-anchored old-match scan at the next structural 03 02 / 00 03 02
# header candidate. Those structural candidates are intentionally cheap and unvalidated; the same
# byte sequence can occur inside a legitimate 214-byte GAME_MATCH_PLAYER_STATS record. If that
# happens, next_q truncates the real match payload before enough player rows are collected and the
# true historical game is lost. Keep every existing header decoder, but refuse to use a would-be
# next-header delimiter when it is physically embedded inside a player-stat record that the CURRENT
# live parser validates. This is binary locality evidence, not a fixture/club heuristic.

for prereq in [
    'def _v131_record_at(raw,p):',
    'def _v131_structural_headers(raw):',
    'for hi,(q,home_id,away_id,span) in enumerate(headers):',
    "next_q=headers[hi+1][0] if hi+1<len(headers) else len(raw)",
    'payload_start=q+span+12',
    "'header_anchored_payload_boundary_scans':0",
]:
    if prereq not in py:raise RuntimeError('v133 prerequisite missing: '+prereq)

diag_anchor="        'header_anchored_payload_boundary_scans':0\n"
diag_new=("        'header_anchored_payload_boundary_scans':0,\n"
          "        'header_anchored_embedded_false_delimiters_skipped':0,\n"
          "        'header_anchored_extended_after_false_delimiter_scans':0\n")
if "'header_anchored_embedded_false_delimiters_skipped':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v133 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

helper_anchor="    def _v131_pair_signature(left,right):\n"
helper_code=r'''    def _v133_header_embedded_in_stat(raw,hq):
        # A real 214-byte player record spanning hq proves that this particular header-like marker
        # is payload bytes, not a safe boundary between matches. Search only the 213 possible starts
        # that could physically cover hq; no archive/member rescan is introduced.
        lo=max(0,int(hq)-213);hi=min(int(hq),len(raw)-214)
        for p in range(lo,hi+1):
            if p>=int(hq) or raw[p]!=2:continue
            try:r=_v131_record_at(raw,p)
            except Exception:r=None
            if r is not None and p<int(hq)<p+214:
                return True
        return False

    def _v133_next_safe_header(raw,headers,hi):
        skipped=0
        for hj in range(int(hi)+1,len(headers)):
            nq=int(headers[hj][0])
            if _v133_header_embedded_in_stat(raw,nq):
                skipped+=1;continue
            return nq,skipped
        return len(raw),skipped

    def _v131_pair_signature(left,right):
'''
if 'def _v133_header_embedded_in_stat(raw,hq):' not in py:
    if helper_anchor not in py:raise RuntimeError('v133 helper insertion anchor missing')
    py=py.replace(helper_anchor,helper_code,1)

old="                next_q=headers[hi+1][0] if hi+1<len(headers) else len(raw)\n"
new=("                next_q,_v133_skipped=_v133_next_safe_header(raw,headers,hi)\n"
     "                if _v133_skipped:\n"
     "                    diagnostics['header_anchored_embedded_false_delimiters_skipped']+=_v133_skipped\n"
     "                    diagnostics['header_anchored_extended_after_false_delimiter_scans']+=1\n")
if '_v133_next_safe_header(raw,headers,hi)' not in py:
    if old not in py:raise RuntimeError('v133 next-header delimiter anchor missing')
    py=py.replace(old,new,1)

handoff_anchor="'unlabelled_rich_header_anchored_payload_boundary_scans':member_rich_diag.get('header_anchored_payload_boundary_scans',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_embedded_false_delimiters_skipped':member_rich_diag.get('header_anchored_embedded_false_delimiters_skipped',0),"+
    "'unlabelled_rich_header_anchored_extended_after_false_delimiter_scans':member_rich_diag.get('header_anchored_extended_after_false_delimiter_scans',0),")
if 'unlabelled_rich_header_anchored_embedded_false_delimiters_skipped' not in py:
    if handoff_anchor not in py:raise RuntimeError('v133 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v133_header_embedded_in_stat(raw,hq):',
    'def _v133_next_safe_header(raw,headers,hi):',
    '_v133_next_safe_header(raw,headers,hi)',
    'header_anchored_embedded_false_delimiters_skipped',
    'header_anchored_extended_after_false_delimiter_scans',
    'payload_start=q+span+12',
    'register_match(ci,f,rev,leid,reid,source)',
]:
    if token not in py:raise RuntimeError('v133 token missing: '+token)
if "next_q=headers[hi+1][0] if hi+1<len(headers) else len(raw)" in py:
    raise RuntimeError('v133 unsafe unvalidated next-header delimiter still present')

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'def _v133_header_embedded_in_stat(raw,hq):' in cpy
assert '_v133_next_safe_header(raw,headers,hi)' in cpy
print('v133 ignores header-like delimiters embedded inside validated retained player-stat records')
