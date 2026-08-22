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

# v168 targets a remaining fail-closed loss inside the already-proven 145..157-byte player-object
# representation. v166 uses one extra player to disambiguate multiple bounded byte starts. If TWO
# candidate starts each have one unique successor, v166 correctly refuses to choose. But one of
# those two short chains can be an accidental parser coincidence that dies one player later while
# the genuine compact serialization continues. Use exactly ONE additional structural player only in
# that already-bounded case. This cannot create compact mode, cannot widen the +/-4 byte family and
# cannot choose by proximity. Exactly one two-step chain must survive; otherwise ambiguity remains.
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']",
    "globals().setdefault('_RICH_CORE_STRIDE_LOOKAHEAD_PENDING_V167',{})",
    '_v167_pending[(id(raw),int(q),int(end))]',
    'qualified.append((step,q,npid,next_hits[0]))',
]:
    if token not in py:raise RuntimeError('v168 prerequisite missing: '+token)

start=py.find('def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

old="""        else:\n            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166',0))+1\n            globals()['_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165']=int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0))+1\n            return None\n"""
new="""        else:\n            # v168: v166 may leave >=2 candidates where each has exactly one q2 successor. Probe\n            # one and only one further compact player. A candidate qualifies only if its already-\n            # unique q2 itself has exactly one unseen q3 inside the same proven +/-4 byte family.\n            _v168_deep=[]\n            if len(qualified)>1:\n                for _v168_step,_v168_q,_v168_npid,_v168_look in qualified:\n                    _v168_step2,_v168_q2,_v168_pid2=_v168_look\n                    _v168_lo3=max(145,int(_v168_step2)-4);_v168_hi3=min(157,int(_v168_step2)+4)\n                    _v168_third=[]\n                    for _v168_step3 in range(_v168_lo3,_v168_hi3+1):\n                        _v168_q3=int(_v168_q2)+int(_v168_step3)\n                        if _v168_q3+145>int(end):continue\n                        _v168_r3=_v150_core_record_at(raw,_v168_q3)\n                        if not _v168_r3:continue\n                        _v168_pid3=int(_v168_r3.get('player_id',0) or 0)\n                        if (_v168_pid3<=0 or _v168_pid3 in seen or\n                                _v168_pid3 in (pid,int(_v168_npid),int(_v168_pid2))):continue\n                        _v168_third.append((_v168_step3,_v168_q3,_v168_pid3))\n                    if len(_v168_third)==1:\n                        _v168_deep.append((_v168_step,_v168_q,_v168_npid,_v168_look,_v168_third[0]))\n            if len(_v168_deep)==1:\n                step,q,npid,_look,_v168_tail=_v168_deep[0]\n                hits=[(step,q,npid)]\n                _v167_step2,_v167_q2,_v167_pid2=_look\n                _v168_step3,_v168_q3,_v168_pid3=_v168_tail\n                _v167_pending=globals().setdefault('_RICH_CORE_STRIDE_LOOKAHEAD_PENDING_V167',{})\n                # Preserve both transitions already paid for by the depth-2 structural proof.\n                _v167_pending[(id(raw),int(q),int(end))]=(int(npid),int(_v167_q2),int(_v167_pid2),int(_v167_step2))\n                _v167_pending[(id(raw),int(_v167_q2),int(end))]=(int(_v167_pid2),int(_v168_q3),int(_v168_pid3),int(_v168_step3))\n                globals()['_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_RESOLVED_V168']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_RESOLVED_V168',0))+1\n            else:\n                globals()['_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_UNRESOLVED_V168']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_UNRESOLVED_V168',0))+1\n                globals()['_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166',0))+1\n                globals()['_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165']=int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0))+1\n                return None\n"""
if old not in block:raise RuntimeError('v168 unresolved v166 branch anchor missing')
block=block.replace(old,new,1)
py=py[:start]+block+py[end:]

# Export direct evidence for the next real hard-save rerun.
if 'unlabelled_rich_core_stride_lookahead_depth2_resolved_v168' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_lookahead_tail_rows_v167':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_TAILS_V167',0)),",
        "'unlabelled_rich_core_stride_lookahead_unresolved_v166':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_lookahead_depth2_resolved_v168':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_RESOLVED_V168',0)),"+
          "'unlabelled_rich_core_stride_lookahead_depth2_unresolved_v168':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_UNRESOLVED_V168',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_RESOLVED_V168']",
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_DEPTH2_UNRESOLVED_V168']",
    '_v167_pending[(id(raw),int(_v167_q2),int(end))]=(int(_v167_pid2),int(_v168_q3),int(_v168_pid3),int(_v168_step3))',
    'if len(_v168_deep)==1:',
    'if len(_v168_third)==1:',
]:assert token in cpy,token
print('v168 adds one bounded depth-2 structural proof only when multiple v166 one-step chains survive; exactly one continuing chain wins and both already-proven successor transitions are preserved for one-shot revalidation')
