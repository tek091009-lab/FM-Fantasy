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

# v166 can resolve two bounded 145..157-byte candidate starts by proving that exactly one of them
# has exactly one further valid unseen player. However, it discards that second proven transition.
# On the immediately following scanner call the newly selected row may again have multiple plausible
# starts (or no independently re-provable continuation), so the exact successor that v166 already
# proved can still be lost. v167 carries ONLY that already-proven q->q2 transition into the next
# call, revalidates offset/PID/stride/current PID, consumes it once, and never discovers a compact
# run on its own. This is analogous to the earlier v160 terminal-proof carry but for v166 lookahead.
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']",
    'qualified.append((step,q,npid,next_hits[0]))',
    'step,q,npid,_look=qualified[0]',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
]:
    if token not in py:raise RuntimeError('v167 prerequisite missing: '+token)

start=py.find('def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

# Consume a pending v166-proven successor only on the exact next raw object / offset / end boundary.
# Revalidate current PID, next PID and physical step before trusting it.
anchor="""    pid=int(r.get('player_id',0) or 0)\n    if pid<=0 or pid in seen:\n        globals()['_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153']=int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0))+1\n        return None\n\n    lo=max(145,d-4);hi=min(157,d+4)\n"""
insert="""    pid=int(r.get('player_id',0) or 0)\n    if pid<=0 or pid in seen:\n        globals()['_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153']=int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0))+1\n        return None\n\n    _v167_pending=globals().setdefault('_RICH_CORE_STRIDE_LOOKAHEAD_PENDING_V167',{})\n    _v167_key=(id(raw),int(p),int(end))\n    _v167_tail=_v167_pending.pop(_v167_key,None)\n    if _v167_tail is not None:\n        _v167_expected_pid,_v167_q2,_v167_pid2,_v167_step2=_v167_tail\n        _v167_actual=int(_v167_q2)-int(p)\n        _v167_r2=_v150_core_record_at(raw,int(_v167_q2)) if 145<=_v167_actual<=157 else None\n        if (int(pid)==int(_v167_expected_pid) and _v167_r2\n                and int(_v167_r2.get('player_id',0) or 0)==int(_v167_pid2)\n                and int(_v167_pid2)>0 and int(_v167_pid2) not in seen and int(_v167_pid2)!=int(pid)\n                and int(_v167_actual)==int(_v167_step2) and abs(int(_v167_actual)-int(d))<=4):\n            r=_v163_apply_physical_gc(raw,p,end,int(_v167_actual),r) if r else r\n            if r and bool(r.get('core_gc_available_v163')):\n                r['core_gc_continuation_v164']=True\n            r['core_stride_actual_v165']=int(_v167_actual)\n            r['core_stride_lookahead_tail_v167']=True\n            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_TAILS_V167']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_TAILS_V167',0))+1\n            return r,int(_v167_q2)\n        globals()['_RICH_CORE_STRIDE_LOOKAHEAD_TAIL_REVALIDATION_REJECTS_V167']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_TAIL_REVALIDATION_REJECTS_V167',0))+1\n\n    lo=max(145,d-4);hi=min(157,d+4)\n"""
if anchor not in block:raise RuntimeError('v167 helper prologue anchor missing')
block=block.replace(anchor,insert,1)

# When v166 has already proved the winning q and one unique q2 successor, preserve q->q2 for the
# exact immediately-following call instead of discarding _look.
old="""        if len(qualified)==1:\n            step,q,npid,_look=qualified[0]\n            hits=[(step,q,npid)]\n            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166',0))+1\n"""
new="""        if len(qualified)==1:\n            step,q,npid,_look=qualified[0]\n            hits=[(step,q,npid)]\n            _v167_step2,_v167_q2,_v167_pid2=_look\n            _v167_pending=globals().setdefault('_RICH_CORE_STRIDE_LOOKAHEAD_PENDING_V167',{})\n            _v167_pending[(id(raw),int(q),int(end))]=(int(npid),int(_v167_q2),int(_v167_pid2),int(_v167_step2))\n            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166',0))+1\n"""
if old not in block:raise RuntimeError('v167 v166 qualified anchor missing')
block=block.replace(old,new,1)
py=py[:start]+block+py[end:]

# Export direct evidence for the next hard-save rerun.
if 'unlabelled_rich_core_stride_lookahead_tail_rows_v167' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_lookahead_resolved_v166':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166',0)),",
        "'unlabelled_rich_core_stride_variable_ambiguities_rejected_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_lookahead_tail_rows_v167':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_TAILS_V167',0)),"+
          "'unlabelled_rich_core_stride_lookahead_tail_revalidation_rejects_v167':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_TAIL_REVALIDATION_REJECTS_V167',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals().setdefault('_RICH_CORE_STRIDE_LOOKAHEAD_PENDING_V167',{})",
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_TAILS_V167']",
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_TAIL_REVALIDATION_REJECTS_V167']",
    "_v167_pending[(id(raw),int(q),int(end))]=(int(npid),int(_v167_q2),int(_v167_pid2),int(_v167_step2))",
    "r['core_stride_lookahead_tail_v167']=True",
]:assert token in cpy,token
print('v167 preserves and one-shot revalidates the exact q->q2 transition already proved by v166 lookahead, so the successor used to disambiguate a compact player start is not discarded on the next scanner step')
