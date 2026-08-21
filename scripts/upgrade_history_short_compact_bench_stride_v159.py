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

# v159 targets a directly observed regression class after the global non-overlap scanner was
# tightened. The older 50-result Championship run detected ~25.7k stat rows and recovered 37/50;
# newer non-overlap-era runs detect ~1.6k rows and recover 33/50. v148 safely restores 158..213-byte
# physical GAME_MATCH_PLAYER_STATS spacing, but only when CURRENT + THREE successor rows prove a
# four-player chain. That proof is impossible for a compact subgroup containing only 2-3 bench rows.
#
# v159 preserves the four-row proof as first priority, then admits ONE shorter three-row physical
# chain only when the two successor rows independently behave like bench/substitute records. This is
# not a general shorter-stride relaxation: it is a semantic fallback for a short terminal subgroup.
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'if len(hits)!=1:return None',
    "globals()['_RICH_COMPACT_STRIDE_TRANSITIONS_V148']",
    'def _v131_scan_stats(raw,start,end):',
]:
    if token not in py:raise RuntimeError('v159 prerequisite missing: '+token)

start=py.find('def _v148_compact_stride_next(raw,p,end):')
end=py.find('\ndef ',start+1)
if end<0:end=len(py)
block=py[start:end]
if '_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159' not in block:
    needle='    # Do not choose between multiple possible compact serialisations.\n    if len(hits)!=1:return None\n'
    if needle not in block:raise RuntimeError('v159 v148 decision anchor missing')
    repl="""    # Do not choose between multiple possible compact serialisations. The original v148\n    # four-row proof remains authoritative whenever present.\n    if len(hits)==0:\n        # Short terminal substitute/bench groups can contain only two successor rows, making a\n        # four-player proof mathematically impossible. Admit exactly one three-row chain only when\n        # BOTH successors independently look like bench records. No starter/general chain gets this\n        # lower evidence requirement.\n        short=[]\n        def _v159_benchish(rr):\n            if int(rr.get('sub_on',0) or 0)>0:return True\n            # Unused bench rows are allowed only when they carry no real match activity. Keep this\n            # intentionally narrow; positive cards/goals/shots/passes/tackles mean the row is active.\n            for kk in ('goals','assists','own_goals','yellow','red','shots','shots_on_target',\n                       'passes_attempted','passes_completed','tackles_attempted','tackles_won',\n                       'headers_attempted','headers_won','sub_off'):\n                if int(rr.get(kk,0) or 0)!=0:return False\n            return True\n        q_hi2=min(int(end)-158,p+214)\n        for q2 in range(p+158,q_hi2):\n            if raw[q2]!=2:continue\n            rr1=_rich_stat_record_at(raw,q2)\n            if not rr1 or not _v159_benchish(rr1):continue\n            pp1=int(rr1.get('player_id',0) or 0)\n            if pp1<=0 or pp1==pid0:continue\n            d1=q2-p\n            s_hi2=min(int(end)-158,q2+214)\n            for s2 in range(q2+158,s_hi2):\n                if raw[s2]!=2:continue\n                d2=s2-q2\n                if abs(d2-d1)>8:continue\n                rr2=_rich_stat_record_at(raw,s2)\n                if not rr2 or not _v159_benchish(rr2):continue\n                pp2=int(rr2.get('player_id',0) or 0)\n                if pp2<=0 or pp2 in (pid0,pp1):continue\n                short.append((q2,s2,d1))\n        # Ambiguous short chains remain unresolved.\n        if len(short)==1:\n            q2,s2,d=short[0]\n            globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']=int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0))+1\n            globals()['_RICH_SHORT_COMPACT_BENCH_MIN_V159']=min(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MIN_V159',999999)),int(d))\n            globals()['_RICH_SHORT_COMPACT_BENCH_MAX_V159']=max(int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),int(d))\n            return q2\n    if len(hits)!=1:return None\n"""
    block=block.replace(needle,repl,1)
    py=py[:start]+block+py[end:]

# Export diagnostics beside the existing v148 stride evidence when possible.
if 'unlabelled_rich_short_compact_bench_transitions_v159' not in py:
    anchor="'unlabelled_rich_compact_stride_transitions_v148':int(globals().get('_RICH_COMPACT_STRIDE_TRANSITIONS_V148',0)),"
    if anchor in py:
        extra=(anchor+
          "'unlabelled_rich_short_compact_bench_transitions_v159':int(globals().get('_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159',0)),"+
          "'unlabelled_rich_short_compact_bench_min_bytes_v159':int(globals().get('_RICH_SHORT_COMPACT_BENCH_MIN_V159',0) if int(globals().get('_RICH_SHORT_COMPACT_BENCH_MIN_V159',999999))<999999 else 0),"+
          "'unlabelled_rich_short_compact_bench_max_bytes_v159':int(globals().get('_RICH_SHORT_COMPACT_BENCH_MAX_V159',0)),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v148_compact_stride_next(raw,p,end):',
    'def _v159_benchish(rr):',
    "globals()['_RICH_SHORT_COMPACT_BENCH_TRANSITIONS_V159']",
    'if len(short)==1:',
    'if len(hits)!=1:return None',
]:assert token in cpy,token
print('v159 preserves v148 four-row compact proof and adds a unique three-row bench-semantic 158..213-byte terminal subgroup fallback')
