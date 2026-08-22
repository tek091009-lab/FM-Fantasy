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

# v169 targets the final reachability hole in the 158..213-byte compact player-object family.
# v148 proves a compact run from CURRENT + three successor rows. v159 lowers that only for a
# terminal bench/substitute subgroup containing CURRENT + two successors. A subgroup consisting of
# exactly TWO bench rows can therefore never be recovered: the one genuine compact transition has
# only a single successor and neither proof is mathematically possible.
#
# Add a deliberately narrow two-row fallback. It is NOT a general compact-stride proof. Both the
# current row and the unique successor must independently have bench/substitute semantics, and there
# must be exactly one valid successor start in the already-established 158..213 byte family. The
# normal v148 four-row and v159 three-row proofs retain priority. This only recovers the physical
# transition; all later side/score/fixture/register_match safeguards are unchanged.
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'def _v159_benchish(rr):',
    "globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']",
    'if len(short)==1:',
]:
    if token not in py:raise RuntimeError('v169 prerequisite missing: '+token)

start=py.find('def _v148_compact_stride_next(raw,p,end):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

old="""        if len(short)==1:\n            q2,s2,d=short[0]\n            globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']=int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0))+1\n            globals()['_RICH_SHORT_COMPACT_BENCH_MIN_V159']=min(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MIN_V159',999999)),int(d))\n            globals()['_RICH_SHORT_COMPACT_BENCH_MAX_V159']=max(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),int(d))\n            return q2\n    if len(hits)!=1:return None\n"""
new="""        if len(short)==1:\n            q2,s2,d=short[0]\n            globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']=int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0))+1\n            globals()['_RICH_SHORT_COMPACT_BENCH_MIN_V159']=min(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MIN_V159',999999)),int(d))\n            globals()['_RICH_SHORT_COMPACT_BENCH_MAX_V159']=max(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),int(d))\n            return q2\n\n        # v169: an exactly-two-row terminal bench subgroup has only one physical transition, so\n        # neither v148 (four rows) nor v159 (three rows) can ever prove it. Keep this fallback\n        # bench-semantic on BOTH ends and require one unique valid compact successor. It cannot\n        # activate for a starter/general player chain and cannot choose between byte starts.\n        current=_rich_stat_record_at(raw,p)\n        if current and _v159_benchish(current):\n            two=[]\n            q_hi3=min(int(end)-157,p+214)\n            for q3 in range(p+158,q_hi3):\n                if raw[q3]!=2:continue\n                rr3=_rich_stat_record_at(raw,q3)\n                if not rr3 or not _v159_benchish(rr3):continue\n                pp3=int(rr3.get('player_id',0) or 0)\n                if pp3<=0 or pp3==pid0:continue\n                two.append((q3,q3-p))\n            if len(two)==1:\n                q3,d3=two[0]\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169']=int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169',0))+1\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_MIN_V169']=min(int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_MIN_V169',999999)),int(d3))\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_MAX_V169']=max(int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_MAX_V169',0)),int(d3))\n                return q3\n            if len(two)>1:\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169']=int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169',0))+1\n    if len(hits)!=1:return None\n"""
if old not in block:raise RuntimeError('v169 v159 terminal decision anchor missing')
block=block.replace(old,new,1)
py=py[:start]+block+py[end:]

# Export direct evidence when a v159 diagnostic anchor is available.
if 'unlabelled_rich_two_row_compact_bench_transitions_v169' not in py:
    anchor="'unlabelled_rich_short_compact_bench_transitions_v159':int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0)),"
    if anchor in py:
        extra=(anchor+
          "'unlabelled_rich_two_row_compact_bench_transitions_v169':int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169',0)),"+
          "'unlabelled_rich_two_row_compact_bench_ambiguities_v169':int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169',0)),"+
          "'unlabelled_rich_two_row_compact_bench_min_bytes_v169':int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_MIN_V169',0) if int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_MIN_V169',999999))<999999 else 0),"+
          "'unlabelled_rich_two_row_compact_bench_max_bytes_v169':int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_MAX_V169',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals()['_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169']",
    "globals()['_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169']",
    'if current and _v159_benchish(current):',
    'if len(two)==1:',
    'if len(short)==1:',
    'if len(hits)!=1:return None',
]:assert token in cpy,token
print('v169 preserves v148/v159 compact proofs and adds only a unique two-row bench-semantic 158..213-byte transition fallback; downstream match validation is unchanged')