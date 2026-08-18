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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html); assert m,'embedded importer missing'
py=base64.b64decode(m.group(1)).decode('utf-8')

marker="CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'"
if marker not in py:
    needle='def read_squad_list_legacy(db: bytes, head: int, next_head: int|None=None) -> list[int]:'
    assert needle in py
    constants="""CURRENT_SQUAD_MIN=12\nCURRENT_SQUAD_STANDARD_MAX=45\nCURRENT_SQUAD_STRICT_MAX=60\nCURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'\n\n\n"""
    py=py.replace(needle,constants+needle,1)

old="""    valid=[]
    for p,vals,kind in options:
        if not (12<=len(vals)<=45):
            diag['rejected_options']+=1;continue
        vals=list(dict.fromkeys(int(x) for x in vals if int(x)>0))
        if not (12<=len(vals)<=45):
            diag['rejected_options']+=1;continue
        valid.append((priority.get(kind,0),p,vals,kind))
"""
new="""    valid=[]
    for p,vals,kind in options:
        # v79: exact current-team headers may legitimately include an academy-inclusive
        # current roster above 45.  Only the strongest exact EID+duplicated-UID structure
        # gets the extended ceiling; weaker compatibility fallbacks remain capped at 45.
        limit=CURRENT_SQUAD_STRICT_MAX if kind=='strict' else CURRENT_SQUAD_STANDARD_MAX
        if not (CURRENT_SQUAD_MIN<=len(vals)<=limit):
            diag['rejected_options']+=1;continue
        vals=list(dict.fromkeys(int(x) for x in vals if int(x)>0))
        if not (CURRENT_SQUAD_MIN<=len(vals)<=limit):
            diag['rejected_options']+=1;continue
        valid.append((priority.get(kind,0),p,vals,kind))
"""
if old in py: py=py.replace(old,new,1)
elif 'limit=CURRENT_SQUAD_STRICT_MAX' not in py: raise RuntimeError('V79 chooser insertion point missing')

old_union="    if len(sets)>=2 and min_j>=0.72 and 12<=len(union)<=45:\n"
new_union="    union_limit=CURRENT_SQUAD_STRICT_MAX if best>=priority['strict'] else CURRENT_SQUAD_STANDARD_MAX\n    if len(sets)>=2 and min_j>=0.72 and CURRENT_SQUAD_MIN<=len(union)<=union_limit:\n"
if old_union in py: py=py.replace(old_union,new_union,1)
elif 'union_limit=CURRENT_SQUAD_STRICT_MAX' not in py: raise RuntimeError('V79 union insertion point missing')

old_safe="""    safe={eid:n for eid,n in sizes.items() if 12<=n<=45}
    unsafe=[normalize_club_name(selected[eid].short or selected[eid].name) for eid,n in sizes.items() if not (12<=n<=45)]
"""
new_safe="""    # scan_first_team_squads already restricts >45 to an exact current-team header.
    # Therefore the mapping validator can safely recognise that proven extended roster.
    safe={eid:n for eid,n in sizes.items() if CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX}
    unsafe=[normalize_club_name(selected[eid].short or selected[eid].name) for eid,n in sizes.items() if not (CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX)]
"""
if old_safe in py: py=py.replace(old_safe,new_safe,1)
elif 'CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX' not in py: raise RuntimeError('V79 fixture evidence insertion point missing')

py=py.replace("'mapping_proof':'all-fixture-teams-map-to-English-clubs + every-current-senior-squad-size-12..45-v73',",
              "'mapping_proof':'all-fixture-teams-map-to-English-clubs + current-db-roster-proof-v79','current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY,",1)

# Preserve V68/V69 policy markers and add the V79 size policy directly in the browser payload.
meta_needle="meta={'fingerprint':fingerprint"
if meta_needle in py:
    py=py.replace(meta_needle,"meta={'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','fixture_club_mapping_policy':fixture_info.get('fixture_club_mapping_policy'),'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence'),'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY,'fingerprint':fingerprint",1)
elif "'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY" not in py:
    raise RuntimeError('V79 payload meta insertion point missing')

compile(py,'fm_importer_v79.py','exec')
required=[marker,"limit=CURRENT_SQUAD_STRICT_MAX if kind=='strict' else CURRENT_SQUAD_STANDARD_MAX",
          'CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX',"'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY",
          "'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68'",
          "'rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69'",
          'current-db-roster-proof-v79']
for t in required: assert t in py,t
new_b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('V79 importer installed: strict current DB rosters 12-60; fallback rosters remain 12-45')
