from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks+=['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')
html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode()

# V80: V79's final fixture-level duplicate/conflict quarantine must use the
# same schema-safe fixture identity as every other retained-history path.
# A missing/zero FM fixture_id must not collapse unrelated fixtures onto 0.
old="""        fid=int(fix['fixture_id'])
        if fid in fixture_conflicts:continue
        if fid not in fixture_seen:
            fixture_seen[fid]=(fsig,len(out));out.append(mm)
        elif fixture_seen[fid][0]==fsig:
            exact_fixture_duplicates+=1
        else:
            fixture_conflicts.add(fid);idx=fixture_seen[fid][1];out[idx]=None
"""
new="""        # V80: use canonical schema-safe fixture identity for final retained
        # representation collapse/quarantine too. This preserves real fixtures
        # when FM omits or zeroes fixture_id in another schema generation.
        fid=fixture_identity(fix)
        if fid in fixture_conflicts:continue
        if fid not in fixture_seen:
            fixture_seen[fid]=(fsig,len(out));out.append(mm)
        elif fixture_seen[fid][0]==fsig:
            exact_fixture_duplicates+=1
        else:
            fixture_conflicts.add(fid);idx=fixture_seen[fid][1];out[idx]=None
"""
if old in py:
    py=py.replace(old,new,1)
elif 'V80: use canonical schema-safe fixture identity for final retained' not in py:
    raise RuntimeError('V80 fixture quarantine anchor missing; V79 must be applied first')

# Keep diagnostics JSON-safe and explicit about the identity representation.
old2="""                                 'conflicting_fixture_ids':sorted(fixture_conflicts)[:40]}"""
new2="""                                 'conflicting_fixture_ids':[list(x) if isinstance(x,tuple) else x for x in sorted(fixture_conflicts,key=str)[:40]],
                                 'fixture_identity_policy':'canonical_id_or_structural_v80'}"""
if old2 in py:
    py=py.replace(old2,new2,1)
elif "'fixture_identity_policy':'canonical_id_or_structural_v80'" not in py:
    raise RuntimeError('V80 diagnostic anchor missing')

for token in ['V80: use canonical schema-safe fixture identity for final retained',
              "fid=fixture_identity(fix)",
              "'fixture_identity_policy':'canonical_id_or_structural_v80'",
              'V79: de-duplicate only byte-local duplicate label representations.']:
    assert token in py,token
compile(py,'fm_importer_v80.py','exec')
html=html[:m.start(1)]+base64.b64encode(py.encode()).decode()+html[m.end(1):]
repack(html);assert reconstruct()==html
print('V80 schema-safe retained fixture quarantine applied')
