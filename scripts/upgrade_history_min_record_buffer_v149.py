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

# v149 fixes a concrete retained-stat truncation bug. The live GAME_MATCH_PLAYER_STATS parser only
# reads mapped bytes through offset 157, so 158 bytes from the record start are sufficient to decode
# every field it currently consumes. Nevertheless the parser and both scanners still require 214
# bytes to remain. That can discard a valid final player row close to the end of a retained payload
# and leave an otherwise complete side short. Keep the existing 214-byte normal object-spacing path
# and v148 compact-stride logic; only lower the MINIMUM readable record buffer to the actual 158 bytes.
for prereq in [
    'def _rich_stat_record_at(',
    'def _v131_scan_stats(raw,start,end):',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
    'def _v148_compact_stride_next(raw,p,end):',
    "globals()['_RICH_COMPACT_STRIDE_TRANSITIONS_V148']",
]:
    if prereq not in py:raise RuntimeError('v149 prerequisite missing: '+prereq)

# Patch only the live stat-record parser containing the known rating mapping at offset 136.
rs=py.find('def _rich_stat_record_at(')
if rs<0:raise RuntimeError('v149 rich stat parser not found')
re_=py.find('\ndef ',rs+1)
if re_<0:re_=len(py)
rblock=py[rs:re_]
old_guard='if p+214>len(buf) or buf[p]!=2:return None'
new_guard='if p+158>len(buf) or buf[p]!=2:return None'
if new_guard not in rblock:
    if old_guard not in rblock:raise RuntimeError('v149 214-byte parser guard not found')
    rblock=rblock.replace(old_guard,new_guard,1)
py=py[:rs]+rblock+py[re_:]

# Patch the original/global retained scanner loop bound inside the v138-marked scanner only.
marker="globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1"
pos=py.find(marker)
if pos<0:raise RuntimeError('v149 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
gblock=py[fs:fe]
changed=False
for old,new in [
    ('while p<end-214:','while p+158<=end:'),
    ('while p+214<=end:','while p+158<=end:'),
]:
    if old in gblock:
        gblock=gblock.replace(old,new,1);changed=True;break
if not changed and 'while p+158<=end:' not in gblock:
    raise RuntimeError('v149 global scanner 214-byte loop bound not found')
# Count rows that would previously have been dropped solely because fewer than 214 bytes remain
# inside this scanner window. This is evidence-only and does not affect matching.
if "_RICH_TAIL_RECORDS_V149" not in gblock:
    needle='out.append(r)\n'
    if needle not in gblock:raise RuntimeError('v149 global append anchor missing')
    repl=(needle+
          "                if p+214>"+re.match(r'def\s+\w+\(([^)]*)\):',gblock).group(1).split(',')[2].split('=')[0].strip()+":\n"
          "                    globals()['_RICH_TAIL_RECORDS_V149']=int(globals().get('_RICH_TAIL_RECORDS_V149',0))+1\n")
    gblock=gblock.replace(needle,repl,1)
py=py[:fs]+gblock+py[fe:]

# Patch the header-first scanner's loop bound. Its normal accepted-record advance remains +214 unless
# v148 proves a compact stride; only the final readable-row boundary changes to 158.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v149 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
hblock=py[hs:he]
if 'while p+158<=end:' not in hblock:
    if 'while p+214<=end:' in hblock:hblock=hblock.replace('while p+214<=end:','while p+158<=end:',1)
    elif 'while p<end-214:' in hblock:hblock=hblock.replace('while p<end-214:','while p+158<=end:',1)
    else:raise RuntimeError('v149 header scanner 214-byte loop bound not found')
if "_RICH_HEADER_TAIL_RECORDS_V149" not in hblock:
    needle='rows.append(r)\n'
    if needle not in hblock:raise RuntimeError('v149 header append anchor missing')
    hblock=hblock.replace(needle,needle+"                if p+214>end:\n                    globals()['_RICH_HEADER_TAIL_RECORDS_V149']=int(globals().get('_RICH_HEADER_TAIL_RECORDS_V149',0))+1\n",1)
py=py[:hs]+hblock+py[he:]

# v148's look-ahead windows also assumed 214 bytes had to remain for successor records. Once the
# parser's true readable minimum is 158, allow a compact-stride chain to include a final record near
# the payload end rather than ruling it out before validation.
for old,new in [
    ('q_hi=min(int(end)-213,p+214)','q_hi=min(int(end)-157,p+214)'),
    ('s_hi=min(int(end)-213,q+214)','s_hi=min(int(end)-157,q+214)'),
    ('t_hi=min(int(end)-213,s+214)','t_hi=min(int(end)-157,s+214)'),
]:
    if old in py:py=py.replace(old,new,1)
    elif new not in py:raise RuntimeError('v149 v148 look-ahead bound missing: '+old)

# Export evidence where the retained-history debug handoff is available.
if 'unlabelled_rich_tail_records_v149' not in py:
    anchors=[
        "'unlabelled_rich_compact_stride_max_bytes_v148':int(globals().get('_RICH_COMPACT_STRIDE_MAX_V148',0)),",
        "'unlabelled_rich_compact_stride_transitions_v148':int(globals().get('_RICH_COMPACT_STRIDE_TRANSITIONS_V148',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_tail_records_v149':int(globals().get('_RICH_TAIL_RECORDS_V149',0)),"+
          "'unlabelled_rich_header_tail_records_v149':int(globals().get('_RICH_HEADER_TAIL_RECORDS_V149',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'if p+158>len(buf) or buf[p]!=2:return None',
    'while p+158<=end:',
    "globals()['_RICH_TAIL_RECORDS_V149']",
    "globals()['_RICH_HEADER_TAIL_RECORDS_V149']",
    'q_hi=min(int(end)-157,p+214)',
    's_hi=min(int(end)-157,q+214)',
    't_hi=min(int(end)-157,s+214)',
    'def _v148_compact_stride_next(raw,p,end):',
]:assert token in cpy,token
print('v149 lowers retained GAME_MATCH_PLAYER_STATS readable buffer from 214 to the actual mapped 158 bytes while preserving 214 normal spacing and v148 compact-stride proof')
