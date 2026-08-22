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

# v159 proves a terminal three-player compact subgroup CURRENT -> Q -> S and returns Q. On the
# following scanner iteration there is only one successor (S), so neither the v148 four-row proof
# nor v159's three-row proof can fire again. The final already-proven player S is therefore skipped
# by the normal +214 step whenever Q->S is <214 bytes. v160 carries ONLY that one already-proven
# terminal transition forward to the immediately following helper call. It does not lower the
# evidence requirement for discovering a compact run.
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'def _v159_benchish(rr):',
    'if len(short)==1:',
    "globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']",
]:
    if token not in py:raise RuntimeError('v160 prerequisite missing: '+token)

start=py.find('def _v148_compact_stride_next(raw,p,end):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

if '_RICH_SHORT_COMPACT_BENCH_TAILS_V160' not in block:
    # Consume a pending terminal transition only when it was proven on the immediately preceding
    # v159 call for this exact immutable bytes object/current offset/end boundary. Revalidate the
    # stored player ID and physical stride before returning it.
    anchor="""    r0=_rich_stat_record_at(raw,p)\n    if not r0:return None\n    pid0=int(r0.get('player_id',0) or 0)\n    if pid0<=0:return None\n"""
    insert="""    r0=_rich_stat_record_at(raw,p)\n    if not r0:return None\n    pid0=int(r0.get('player_id',0) or 0)\n    if pid0<=0:return None\n    _v160_pending=globals().setdefault('_RICH_SHORT_COMPACT_PENDING_V160',{})\n    _v160_key=(id(raw),int(p),int(end))\n    _v160_tail=_v160_pending.pop(_v160_key,None)\n    if _v160_tail is not None:\n        _v160_s,_v160_pid,_v160_stride=_v160_tail\n        _v160_d=int(_v160_s)-int(p)\n        _v160_r=_rich_stat_record_at(raw,int(_v160_s)) if 158<=_v160_d<=213 else None\n        if (_v160_r and int(_v160_r.get('player_id',0) or 0)==int(_v160_pid)\n                and abs(_v160_d-int(_v160_stride))<=8):\n            globals()['_RICH_SHORT_COMPACT_BENCH_TAILS_V160']=int(globals().get('_RICH_SHORT_COMPACT_BENCH_TAILS_V160',0))+1\n            return int(_v160_s)\n"""
    if anchor not in block:raise RuntimeError('v160 helper prologue anchor missing')
    block=block.replace(anchor,insert,1)

    old="""            globals()['_RICH_SHORT_COMPACT_BENCH_MAX_V159']=max(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),int(d))\n            return q2\n"""
    new="""            globals()['_RICH_SHORT_COMPACT_BENCH_MAX_V159']=max(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),int(d))\n            # q2 is the next scanner position. Preserve the already-proven final transition q2->s2\n            # for exactly that next call so the third player is not skipped by the fallback +214.\n            _v160_pending=globals().setdefault('_RICH_SHORT_COMPACT_PENDING_V160',{})\n            _v160_pending[(id(raw),int(q2),int(end))]=(int(s2),int(pp2),int(d))\n            return q2\n"""
    if old not in block:raise RuntimeError('v160 v159 short-return anchor missing')
    block=block.replace(old,new,1)
    py=py[:start]+block+py[end:]

# Export a direct count of terminal third-player rows that v159 proved but could not previously reach.
if 'unlabelled_rich_short_compact_bench_tail_rows_v160' not in py:
    anchor="'unlabelled_rich_short_compact_bench_transitions_v159':int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0)),"
    if anchor in py:
        py=py.replace(anchor,anchor+"'unlabelled_rich_short_compact_bench_tail_rows_v160':int(globals().get('_RICH_SHORT_COMPACT_BENCH_TAILS_V160',0)),",1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "globals().setdefault('_RICH_SHORT_COMPACT_PENDING_V160',{})",
    "globals()['_RICH_SHORT_COMPACT_BENCH_TAILS_V160']",
    "_v160_pending[(id(raw),int(q2),int(end))]=(int(s2),int(pp2),int(d))",
    'return int(_v160_s)',
]:assert token in cpy,token
print('v160 carries the already-proven final q2->s2 transition from a unique v159 three-player compact bench chain, so the third terminal player is no longer skipped')