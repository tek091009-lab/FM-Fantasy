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

# v163 narrows v162's quarantine. v162 correctly observed that +146
# team_goals_conceded_while_on_pitch is outside the proven 145-byte core, so a true
# 145/146-byte object cannot safely expose it. But v150's physical family is 145..157 bytes.
# When a stride is >=147, byte +146 is physically BEFORE the next player object and therefore
# is not borrowed from the following record. Preserve v162 for true 145/146-byte objects, but
# recover exact +146 goals-conceded for uniquely-proven 147..157-byte strides.
for token in [
    'def _v150_core_record_at(raw,p):',
    'def _v150_core_stride_next(raw,p,end):',
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
    'def _v155_prepare_core_fantasy_row(r):',
    "r['historical_fantasy_core_complete_v162']=False",
    "r['core_missing_fantasy_field_v162']='team_goals_conceded_while_on_pitch'",
]:
    if token not in py:raise RuntimeError('v163 prerequisite missing: '+token)

helper="""
def _v163_apply_physical_gc(raw,p,end,stride,r):
    # Only trust +146 when the proven physical object extends through that byte.
    # v150 already supplies the hard part: one unique, repeated 145..157-byte serialization.
    try:d=int(stride)
    except Exception:return r
    r=dict(r)
    r['core_physical_stride_v163']=d
    if not (147<=d<=157):return r
    lim=min(len(raw),int(end))
    if int(p)+147>lim:return r
    gc=int(raw[int(p)+146])
    # One-byte goals-conceded count should remain football-plausible. Reject impossible tail
    # values rather than promoting a schema whose +146 semantics have clearly changed.
    if not (0<=gc<=20):
        r['core_gc_tail_rejected_v163']=gc
        return r
    r['core_exact_goals_conceded_v163']=gc
    r['core_gc_available_v163']=True
    return r

"""
if 'def _v163_apply_physical_gc(raw,p,end,stride,r):' not in py:
    pos=py.find('def _v150_core_stride_next(raw,p,end):')
    if pos<0:raise RuntimeError('v163 helper insertion anchor missing')
    py=py[:pos]+helper+py[pos:]

# Initial four-record proof: once d is uniquely proven, annotate the current row with +146 if
# the physical object is long enough. This affects both normal v150 use and v151 rescue use.
start=py.find('def _v150_core_stride_next(raw,p,end):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]
if '_v163_apply_physical_gc(raw,p,end,d,r0)' not in block:
    needle="    return r0,q\n"
    if needle not in block:raise RuntimeError('v163 v150 return anchor missing')
    block=block.replace(needle,"    r0=_v163_apply_physical_gc(raw,p,end,d,r0)\n    return r0,q\n",1)
    py=py[:start]+block+py[end:]

# Stateful v152 continuation: the stride is already proven by v150, so every following short-stride
# row can recover +146 under the same physical rule. Final truncated rows still self-quarantine if
# fewer than 147 bytes remain.
start=py.find('def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]
if '_v163_apply_physical_gc(raw,p,end,d,r)' not in block:
    needle="    r=_v150_core_record_at(raw,p)\n"
    if needle not in block:raise RuntimeError('v163 v152 row anchor missing')
    block=block.replace(needle,needle+"    r=_v163_apply_physical_gc(raw,p,end,d,r) if r else r\n",1)
    py=py[:start]+block+py[end:]

# v162 truth policy: retain its strict inactive-row path and its quarantine for true missing-GC
# rows, but promote an ACTIVE row when v163 has exact +146 data from inside a proven >=147-byte
# object. Extended non-fantasy diagnostics remain unavailable/None exactly as before.
start=py.find('def _v155_prepare_core_fantasy_row(r):')
end=py.find('\ndef ',start+1)
if start<0 or end<0:raise RuntimeError('v163 v162 truth helper boundaries missing')
block=py[start:end]
if "core_gc_available_v163" not in block:
    old=("    else:\n"
         "        # +146 is not physically present in the proven 145-byte core. Never turn its zero-fill into\n"
         "        # a real goals-conceded value for an active player.\n"
         "        r['goals_conceded']=None\n")
    if old not in block:raise RuntimeError('v163 v162 active quarantine anchor missing')
    new=("    elif bool(r.get('core_gc_available_v163')):\n"
         "        # v163: +146 is physically inside a uniquely-proven 147..157-byte object.\n"
         "        gc=int(r.get('core_exact_goals_conceded_v163',0) or 0)\n"
         "        r['team_goals_conceded_while_on_pitch']=gc\n"
         "        r['goals_conceded']=gc\n"
         "        r['core_exact_goals_conceded_v155']=gc\n"
         "        r['historical_fantasy_core_complete_v155']=True\n"
         "        r['historical_fantasy_core_complete_v162']=True\n"
         "        r['historical_fantasy_core_complete_v163']=True\n"
         "        r['core_stat_policy_v163']='exact core stats + physically present +146 goals-conceded'\n"
         "    else:\n"
         "        # True 145/146-byte objects (or a truncated final row) still lack +146.\n"
         "        r['goals_conceded']=None\n")
    block=block.replace(old,new,1)
    # Preserve an explicit v163 false flag on rows still missing GC.
    needle="        r['historical_fantasy_core_complete_v162']=False\n"
    if needle in block:
        block=block.replace(needle,needle+"        r['historical_fantasy_core_complete_v163']=False\n",1)
    py=py[:start]+block+py[end:]

# Export evidence so the next hard-save rerun can tell exactly how much of the short-stride family
# is 147..157 (potentially recoverable) versus true 145/146-byte incomplete rows.
if 'unlabelled_rich_core_gc_recovered_v163' not in py:
    anchors=[
        "'unlabelled_rich_core_active_quarantined_v162':int(globals().get('_RICH_CORE_ACTIVE_QUARANTINED_V162',0)),",
        "'unlabelled_rich_core_stride_max_bytes_v150':int(globals().get('_RICH_CORE_STRIDE_MAX_V150',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_gc_recovered_v163':int(globals().get('_RICH_CORE_GC_RECOVERED_V163',0)),"+
          "'unlabelled_rich_header_core_gc_recovered_v163':int(globals().get('_RICH_HEADER_CORE_GC_RECOVERED_V163',0)),")
        py=py.replace(anchor,extra,1)

# Count promotion at the two existing prepare call sites without changing scanner authority.
needle="                    r=_v155_prepare_core_fantasy_row(r)\n"
if py.count(needle)>=2 and "_RICH_CORE_GC_RECOVERED_V163" not in py[py.find(needle):]:
    # Distinguish global/header by the same locals-based convention v162 already uses.
    repl=(needle+
      "                    if bool(r.get('historical_fantasy_core_complete_v163')) and bool(r.get('core_gc_available_v163')):\n"
      "                        _v163_is_header=('rows' in locals() and isinstance(locals().get('rows'),list))\n"
      "                        _v163_key='_RICH_HEADER_CORE_GC_RECOVERED_V163' if _v163_is_header else '_RICH_CORE_GC_RECOVERED_V163'\n"
      "                        globals()[_v163_key]=int(globals().get(_v163_key,0))+1\n")
    py=py.replace(needle,repl)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
    '147<=d<=157',
    "r['core_exact_goals_conceded_v163']=gc",
    '_v163_apply_physical_gc(raw,p,end,d,r0)',
    '_v163_apply_physical_gc(raw,p,end,d,r) if r else r',
    "elif bool(r.get('core_gc_available_v163')):",
    "r['historical_fantasy_core_complete_v163']=True",
    "'_RICH_CORE_GC_RECOVERED_V163'",
]:assert token in cpy,token
print('v163 recovers exact +146 goals-conceded only when it is physically inside a uniquely-proven 147..157-byte player object; true 145/146-byte active rows remain quarantined')
