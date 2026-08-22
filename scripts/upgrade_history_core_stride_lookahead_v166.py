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

# v166 fixes a fail-closed ambiguity that can truncate a *proven* 145..157-byte historical
# player-object run. v165 correctly searches only the already-proven +/-4-byte width family, but if
# two byte starts independently look like valid player cores it rejects the entire continuation.
# That is safe, but unnecessarily loses a genuine row when only one of those starts itself continues
# into another structurally valid unseen player at the same near-stable spacing. v166 does not widen
# the search window and cannot create a short-stride representation. It only uses one extra player
# of structural lookahead to resolve an ambiguity that v150/v165 have already bounded.
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    'lo=max(145,d-4);hi=min(157,d+4)',
    "globals()['_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165']",
    'def _v150_core_record_at(raw,p):',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
]:
    if token not in py:raise RuntimeError('v166 prerequisite missing: '+token)

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

    # v166: if the bounded v165 window contains multiple plausible player starts, do not choose by
    # proximity. Instead require exactly one candidate to have exactly one structurally valid unseen
    # successor in the same already-proven near-stable width family. A candidate with zero or >1
    # successors cannot resolve the ambiguity. This is one-step lookahead only and remains fail-closed.
    if len(hits)>1:
        qualified=[]
        for step,q,npid in hits:
            lo2=max(145,int(step)-4);hi2=min(157,int(step)+4)
            next_hits=[]
            for step2 in range(lo2,hi2+1):
                q2=q+step2
                if q2+145>int(end):continue
                rr=_v150_core_record_at(raw,q2)
                if not rr:continue
                pid2=int(rr.get('player_id',0) or 0)
                if pid2<=0 or pid2 in seen or pid2 in (pid,npid):continue
                next_hits.append((step2,q2,pid2))
            if len(next_hits)==1:
                qualified.append((step,q,npid,next_hits[0]))
        if len(qualified)==1:
            step,q,npid,_look=qualified[0]
            hits=[(step,q,npid)]
            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166',0))+1
        else:
            globals()['_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166']=int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166',0))+1
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

    r=_v163_apply_physical_gc(raw,p,end,d,r) if r else r
    if r and bool(r.get('core_gc_available_v163')):
        r['core_gc_continuation_v164']=True
    return r,None

"""
py=py[:start]+new+py[end:]

# Export evidence for the first real hard-save rerun.
if 'unlabelled_rich_core_stride_lookahead_resolved_v166' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_variable_ambiguities_rejected_v165':int(globals().get('_RICH_CORE_STRIDE_VARIABLE_AMBIGUITIES_REJECTED_V165',0)),",
        "'unlabelled_rich_core_stride_duplicate_pid_rejects_v153':int(globals().get('_RICH_CORE_STRIDE_DUPLICATE_PID_REJECTS_V153',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_lookahead_resolved_v166':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166',0)),"+
          "'unlabelled_rich_core_stride_lookahead_unresolved_v166':int(globals().get('_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_RESOLVED_V166']",
    "globals()['_RICH_CORE_STRIDE_LOOKAHEAD_UNRESOLVED_V166']",
    'if len(qualified)==1:',
    'if len(next_hits)==1:',
    'lo2=max(145,int(step)-4);hi2=min(157,int(step)+4)',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
]:assert token in cpy,token
print('v166 preserves fail-closed short-stride recovery while allowing one extra structural player to disambiguate multiple bounded v165 starts')
