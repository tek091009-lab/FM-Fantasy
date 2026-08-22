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

# v170 closes the remaining reachability hole in the 158..213-byte compact transition family.
# v159 can prove CURRENT + two bench/sub successors, and v169 can prove a two-row terminal subgroup
# only when BOTH current and successor are bench-semantic. Neither can recover a side containing
# exactly ONE used substitute when the only compact transition is STARTER11 -> SUB1: v159 lacks a
# second successor and v169 rejects the active/starter-like current row.
#
# Add a very narrow fallback: when the current valid player is NOT bench-semantic, admit one compact
# successor only if that successor has a genuine positive substitution-on minute. Do not admit an
# unused bench row from a single transition because that is insufficient structural evidence. There
# must be exactly one valid used-sub successor start in 158..213 bytes. This only changes row
# reachability; all side/score/fixture/register_match validation remains downstream and unchanged.
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'def _v159_benchish(rr):',
    "globals()['_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169']",
    'if current and _v159_benchish(current):',
    'if len(hits)!=1:return None',
]:
    if token not in py:raise RuntimeError('v170 prerequisite missing: '+token)

start=py.find('def _v148_compact_stride_next(raw,p,end):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

needle="""            if len(two)>1:\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169']=int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169',0))+1\n    if len(hits)!=1:return None\n"""
repl="""            if len(two)>1:\n                globals()['_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169']=int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_AMBIGUITIES_V169',0))+1\n\n        # v170: exactly one used substitute can form a two-row physical subgroup with the last\n        # active/starter row. v159 cannot prove it (needs two successors) and v169 intentionally\n        # requires both rows to be bench-semantic. Only a genuine positive sub_on successor may use\n        # this reduced proof. A lone unused row is not enough evidence.\n        if current and not _v159_benchish(current):\n            one_sub=[]\n            q_hi4=min(int(end)-157,p+214)\n            for q4 in range(p+158,q_hi4):\n                if raw[q4]!=2:continue\n                rr4=_rich_stat_record_at(raw,q4)\n                if not rr4:continue\n                if int(rr4.get('sub_on',0) or 0)<=0:continue\n                pp4=int(rr4.get('player_id',0) or 0)\n                if pp4<=0 or pp4==pid0:continue\n                one_sub.append((q4,q4-p))\n            if len(one_sub)==1:\n                q4,d4=one_sub[0]\n                globals()['_RICH_SINGLE_SUB_COMPACT_TRANSITIONS_V170']=int(globals().get('_RICH_SINGLE_SUB_COMPACT_TRANSITIONS_V170',0))+1\n                globals()['_RICH_SINGLE_SUB_COMPACT_MIN_V170']=min(int(globals().get('_RICH_SINGLE_SUB_COMPACT_MIN_V170',999999)),int(d4))\n                globals()['_RICH_SINGLE_SUB_COMPACT_MAX_V170']=max(int(globals().get('_RICH_SINGLE_SUB_COMPACT_MAX_V170',0)),int(d4))\n                return q4\n            if len(one_sub)>1:\n                globals()['_RICH_SINGLE_SUB_COMPACT_AMBIGUITIES_V170']=int(globals().get('_RICH_SINGLE_SUB_COMPACT_AMBIGUITIES_V170',0))+1\n    if len(hits)!=1:return None\n"""
if needle not in block:raise RuntimeError('v170 v169 decision anchor missing')
block=block.replace(needle,repl,1)
py=py[:start]+block+py[end:]

if 'unlabelled_rich_single_sub_compact_transitions_v170' not in py:
    anchor="'unlabelled_rich_two_row_compact_bench_transitions_v169':int(globals().get('_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169',0)),"
    if anchor in py:
        extra=(anchor+
          "'unlabelled_rich_single_sub_compact_transitions_v170':int(globals().get('_RICH_SINGLE_SUB_COMPACT_TRANSITIONS_V170',0)),"+
          "'unlabelled_rich_single_sub_compact_ambiguities_v170':int(globals().get('_RICH_SINGLE_SUB_COMPACT_AMBIGUITIES_V170',0)),"+
          "'unlabelled_rich_single_sub_compact_min_bytes_v170':int(globals().get('_RICH_SINGLE_SUB_COMPACT_MIN_V170',0) if int(globals().get('_RICH_SINGLE_SUB_COMPACT_MIN_V170',999999))<999999 else 0),"+
          "'unlabelled_rich_single_sub_compact_max_bytes_v170':int(globals().get('_RICH_SINGLE_SUB_COMPACT_MAX_V170',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals()['_RICH_SINGLE_SUB_COMPACT_TRANSITIONS_V170']",
    "globals()['_RICH_SINGLE_SUB_COMPACT_AMBIGUITIES_V170']",
    "int(rr4.get('sub_on',0) or 0)<=0",
    'if current and not _v159_benchish(current):',
    'if len(one_sub)==1:',
    "globals()['_RICH_TWO_ROW_COMPACT_BENCH_TRANSITIONS_V169']",
    'if len(short)==1:',
]:assert token in cpy,token
print('v170 preserves v148/v159/v169 compact proofs and adds only a unique active-current -> positive-sub_on single-successor 158..213-byte transition fallback; downstream match validation is unchanged')
