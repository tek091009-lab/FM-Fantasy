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

# v149 established that every currently consumed full GAME_MATCH_PLAYER_STATS field is readable
# when exactly 158 bytes remain. v148/v159 were written before that change and their compact-stride
# search windows still stop too early: v148 uses end-213, while v159 uses end-158 as an EXCLUSIVE
# range bound. Both therefore miss valid compact rows near the end of a retained payload/member.
#
# v161 changes only search reachability. A valid record may begin at end-158 inclusive, so Python's
# exclusive range upper bound must be end-157. The maximum compact stride remains 213 bytes, so the
# other upper bound stays current_position+214. All existing repeated-stride/bench evidence and
# downstream fixture validation remain untouched.
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'q_hi=min(int(end)-213,p+214)',
    's_hi=min(int(end)-213,q+214)',
    't_hi=min(int(end)-213,s+214)',
    'q_hi2=min(int(end)-158,p+214)',
    's_hi2=min(int(end)-158,q2+214)',
    "globals()['_RICH_SHORT_COMPACT_BENCH_TAILS_V160']",
]:
    if token not in py:raise RuntimeError('v161 prerequisite missing: '+token)

replacements={
    'q_hi=min(int(end)-213,p+214)':'q_hi=min(int(end)-157,p+214)',
    's_hi=min(int(end)-213,q+214)':'s_hi=min(int(end)-157,q+214)',
    't_hi=min(int(end)-213,s+214)':'t_hi=min(int(end)-157,s+214)',
    'q_hi2=min(int(end)-158,p+214)':'q_hi2=min(int(end)-157,p+214)',
    's_hi2=min(int(end)-158,q2+214)':'s_hi2=min(int(end)-157,q2+214)',
}
for old,new in replacements.items():
    if py.count(old)!=1:raise RuntimeError(f'v161 expected one occurrence of {old!r}, found {py.count(old)}')
    py=py.replace(old,new,1)

# Export a policy marker so future debugs/build audits can distinguish the corrected inclusive tail
# bound from the earlier compact-stride implementations.
if "_RICH_COMPACT_TAIL_BOUND_V161" not in py:
    anchor="globals()['_RICH_SHORT_COMPACT_BENCH_TAILS_V160']=int(globals().get('_RICH_SHORT_COMPACT_BENCH_TAILS_V160',0))+1"
    if anchor not in py:raise RuntimeError('v161 marker anchor missing')
    py=py.replace(anchor,anchor+"\n            globals()['_RICH_COMPACT_TAIL_BOUND_V161']=1",1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'q_hi=min(int(end)-157,p+214)',
    's_hi=min(int(end)-157,q+214)',
    't_hi=min(int(end)-157,s+214)',
    'q_hi2=min(int(end)-157,p+214)',
    's_hi2=min(int(end)-157,q2+214)',
    "globals()['_RICH_COMPACT_TAIL_BOUND_V161']=1",
]:assert token in cpy,token
for stale in [
    'q_hi=min(int(end)-213,p+214)',
    's_hi=min(int(end)-213,q+214)',
    't_hi=min(int(end)-213,s+214)',
    'q_hi2=min(int(end)-158,p+214)',
    's_hi2=min(int(end)-158,q2+214)',
]:assert stale not in cpy,stale
print('v161 makes compact-stride searches include a fully readable player beginning exactly 158 bytes before the payload end; evidence and fixture gates unchanged')
