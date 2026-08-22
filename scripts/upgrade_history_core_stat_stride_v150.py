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

# v150 targets the remaining object-spacing range deliberately excluded by v148: 145..157 bytes.
# Original FM reverse-engineering established a 145-byte fixed GAME_MATCH_PLAYER_STATS core. The
# current full parser also consumes optional/extended counters through byte 157, so simply running
# that parser on a <158-byte physical object would read bytes belonging to the next player object.
#
# Add a CORE-ONLY representation instead: copy exactly the proven 145-byte core into a temporary
# 158-byte buffer, zero the optional 145..157 tail, and reuse the existing validated parser. This
# preserves all fantasy-critical core stats while guaranteeing that one player's tail can never be
# read from the next object. A shorter physical stride is accepted only when FOUR distinct player
# records form one unique, near-stable 145..157-byte chain. Normal 214 spacing and v148's 158..213
# compact representation remain first-class paths.
for prereq in [
    'def _rich_stat_record_at(',
    'if p+158>len(buf) or buf[p]!=2:return None',
    'def _v148_compact_stride_next(raw,p,end):',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
    'def _v131_scan_stats(raw,start,end):',
]:
    if prereq not in py:raise RuntimeError('v150 prerequisite missing: '+prereq)

helper="""
def _v150_core_record_at(raw,p):
    p=int(p)
    if p<0 or p+145>len(raw) or raw[p]!=2:return None
    # Never expose bytes 145..157 from the following object to the full parser. The original
    # reverse-engineering proved bytes 0..144 as the fixed record core; optional extended counters
    # are deliberately zero-filled for this alternate physical serialization.
    tmp=bytes(raw[p:p+145])+bytes(13)
    r=_rich_stat_record_at(tmp,0)
    if not r:return None
    r=dict(r);r['offset']=p;r['core_only_v150']=True
    return r


def _v150_core_stride_next(raw,p,end):
    r0=_v150_core_record_at(raw,p)
    if not r0:return None
    pid0=int(r0.get('player_id',0) or 0)
    if pid0<=0:return None
    hits=[]
    q_hi=min(int(end)-144,p+158)
    for q in range(p+145,q_hi):
        if raw[q]!=2:continue
        r1=_v150_core_record_at(raw,q)
        if not r1:continue
        pid1=int(r1.get('player_id',0) or 0)
        if pid1<=0 or pid1==pid0:continue
        d1=q-p
        succ2=[]
        s_hi=min(int(end)-144,q+158)
        for s in range(q+145,s_hi):
            if raw[s]!=2:continue
            d2=s-q
            if abs(d2-d1)>4:continue
            r2=_v150_core_record_at(raw,s)
            if not r2:continue
            pid2=int(r2.get('player_id',0) or 0)
            if pid2<=0 or pid2 in (pid0,pid1):continue
            succ3=[]
            t_hi=min(int(end)-144,s+158)
            for t in range(s+145,t_hi):
                if raw[t]!=2:continue
                d3=t-s
                if abs(d3-d1)>4 or abs(d3-d2)>4:continue
                r3=_v150_core_record_at(raw,t)
                if not r3:continue
                pid3=int(r3.get('player_id',0) or 0)
                if pid3<=0 or pid3 in (pid0,pid1,pid2):continue
                succ3.append(t)
            if len(succ3)==1:succ2.append((s,succ3[0]))
        if len(succ2)==1:hits.append((q,succ2[0][0],succ2[0][1],d1))
    # Never choose between competing compact serialisations.
    if len(hits)!=1:return None
    q,s,t,d=hits[0]
    globals()['_RICH_CORE_STRIDE_MIN_V150']=min(int(globals().get('_RICH_CORE_STRIDE_MIN_V150',999999)),int(d))
    globals()['_RICH_CORE_STRIDE_MAX_V150']=max(int(globals().get('_RICH_CORE_STRIDE_MAX_V150',0)),int(d))
    return r0,q

"""
if 'def _v150_core_record_at(raw,p):' not in py:
    anchor='def _v148_compact_stride_next(raw,p,end):'
    pos=py.find(anchor)
    if pos<0:raise RuntimeError('v150 helper insertion anchor missing')
    py=py[:pos]+helper+py[pos:]

# Patch original/global scanner. Detect the proven <158-byte serialization BEFORE appending the
# full-parser row, replace that row with its core-only version, then advance to the proven next
# object. If no unique v150 chain exists, v148 and normal +214 behaviour remain unchanged.
marker="globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1"
pos=py.find(marker)
if pos<0:raise RuntimeError('v150 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
gblock=py[fs:fe]
fm=re.match(r'def\s+\w+\(([^)]*)\):',gblock)
if not fm:raise RuntimeError('v150 global scanner signature unreadable')
params=[x.strip().split('=')[0].strip() for x in fm.group(1).split(',')]
if len(params)<3:raise RuntimeError('v150 expected raw,start,end global scanner')
raw_name,end_name=params[0],params[2]
if "_RICH_CORE_STRIDE_TRANSITIONS_V150" not in gblock:
    needle="""            if r:
                out.append(r)
"""
    if needle not in gblock:raise RuntimeError('v150 global append anchor missing')
    repl=("            if r:\n"
          "                _v150_pair=_v150_core_stride_next("+raw_name+",p,"+end_name+")\n"
          "                _v150_nxt=None\n"
          "                if _v150_pair is not None:\n"
          "                    r,_v150_nxt=_v150_pair\n"
          "                    globals()['_RICH_CORE_STRIDE_TRANSITIONS_V150']=int(globals().get('_RICH_CORE_STRIDE_TRANSITIONS_V150',0))+1\n"
          "                out.append(r)\n")
    gblock=gblock.replace(needle,repl,1)
    # Insert v150 advance immediately before v148 compact-stride rescue/default +214 logic.
    adv="""                _v148_nxt=_v148_compact_stride_next("""
    idx=gblock.find(adv)
    if idx<0:raise RuntimeError('v150 global v148 advance anchor missing')
    ins=("                if _v150_nxt is not None:\n"
         "                    p=_v150_nxt;continue\n")
    gblock=gblock[:idx]+ins+gblock[idx:]
py=py[:fs]+gblock+py[fe:]

# Patch header-first scanner identically. The direct-header path therefore cannot lose an entire
# historical game merely because its player objects use the shorter core-only serialization.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v150 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
hblock=py[hs:he]
if "_RICH_HEADER_CORE_STRIDE_TRANSITIONS_V150" not in hblock:
    needle="""            if r:
                rows.append(r)
"""
    if needle not in hblock:raise RuntimeError('v150 header append anchor missing')
    repl=("            if r:\n"
          "                _v150_pair=_v150_core_stride_next(raw,p,end)\n"
          "                _v150_nxt=None\n"
          "                if _v150_pair is not None:\n"
          "                    r,_v150_nxt=_v150_pair\n"
          "                    globals()['_RICH_HEADER_CORE_STRIDE_TRANSITIONS_V150']=int(globals().get('_RICH_HEADER_CORE_STRIDE_TRANSITIONS_V150',0))+1\n"
          "                rows.append(r)\n")
    hblock=hblock.replace(needle,repl,1)
    adv='                _v148_nxt=_v148_compact_stride_next(raw,p,end)'
    idx=hblock.find(adv)
    if idx<0:raise RuntimeError('v150 header v148 advance anchor missing')
    ins=("                if _v150_nxt is not None:\n"
         "                    p=_v150_nxt;continue\n")
    hblock=hblock[:idx]+ins+hblock[idx:]
py=py[:hs]+hblock+py[he:]

# Export evidence. These counters let the next hard-save run immediately prove or rule out the
# 145..157-byte object family without affecting acceptance itself.
if 'unlabelled_rich_core_stride_transitions_v150' not in py:
    anchors=[
        "'unlabelled_rich_header_tail_records_v149':int(globals().get('_RICH_HEADER_TAIL_RECORDS_V149',0)),",
        "'unlabelled_rich_compact_stride_max_bytes_v148':int(globals().get('_RICH_COMPACT_STRIDE_MAX_V148',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_transitions_v150':int(globals().get('_RICH_CORE_STRIDE_TRANSITIONS_V150',0)),"+
          "'unlabelled_rich_header_core_stride_transitions_v150':int(globals().get('_RICH_HEADER_CORE_STRIDE_TRANSITIONS_V150',0)),"+
          "'unlabelled_rich_core_stride_min_bytes_v150':int(globals().get('_RICH_CORE_STRIDE_MIN_V150',0) if int(globals().get('_RICH_CORE_STRIDE_MIN_V150',999999))<999999 else 0),"+
          "'unlabelled_rich_core_stride_max_bytes_v150':int(globals().get('_RICH_CORE_STRIDE_MAX_V150',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v150_core_record_at(raw,p):',
    'tmp=bytes(raw[p:p+145])+bytes(13)',
    'def _v150_core_stride_next(raw,p,end):',
    'for q in range(p+145,q_hi):',
    'if abs(d2-d1)>4:continue',
    "globals()['_RICH_CORE_STRIDE_TRANSITIONS_V150']",
    "globals()['_RICH_HEADER_CORE_STRIDE_TRANSITIONS_V150']",
    'def _v148_compact_stride_next(raw,p,end):',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:assert token in cpy,token
print('v150 adds a collision-safe 145..157-byte core-only GAME_MATCH_PLAYER_STATS stride path without reading optional tail bytes from the next player object')
