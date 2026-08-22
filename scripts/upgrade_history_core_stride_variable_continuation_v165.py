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

# v165 fixes a structural mismatch between the original v150 short-stride proof and the stateful
# v153/v164 continuation. v150 deliberately accepts a 145..157-byte physical serialization when
# the first three observed strides are NEAR-STABLE (each within four bytes), e.g. 149,151,150.
# After that proof, however, v152/v153 froze only the first stride and demanded every later player
# start at exactly p+d. A legitimate variable-width run could therefore be proved successfully and
# then lose its next/tail rows immediately. Keep v150's proof exactly as-is, but let the already-
# proven continuation search only the same bounded d +/- 4 physical window and proceed only when
# exactly ONE valid unseen player record exists. This is not a general byte scan and cannot create
# the representation itself; initial authority still comes exclusively from v150.
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
    "r['core_gc_continuation_v164']=True",
    'def _v150_core_stride_next(raw,p,end):',
    'if abs(d2-d1)>4:continue',
    'if abs(d3-d1)>4 or abs(d3-d2)>4:continue',
]:
    if token not in py:raise RuntimeError('v165 prerequisite missing: '+token)

start=py.find('def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
old=py[start:end]

new="""def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):
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

    # v150 proved a near-stable family, not one exact fixed width. Search only the same bounded
    # physical tolerance around that already-proven baseline, and never choose between alternatives.
    lo=max(145,d-4);hi=min(157,d+4)
    hits=[]
    for step in range(lo,hi+1):
        q=p+step
        if q+145>int(end):continue
        nr=_v150_core_record_at(raw,q)
        if not nr:continue
        npid=int(nr.get('player_id',0) or 0)
        if npid<=0 or npid==pid or npid in seen:continue
        hits.append((step,q,npid))
    if len(hits)>1:
        globals()['_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165']=int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0))+1
        return None
    if len(hits)==1:
        actual,q,_=hits[0]
        r=_v163_apply_physical_gc(raw,p,end,actual,r) if r else r
        if r and bool(r.get('core_gc_available_v163')):
            r['core_gc_continuation_v164']=True
        r['core_stride_actual_v165']=int(actual)
        if int(actual)!=int(d):
            r['core_stride_variable_continuation_v165']=True
            globals()['_RICH_CORE_STRIDE_VARIABLE_CONTINUATIONS_V165']=int(globals().get('_RICH_CORE_STRIDE_VARIABLE_CONTINUATIONS_V165',0))+1
            globals()['_RICH_CORE_STRIDE_VARIABLE_MIN_V165']=min(int(globals().get('_RICH_CORE_STRIDE_VARIABLE_MIN_V165',999999)),int(actual))
            globals()['_RICH_CORE_STRIDE_VARIABLE_MAX_V165']=max(int(globals().get('_RICH_CORE_STRIDE_VARIABLE_MAX_V165',0)),int(actual))
        return r,q

    # No successor exists in the proven tolerance window. Preserve v153's terminal-row behaviour.
    # With no next object there is no stronger physical-width evidence than the already-proven
    # baseline, so v163/v164's existing conservative rule remains unchanged for this final row.
    r=_v163_apply_physical_gc(raw,p,end,d,r) if r else r
    if r and bool(r.get('core_gc_available_v163')):
        r['core_gc_continuation_v164']=True
    return r,None

"""
py=py[:start]+new+py[end:]

# Export direct evidence for the next real raw-save rerun.
if 'unlabelled_rich_core_stride_variable_continuations_v165' not in py:
    anchors=[
        "'unlabelled_rich_core_gc_continuation_recovered_v164':int(globals().get('_RICH_CORE_GC_CONTINUATION_RECOVERED_V164',0)),",
        "'unlabelled_rich_core_stride_duplicate_pid_rejects_v153':int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_variable_continuations_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_CONTINUATIONS_V165',0)),"+
          "'unlabelled_rich_core_stride_variable_ambiguities_rejected_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0)),"+
          "'unlabelled_rich_core_stride_variable_min_bytes_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_MIN_V165',0) if int(globals().get('_RICH_CORE_STRIDE_VARIABLE_MIN_V165',999999))<999999 else 0),"+
          "'unlabelled_rich_core_stride_variable_max_bytes_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_MAX_V165',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'lo=max(145,d-4);hi=min(157,d+4)',
    "globals()['_RICH_CORE_STRIDE_VARIABLE_CONTINUATIONS_V165']",
    "globals()['_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165']",
    "r['core_stride_actual_v165']=int(actual)",
    'def _v150_core_stride_next(raw,p,end):',
    'if abs(d2-d1)>4:continue',
    'if abs(d3-d1)>4 or abs(d3-d2)>4:continue',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
]:assert token in cpy,token
print('v165 preserves v150 near-stable 145..157-byte proof through continuation: later rows may vary within the already-proven +/-4-byte physical tolerance, but only a unique valid unseen PID can advance the run')
