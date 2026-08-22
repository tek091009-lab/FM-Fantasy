from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def confirmed_name_transitive_graph_pass():' not in py:
    raise RuntimeError('v110 prerequisite missing: v109 transitive graph')

# v109 ordered each pair by mutating `a`, the outer-loop node index. Once a swap occurred,
# every later `b` for that same name could be counted against the wrong node. That silently
# under-counts or misattributes shared-name edges and can break legitimate rotation chains.
old="""            for a_pos in range(len(idxs)):
                a=idxs[a_pos]
                for b in idxs[a_pos+1:]:
                    if a>b:a,b=b,a
                    pair_shared[(a,b)]+=1
"""
new="""            for a_pos in range(len(idxs)):
                a=idxs[a_pos]
                for b in idxs[a_pos+1:]:
                    aa,bb=(a,b) if a<b else (b,a)
                    pair_shared[(aa,bb)]+=1
"""
if old not in py:
    if 'aa,bb=(a,b) if a<b else (b,a)' not in py:
        raise RuntimeError('v110 pair-counter anchor missing')
else:
    py=py.replace(old,new,1)

# Expose the identity-policy version so debug payloads can prove that graph edges were counted
# with a non-mutating canonical pair key.
diag_anchor="    diagnostics.setdefault('confirmed_name_transitive_conflict_components_rejected',0)\n"
diag_new=diag_anchor+"    diagnostics['confirmed_name_transitive_pair_counter_policy']='non_mutating_sorted_pair_v110'\n"
if "confirmed_name_transitive_pair_counter_policy" not in py:
    if diag_anchor not in py:raise RuntimeError('v110 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

handoff="'unlabelled_rich_confirmed_name_transitive_conflict_components_rejected':member_rich_diag.get('confirmed_name_transitive_conflict_components_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_transitive_pair_counter_policy':member_rich_diag.get('confirmed_name_transitive_pair_counter_policy','unknown'),"
if 'unlabelled_rich_confirmed_name_transitive_pair_counter_policy' not in py:
    if handoff not in py:raise RuntimeError('v110 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'aa,bb=(a,b) if a<b else (b,a)' in cpy
assert 'if a>b:a,b=b,a' not in cpy
assert "confirmed_name_transitive_pair_counter_policy']='non_mutating_sorted_pair_v110'" in cpy
assert 'def confirmed_name_transitive_graph_pass():' in cpy
assert 'shared/denom<0.55' in cpy
print('v110 non-mutating transitive retained-name pair counter applied')
