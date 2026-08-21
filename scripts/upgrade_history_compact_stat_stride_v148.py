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

# v148 corrects a schema assumption introduced by v137/v138. The original FM26 reverse-engineering
# established that GAME_MATCH_PLAYER_STATS has a 145-byte fixed front/core section; 214 bytes was
# only the minimum spacing observed between consecutive objects in that particular save. Therefore
# blindly jumping +214 after every accepted row can skip a real next player object in another schema
# whose object spacing is shorter. Preserve the existing +214 path as the default, but add a bounded
# compact-stride rescue when the bytes themselves prove a repeated run of shorter records.
#
# To keep all currently consumed mapped fields (through byte 157) physically inside the object,
# v148 only rescues spacings 158..213. A shorter 145..157 representation needs a separate core-only
# field decoder rather than reading extended fields across the next object. Require FOUR distinct
# valid player rows (current + three successors) with nearly stable compact spacing before changing
# the scanner step. Ambiguous compact runs are rejected.
for prereq in [
    'def _rich_stat_record_at(',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
    'def _v131_scan_stats(raw,start,end):',
    'rows.append(r);p+=214;continue',
    'def _rich_candidate_squad_pairs(',
]:
    if prereq not in py:raise RuntimeError('v148 prerequisite missing: '+prereq)

helper="""
def _v148_compact_stride_next(raw,p,end):
    # Existing full parser remains authoritative. This helper only decides whether the next object
    # demonstrably begins before p+214. Four-row repeated evidence prevents re-entering arbitrary
    # bytes in the tail of one normal 214+-spaced record.
    r0=_rich_stat_record_at(raw,p)
    if not r0:return None
    pid0=int(r0.get('player_id',0) or 0)
    if pid0<=0:return None
    hits=[]
    q_hi=min(int(end)-213,p+214)
    for q in range(p+158,q_hi):
        if raw[q]!=2:continue
        r1=_rich_stat_record_at(raw,q)
        if not r1:continue
        pid1=int(r1.get('player_id',0) or 0)
        if pid1<=0 or pid1==pid0:continue
        d1=q-p
        succ2=[]
        s_hi=min(int(end)-213,q+214)
        for s in range(q+158,s_hi):
            if raw[s]!=2:continue
            d2=s-q
            if abs(d2-d1)>8:continue
            r2=_rich_stat_record_at(raw,s)
            if not r2:continue
            pid2=int(r2.get('player_id',0) or 0)
            if pid2<=0 or pid2 in (pid0,pid1):continue
            succ3=[]
            t_hi=min(int(end)-213,s+214)
            for t in range(s+158,t_hi):
                if raw[t]!=2:continue
                d3=t-s
                if abs(d3-d1)>8 or abs(d3-d2)>8:continue
                r3=_rich_stat_record_at(raw,t)
                if not r3:continue
                pid3=int(r3.get('player_id',0) or 0)
                if pid3<=0 or pid3 in (pid0,pid1,pid2):continue
                succ3.append(t)
            if len(succ3)==1:succ2.append((s,succ3[0]))
        if len(succ2)==1:hits.append((q,succ2[0][0],succ2[0][1],d1))
    # Do not choose between multiple possible compact serialisations.
    if len(hits)!=1:return None
    q,s,t,d=hits[0]
    globals()['_RICH_COMPACT_STRIDE_MIN_V148']=min(int(globals().get('_RICH_COMPACT_STRIDE_MIN_V148',999999)),int(d))
    globals()['_RICH_COMPACT_STRIDE_MAX_V148']=max(int(globals().get('_RICH_COMPACT_STRIDE_MAX_V148',0)),int(d))
    return q

"""
if 'def _v148_compact_stride_next(raw,p,end):' not in py:
    anchor='def _rich_candidate_squad_pairs('
    pos=py.find(anchor)
    if pos<0:raise RuntimeError('v148 helper insertion anchor missing')
    py=py[:pos]+helper+py[pos:]

# Patch the original/global retained scanner dynamically so we do not assume its raw/end parameter
# names. v138's marker uniquely identifies the intended scanner block.
marker="globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1"
pos=py.find(marker)
if pos<0:raise RuntimeError('v148 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fm=re.match(r'def\s+\w+\(([^)]*)\):',py[fs:])
if not fm:raise RuntimeError('v148 could not parse global scanner signature')
params=[x.strip().split('=')[0].strip() for x in fm.group(1).split(',')]
if len(params)<3:raise RuntimeError('v148 expected raw,start,end scanner signature')
raw_name,end_name=params[0],params[2]
old=marker+"\n                p+=214;continue"
new=(marker+"\n                _v148_nxt=_v148_compact_stride_next("+raw_name+",p,"+end_name+")\n"
     "                if _v148_nxt is not None:\n"
     "                    globals()['_RICH_COMPACT_STRIDE_TRANSITIONS_V148']=int(globals().get('_RICH_COMPACT_STRIDE_TRANSITIONS_V148',0))+1\n"
     "                    p=_v148_nxt;continue\n"
     "                p+=214;continue")
if "_RICH_COMPACT_STRIDE_TRANSITIONS_V148" not in py:
    if old not in py:raise RuntimeError('v148 global +214 scanner anchor missing')
    py=py.replace(old,new,1)

# Apply the same evidence-based rescue to the header-first scanner. Keep its normal +214 path when
# no uniquely proven compact run exists.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v148 header-first scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
hblock=py[hs:he]
hold='rows.append(r);p+=214;continue'
hnew=("rows.append(r)\n"
      "                _v148_nxt=_v148_compact_stride_next(raw,p,end)\n"
      "                if _v148_nxt is not None:\n"
      "                    globals()['_RICH_HEADER_COMPACT_STRIDE_TRANSITIONS_V148']=int(globals().get('_RICH_HEADER_COMPACT_STRIDE_TRANSITIONS_V148',0))+1\n"
      "                    p=_v148_nxt;continue\n"
      "                p+=214;continue")
if "_RICH_HEADER_COMPACT_STRIDE_TRANSITIONS_V148" not in py:
    if hold not in hblock:raise RuntimeError('v148 header-first +214 anchor missing')
    hblock=hblock.replace(hold,hnew,1)
    py=py[:hs]+hblock+py[he:]

# Export diagnostics into the existing retained-history debug payload when that handoff exists.
if 'unlabelled_rich_compact_stride_transitions_v148' not in py:
    anchor="'unlabelled_rich_dual_subgroup_contiguous_candidate_pairs':member_rich_diag.get('dual_subgroup_contiguous_candidate_pairs',0),"
    if anchor in py:
        extra=(anchor
          +"'unlabelled_rich_compact_stride_transitions_v148':int(globals().get('_RICH_COMPACT_STRIDE_TRANSITIONS_V148',0)),"
          +"'unlabelled_rich_header_compact_stride_transitions_v148':int(globals().get('_RICH_HEADER_COMPACT_STRIDE_TRANSITIONS_V148',0)),"
          +"'unlabelled_rich_compact_stride_min_bytes_v148':int(globals().get('_RICH_COMPACT_STRIDE_MIN_V148',0) if int(globals().get('_RICH_COMPACT_STRIDE_MIN_V148',999999))<999999 else 0),"
          +"'unlabelled_rich_compact_stride_max_bytes_v148':int(globals().get('_RICH_COMPACT_STRIDE_MAX_V148',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'for q in range(p+158,q_hi):',
    'if abs(d2-d1)>8:continue',
    'if len(hits)!=1:return None',
    "globals()['_RICH_COMPACT_STRIDE_TRANSITIONS_V148']",
    "globals()['_RICH_HEADER_COMPACT_STRIDE_TRANSITIONS_V148']",
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:assert token in cpy,token
print('v148 preserves normal +214 scanning but rescues uniquely proven repeated 158..213-byte GAME_MATCH_PLAYER_STATS object spacing')
