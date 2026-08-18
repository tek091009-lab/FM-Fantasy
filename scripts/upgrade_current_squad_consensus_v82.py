from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

old=re.compile(r'''    viable=\[x for x in metrics if x\['resolved'\]>=8 and x\['ratio'\]>=0\.65 and x\['cas'\]>=8\]\n    if viable:\n        viable\.sort\(key=lambda x:\(x\['top16avg'\],x\['median_ca'\],x\['high_ca'\],x\['ratio'\],len\(x\['vals'\]\)\) ,reverse=True\)\n        one=viable\[0\];two=viable\[1\] if len\(viable\)>1 else None\n        clear=two is None or \(one\['top16avg'\]-two\['top16avg'\]>=6\.0\) or \(one\['median_ca'\]-two\['median_ca'\]>=8\.0 and one\['top16avg'\]>=two\['top16avg'\]\+3\.0\)\n        if clear:\n            diag\['resolved_squad_blocks'\]\.append\(\{'club_eid':eid,'method':'current_person_senior_quality_v75','players':len\(one\['vals'\]\),'resolved_people':one\['resolved'\],'top16avg':round\(one\['top16avg'\],1\),'median_ca':round\(one\['median_ca'\],1\),'runner_up_top16avg':round\(two\['top16avg'\],1\) if two else None\}\)\n            return \(one\['offset'\],one\['vals'\],one\['kind'\]\)\n''')

replacement="""    viable=[x for x in metrics if x['resolved']>=8 and x['ratio']>=0.65 and x['cas']>=8]\n    if viable:\n        viable.sort(key=lambda x:(x['top16avg'],x['median_ca'],x['high_ca'],x['ratio'],len(x['vals'])) ,reverse=True)\n        one=viable[0];two=viable[1] if len(viable)>1 else None\n        clear=two is None or (one['top16avg']-two['top16avg']>=6.0) or (one['median_ca']-two['median_ca']>=8.0 and one['top16avg']>=two['top16avg']+3.0)\n        if clear:\n            # v82: ability is useful reverse-engineering evidence, but it is not structural\n            # proof that one conflicting CURRENT-DB block is the authoritative senior squad.\n            # Keep the ranking for diagnostics and future schema learning; do not let CA\n            # silently override a real current-database disagreement.\n            diag.setdefault('ability_only_resolution_quarantined',0)\n            diag['ability_only_resolution_quarantined']+=1\n            diag.setdefault('ability_profile_evidence',[]).append({\n                'club_eid':eid,'method':'current_person_ability_profile_evidence_v82',\n                'candidate_offset':one['offset'],'players':len(one['vals']),\n                'resolved_people':one['resolved'],'top16avg':round(one['top16avg'],1),\n                'median_ca':round(one['median_ca'],1),\n                'runner_up_top16avg':round(two['top16avg'],1) if two else None,\n                'authoritative':False\n            })\n"""

py2,n=old.subn(replacement,py,count=1)
if n!=1:
    if 'current_person_ability_profile_evidence_v82' in py:
        print('v82 already present'); raise SystemExit(0)
    raise RuntimeError(f'ability resolver block not found ({n})')
py=py2
py=py.replace("'block_policy':'v75-current-db-structural-senior-resolution-no-history'","'block_policy':'v82-current-db-consensus-only-ability-non-authoritative'",1)

compile(py,'fm_importer_v82.py','exec')
required=['current_person_ability_profile_evidence_v82','ability_only_resolution_quarantined','v82-current-db-consensus-only-ability-non-authoritative','high_overlap_current_db_union_v75']
for token in required:
    if token not in py: raise RuntimeError('missing v82 token '+token)
if "'method':'current_person_senior_quality_v75'" in py:
    raise RuntimeError('old ability-authoritative resolution still present')

newb64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+newb64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('v82 current-squad consensus-only resolver applied')
