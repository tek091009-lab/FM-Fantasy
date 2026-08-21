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

# v151 fixes a reachability hole in v150. v150 correctly added a core-only decoder for physical
# GAME_MATCH_PLAYER_STATS objects spaced 145..157 bytes apart, but both scanners only asked v150
# for help AFTER the normal >=158-byte parser had already returned a row. That fails for an important
# real representation: an unused substitute can have rating_raw==0 and no activity in its own
# 145-byte core, while bytes 145..157 physically belong to the NEXT player object. The normal parser
# reads those next-player bytes as this row's optional tail; v125's strict unrated-inactive guard can
# therefore reject the row before v150 is ever consulted.
#
# Try the independently isolated v150 core chain whenever the full parser FAILS. A shorter row is
# accepted only when v150 already proves one unique four-player 145..157-byte serialization. This
# does not lower the player-row validator or fixture matcher; it merely makes the existing core-only
# representation reachable for zero-rated/unused historical bench rows.
for token in [
    'def _v150_core_record_at(raw,p):',
    'def _v150_core_stride_next(raw,p,end):',
    "'unrated_inactive_candidate':bool(unrated_inactive)",
    "globals()['_RICH_CORE_STRIDE_TRANSITIONS_V150']",
    'def _v131_scan_stats(raw,start,end):',
]:
    if token not in py:raise RuntimeError('v151 prerequisite missing: '+token)


def patch_scanner(block:str, raw_name:str, end_name:str, counter:str)->str:
    marker=f"globals()['{counter}']"
    if marker in block:return block
    # Both scanners evaluate `r` immediately before the existing `if r:` append path. Insert an
    # independent core-only rescue before that branch, then let the existing v150 append/advance
    # logic continue unchanged.
    needle='            if r:\n'
    idx=block.find(needle)
    if idx<0:raise RuntimeError('v151 scanner `if r` anchor missing')
    pre=("            _v151_nxt=None\n"
         "            if not r:\n"
         f"                _v151_pair=_v150_core_stride_next({raw_name},p,{end_name})\n"
         "                if _v151_pair is not None:\n"
         "                    r,_v151_nxt=_v151_pair\n"
         f"                    globals()['{counter}']=int(globals().get('{counter}',0))+1\n")
    block=block[:idx]+pre+block[idx:]
    # Avoid re-proving the same chain inside v150 after the v151 rescue. Reuse its next offset.
    old=f"                _v150_pair=_v150_core_stride_next({raw_name},p,{end_name})\n"
    new=(f"                _v150_pair=(r,_v151_nxt) if _v151_nxt is not None else "
         f"_v150_core_stride_next({raw_name},p,{end_name})\n")
    if old not in block:raise RuntimeError('v151 v150 pair anchor missing')
    return block.replace(old,new,1)

# Global retained-stat scanner: locate the function containing the v138 non-overlap marker.
pos=py.find("globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1")
if pos<0:raise RuntimeError('v151 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
g=py[fs:fe]
fm=re.match(r'def\s+\w+\(([^)]*)\):',g)
if not fm:raise RuntimeError('v151 global scanner signature unreadable')
params=[x.strip().split('=')[0].strip() for x in fm.group(1).split(',')]
if len(params)<3:raise RuntimeError('v151 expected raw,start,end global scanner')
g=patch_scanner(g,params[0],params[2],'_RICH_CORE_UNRATED_RESCUES_V151')
py=py[:fs]+g+py[fe:]

# Header-first scanner: same rescue, because a header-anchored old game can otherwise lose its
# unused bench rows and fail side reconstruction despite having a valid binary match header.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v151 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
h=py[hs:he]
h=patch_scanner(h,'raw','end','_RICH_HEADER_CORE_UNRATED_RESCUES_V151')
py=py[:hs]+h+py[he:]

# Export explicit evidence so the next hard-save rerun can tell whether this exact representation
# exists instead of folding it into the broader v150 counter.
if 'unlabelled_rich_core_unrated_rescues_v151' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_max_bytes_v150':int(globals().get('_RICH_CORE_STRIDE_MAX_V150',0)),",
        "'unlabelled_rich_core_stride_transitions_v150':int(globals().get('_RICH_CORE_STRIDE_TRANSITIONS_V150',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_unrated_rescues_v151':int(globals().get('_RICH_CORE_UNRATED_RESCUES_V151',0)),"+
          "'unlabelled_rich_header_core_unrated_rescues_v151':int(globals().get('_RICH_HEADER_CORE_UNRATED_RESCUES_V151',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "if not r:\n                _v151_pair=_v150_core_stride_next(",
    "globals()['_RICH_CORE_UNRATED_RESCUES_V151']",
    "globals()['_RICH_HEADER_CORE_UNRATED_RESCUES_V151']",
    "_v150_pair=(r,_v151_nxt) if _v151_nxt is not None else _v150_core_stride_next(",
    'def _v150_core_record_at(raw,p):',
    'tmp=bytes(raw[p:p+145])+bytes(13)',
]:assert token in cpy,token
print('v151 makes the proven 145..157-byte core-only row decoder reachable when the full parser fails on next-player tail contamination, including unrated inactive bench rows')
