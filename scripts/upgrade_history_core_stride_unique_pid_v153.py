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

# v153 fixes a structural contamination hole in v152's proven 145..157-byte continuation.
# v150 initially proves four DISTINCT stable player IDs, but v152 continuation only prevented the
# current row repeating the immediately previous PID. A later row could therefore repeat P1 after
# P1,P2,P3,P4 and still be accepted into the same physical run. That duplicate row can poison team
# uniqueness/side construction and hide an otherwise valid historical match. Keep the initial v150
# proof unchanged; once a short-stride run is active, require every accepted continuation PID to be
# unique across the ENTIRE run.
for token in [
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
    '_v152_core_stride=None',
    '_v152_core_last_pid=None',
    "globals()['_RICH_CORE_STRIDE_CONTINUATIONS_V152']",
    "globals()['_RICH_HEADER_CORE_STRIDE_CONTINUATIONS_V152']",
]:
    if token not in py:raise RuntimeError('v153 prerequisite missing: '+token)

helper="""
def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):
    try:d=int(stride)
    except Exception:return None
    if not (145<=d<=157):return None
    seen=set(int(x) for x in (seen_pids or ()) if int(x)>0)
    r=_v150_core_record_at(raw,p)
    if not r:return None
    pid=int(r.get('player_id',0) or 0)
    if pid<=0 or pid in seen:
        globals()['_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153']=int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0))+1
        return None
    q=p+d
    # The current row is valid as the terminal record even when no complete next core remains.
    if q+145>int(end):return r,None
    nr=_v150_core_record_at(raw,q)
    npid=int(nr.get('player_id',0) or 0) if nr else 0
    if not nr or npid<=0:return r,None
    if npid==pid or npid in seen:
        globals()['_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153']=int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0))+1
        return r,None
    return r,q

"""
if 'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):' not in py:
    anchor='def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):'
    pos=py.find(anchor)
    if pos<0:raise RuntimeError('v153 helper anchor missing')
    py=py[:pos]+helper+py[pos:]

# Patch both v152 scanner instances. Maintain one seen-PID set per proven compact run. The set is
# seeded/extended only by rows actually appended while the proven v150/v152 stride is active and is
# reset whenever that physical run terminates.
py=py.replace('_v152_core_stride=None\n    _v152_core_last_pid=None\n    while p+145<=',
              '_v152_core_stride=None\n    _v152_core_last_pid=None\n    _v153_core_seen_pids=set()\n    while p+145<=',2)

old='_v152_state_pair=_v152_core_stride_continue('
if py.count(old)<2:raise RuntimeError('v153 expected two v152 continuation calls')
# Replace the full fifth argument by the new seen set without changing scanner raw/end variables.
py=re.sub(r'_v152_state_pair=_v152_core_stride_continue\(([^,]+),p,([^,]+),_v152_core_stride,_v152_core_last_pid\)',
          r'_v152_state_pair=_v153_core_stride_continue(\1,p,\2,_v152_core_stride,_v153_core_seen_pids)',py,count=2)

# Whenever v152 declares the physical run broken, clear its accumulated uniqueness evidence too.
py=py.replace('        _v152_core_stride=None\n        _v152_core_last_pid=None',
              '        _v152_core_stride=None\n        _v152_core_last_pid=None\n        _v153_core_seen_pids.clear()',2)

# The accepted-row append blocks already expose r. Add each accepted core-stride PID to the run-wide
# set, including the first row whose strict v150 proof activates the stride. This prevents P1 from
# reappearing several records later even though it is not the immediate predecessor.
append_pat=re.compile(r"(\s+)(out\.append\(r\)|rows\.append\(r\))\n\1if _v152_state_pair is not None:")

def repl(mm):
    ind=mm.group(1)
    return (ind+mm.group(2)+'\n'+
            ind+'if _v152_core_stride is not None:\n'+
            ind+'    _v153_pid=int(r.get(\'player_id\',0) or 0)\n'+
            ind+'    if _v153_pid>0:_v153_core_seen_pids.add(_v153_pid)\n'+
            ind+'if _v152_state_pair is not None:')
py,n=append_pat.subn(repl,py,count=2)
if n!=2:raise RuntimeError(f'v153 append-state patches={n}, expected 2')

# When a terminal row ends proven-stride mode, clear state after that row has been counted.
py=py.replace("                        _v152_core_stride=None\n", 
              "                        _v152_core_stride=None\n                        _v153_core_seen_pids.clear()\n",2)

# Export evidence so the next hard-save rerun tells us whether duplicated PIDs were actually being
# admitted by the short-stride representation.
if 'unlabelled_rich_core_stride_duplicate_pid_rejects_v153' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_tail_rows_v152':int(globals().get('_RICH_CORE_STRIDE_TAIL_ROWS_V152',0)),",
        "'unlabelled_rich_core_stride_continuations_v152':int(globals().get('_RICH_CORE_STRIDE_CONTINUATIONS_V152',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_duplicate_pid_rejects_v153':int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    '_v153_core_seen_pids=set()',
    '_v153_pid=int(r.get(\'player_id\',0) or 0)',
    "globals()['_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153']",
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
    'def _v150_core_stride_next(raw,p,end):',
]:assert token in cpy,token
print('v153 preserves v150/v152 short-stride recovery while rejecting any stable PID repeated anywhere inside one proven physical player run')