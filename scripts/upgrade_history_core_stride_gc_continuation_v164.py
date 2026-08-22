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

# v164 fixes a reachability bug between v153 and v163.
# v153 replaced both scanner calls to _v152_core_stride_continue() with the stricter
# _v153_core_stride_continue() so whole-run PID uniqueness could be enforced. v163 later added
# stride-aware +146 goals-conceded recovery to _v152_core_stride_continue(), but that helper is no
# longer called by the live scanner after v153. Result: v163 can recover +146 on rows that can still
# freshly prove a four-record v150 chain, but the final 1..3 ACTIVE rows that depend on v153's
# stateful continuation never receive core_gc_available_v163 and are quarantined by v162.
#
# Patch the actually-live v153 continuation helper. This does not alter stride proof, player
# identity, side construction, score matching or fixture acceptance; it only applies v163's already
# validated physical-byte rule to continuation rows that v153 has already admitted.
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    'def _v163_apply_physical_gc(raw,p,end,stride,r):',
    "elif bool(r.get('core_gc_available_v163')):",
    '_v153_core_stride_continue(',
]:
    if token not in py:raise RuntimeError('v164 prerequisite missing: '+token)

start=py.find('def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]

if "core_gc_continuation_v164" not in block:
    needle="    r=_v150_core_record_at(raw,p)\n"
    if needle not in block:raise RuntimeError('v164 v153 row anchor missing')
    repl=(needle+
          "    r=_v163_apply_physical_gc(raw,p,end,d,r) if r else r\n"+
          "    if r and bool(r.get('core_gc_available_v163')):\n"+
          "        r['core_gc_continuation_v164']=True\n")
    block=block.replace(needle,repl,1)
    py=py[:start]+block+py[end:]

# Count rows that become fantasy-complete specifically because the live v153 continuation now gets
# v163's exact +146 byte. Count after the existing v155/v162/v163 truth preparation at both scanner
# call sites; this avoids counting structurally-seen rows that are later rejected for another reason.
needle="                    r=_v155_prepare_core_fantasy_row(r)\n"
if py.count(needle)<2:raise RuntimeError('v164 expected two core truth preparation call sites')
marker="_RICH_CORE_GC_CONTINUATION_RECOVERED_V164"
if marker not in py:
    repl=(needle+
          "                    if bool(r.get('core_gc_continuation_v164')) and bool(r.get('historical_fantasy_core_complete_v163')):\n"+
          "                        _v164_is_header=('rows' in locals() and isinstance(locals().get('rows'),list))\n"+
          "                        _v164_key='_RICH_HEADER_CORE_GC_CONTINUATION_RECOVERED_V164' if _v164_is_header else '_RICH_CORE_GC_CONTINUATION_RECOVERED_V164'\n"+
          "                        globals()[_v164_key]=int(globals().get(_v164_key,0))+1\n")
    py=py.replace(needle,repl)

# Export direct evidence for the next raw-save rerun.
if 'unlabelled_rich_core_gc_continuation_recovered_v164' not in py:
    anchors=[
        "'unlabelled_rich_core_gc_recovered_v163':int(globals().get('_RICH_CORE_GC_RECOVERED_V163',0)),",
        "'unlabelled_rich_core_active_quarantined_v162':int(globals().get('_RICH_CORE_ACTIVE_QUARANTINED_V162',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_gc_continuation_recovered_v164':int(globals().get('_RICH_CORE_GC_CONTINUATION_RECOVERED_V164',0)),"+
          "'unlabelled_rich_header_core_gc_continuation_recovered_v164':int(globals().get('_RICH_HEADER_CORE_GC_CONTINUATION_RECOVERED_V164',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v153_core_stride_continue(raw,p,end,stride,seen_pids=None):',
    'r=_v163_apply_physical_gc(raw,p,end,d,r) if r else r',
    "r['core_gc_continuation_v164']=True",
    "'_RICH_CORE_GC_CONTINUATION_RECOVERED_V164'",
    "'_RICH_HEADER_CORE_GC_CONTINUATION_RECOVERED_V164'",
    "elif bool(r.get('core_gc_available_v163')):",
]:assert token in cpy,token
print('v164 applies v163 exact +146 goals-conceded recovery to the actually-live v153 short-stride continuation, preventing final active rows of proven 147..157-byte runs from being quarantined solely because they cannot re-prove four future records')