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

# v152 fixes a tail-loss defect in the proven 145..157-byte core-only representation.
# v150 proves a compact serialization using current row + THREE future rows. Requiring that same
# four-row look-ahead independently at every position means the final three players of every valid
# short-stride run can never take the v150 path. v151 made failed full-parser rows reachable, but it
# still inherits that forward-proof requirement. Once a stride has already been proved by four
# distinct valid core records, safely CONTINUE that exact stride through subsequent valid core rows
# until it physically breaks. This lets the last 1..3 rows survive without weakening initial proof.
for token in [
    'def _v150_core_record_at(raw,p):',
    'def _v150_core_stride_next(raw,p,end):',
    "globals()['_RICH_CORE_UNRATED_RESCUES_V151']",
    "_v150_pair=(r,_v151_nxt) if _v151_nxt is not None else _v150_core_stride_next(",
    'def _v131_scan_stats(raw,start,end):',
]:
    if token not in py:raise RuntimeError('v152 prerequisite missing: '+token)

helper="""
def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):
    try:d=int(stride)
    except Exception:return None
    if not (145<=d<=157):return None
    r=_v150_core_record_at(raw,p)
    if not r:return None
    pid=int(r.get('player_id',0) or 0)
    if pid<=0 or (last_pid is not None and pid==int(last_pid)):return None
    q=p+d
    # Current row is still valid even when it is the final record. Return next=None so the scanner
    # appends it, then leaves proven-stride mode instead of demanding three impossible successors.
    if q+145>int(end):return r,None
    nr=_v150_core_record_at(raw,q)
    npid=int(nr.get('player_id',0) or 0) if nr else 0
    if not nr or npid<=0 or npid==pid:return r,None
    return r,q

"""
if 'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):' not in py:
    anchor='def _v150_core_stride_next(raw,p,end):'
    pos=py.find(anchor)
    if pos<0:raise RuntimeError('v152 helper insertion anchor missing')
    py=py[:pos]+helper+py[pos:]


def patch_scanner(block:str,raw_name:str,end_name:str,state_counter:str,tail_counter:str)->str:
    if f"globals()['{state_counter}']" in block:return block
    # Core-only objects need only the proven 145-byte core to remain. The normal/full parser still
    # self-rejects when <158 bytes remain, so this only makes a previously-proved core tail reachable.
    old_loop=f'while p+158<={end_name}:'
    if old_loop not in block:raise RuntimeError('v152 158-byte loop bound missing')
    block=block.replace(old_loop,"_v152_core_stride=None\n    _v152_core_last_pid=None\n    while p+145<="+end_name+':',1)

    # Locate the normal parser assignment and override it only while an already-proven v150 stride
    # is active. This prevents optional bytes from the next compact object contaminating the row.
    pat=re.compile(r'(?m)^(\s*)r=_rich_stat_record_at\(([^\n]+)\)$')
    mm=pat.search(block)
    if not mm:raise RuntimeError('v152 parser assignment missing')
    indent=mm.group(1)
    injected=(mm.group(0)+"\n"+
        indent+"_v152_state_pair=None\n"+
        indent+"if _v152_core_stride is not None:\n"+
        indent+f"    _v152_state_pair=_v152_core_stride_continue({raw_name},p,{end_name},_v152_core_stride,_v152_core_last_pid)\n"+
        indent+"    if _v152_state_pair is not None:\n"+
        indent+"        r,_v152_state_nxt=_v152_state_pair\n"+
        indent+f"        globals()['{state_counter}']=int(globals().get('{state_counter}',0))+1\n"+
        indent+"    else:\n"+
        indent+"        _v152_core_stride=None\n"+
        indent+"        _v152_core_last_pid=None")
    block=block[:mm.start()]+injected+block[mm.end():]

    old=f"_v150_pair=(r,_v151_nxt) if _v151_nxt is not None else _v150_core_stride_next({raw_name},p,{end_name})"
    new=("_v150_pair=(r,_v152_state_nxt) if _v152_state_pair is not None else "
         f"((r,_v151_nxt) if _v151_nxt is not None else _v150_core_stride_next({raw_name},p,{end_name}))")
    if old not in block:raise RuntimeError('v152 v150 pair expression missing')
    block=block.replace(old,new,1)

    # Once the existing strict four-record proof finds a 145..157 stride, retain that exact stride
    # for tail continuation. Initial authority still comes exclusively from v150.
    needle='                if _v150_pair is not None:\n'
    idx=block.find(needle)
    if idx<0:raise RuntimeError('v152 v150 success branch missing')
    ins=(needle+
         "                    if _v152_core_stride is None and _v151_nxt is None and _v152_state_pair is None:\n"
         "                        _v152_candidate_stride=int(_v150_pair[1])-int(p) if _v150_pair[1] is not None else 0\n"
         "                        if 145<=_v152_candidate_stride<=157:\n"
         "                            _v152_core_stride=_v152_candidate_stride\n")
    block=block[:idx]+ins+block[idx+len(needle):]

    # Track current PID whenever the row is accepted in proven-stride mode, and count final rows
    # that are now kept even though no future row exists to re-prove the chain.
    append_needle='                out.append(r)\n' if 'out.append(r)' in block else '                rows.append(r)\n'
    if append_needle not in block:raise RuntimeError('v152 append anchor missing')
    append_extra=(append_needle+
        "                if _v152_state_pair is not None:\n"
        "                    _v152_core_last_pid=int(r.get('player_id',0) or 0)\n"
        "                    if _v152_state_nxt is None:\n"
        f"                        globals()['{tail_counter}']=int(globals().get('{tail_counter}',0))+1\n"
        "                        _v152_core_stride=None\n")
    block=block.replace(append_needle,append_extra,1)
    return block

# Global scanner containing v138 marker.
pos=py.find("globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1")
if pos<0:raise RuntimeError('v152 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
g=py[fs:fe]
fm=re.match(r'def\s+\w+\(([^)]*)\):',g)
if not fm:raise RuntimeError('v152 global scanner signature unreadable')
params=[x.strip().split('=')[0].strip() for x in fm.group(1).split(',')]
if len(params)<3:raise RuntimeError('v152 expected raw,start,end scanner')
g=patch_scanner(g,params[0],params[2],'_RICH_CORE_STRIDE_CONTINUATIONS_V152','_RICH_CORE_STRIDE_TAIL_ROWS_V152')
py=py[:fs]+g+py[fe:]

# Header-first scanner receives identical stateful tail continuation.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v152 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
h=py[hs:he]
h=patch_scanner(h,'raw','end','_RICH_HEADER_CORE_STRIDE_CONTINUATIONS_V152','_RICH_HEADER_CORE_STRIDE_TAIL_ROWS_V152')
py=py[:hs]+h+py[he:]

# Export evidence for the next real hard-save rerun.
if 'unlabelled_rich_core_stride_tail_rows_v152' not in py:
    anchors=[
        "'unlabelled_rich_core_unrated_rescues_v151':int(globals().get('_RICH_CORE_UNRATED_RESCUES_V151',0)),",
        "'unlabelled_rich_core_stride_max_bytes_v150':int(globals().get('_RICH_CORE_STRIDE_MAX_V150',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_stride_continuations_v152':int(globals().get('_RICH_CORE_STRIDE_CONTINUATIONS_V152',0)),"+
          "'unlabelled_rich_header_core_stride_continuations_v152':int(globals().get('_RICH_HEADER_CORE_STRIDE_CONTINUATIONS_V152',0)),"+
          "'unlabelled_rich_core_stride_tail_rows_v152':int(globals().get('_RICH_CORE_STRIDE_TAIL_ROWS_V152',0)),"+
          "'unlabelled_rich_header_core_stride_tail_rows_v152':int(globals().get('_RICH_HEADER_CORE_STRIDE_TAIL_ROWS_V152',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
    'while p+145<=',
    "globals()['_RICH_CORE_STRIDE_CONTINUATIONS_V152']",
    "globals()['_RICH_HEADER_CORE_STRIDE_CONTINUATIONS_V152']",
    "globals()['_RICH_CORE_STRIDE_TAIL_ROWS_V152']",
    "globals()['_RICH_HEADER_CORE_STRIDE_TAIL_ROWS_V152']",
    'def _v150_core_stride_next(raw,p,end):',
    "globals()['_RICH_CORE_UNRATED_RESCUES_V151']",
]:assert token in cpy,token
print('v152 carries an already-proven 145..157-byte core-only stride through its final rows instead of demanding three impossible future records at every position')
