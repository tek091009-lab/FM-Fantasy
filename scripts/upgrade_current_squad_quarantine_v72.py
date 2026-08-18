from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]


def reconstruct_html()->str:
    packed=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(packed)).decode('utf-8')


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    if len(chunks)<len(PARTS):chunks+=['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed:raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


def patch_source(py:str)->str:
    old="""        if len(clubs)!=1:\n            ambiguous.append({'player_eid':eid,'club_eids':clubs,'reason':'multiple_current_squad_records'})\n            continue\n"""
    new="""        if len(clubs)!=1:\n            # v72: preserve the decoded person and every current-DB club candidate, but\n            # never guess current membership from retained/history evidence.  The player\n            # is quarantined from the selectable fantasy DB until a future current-DB\n            # decoder can resolve the ambiguity.\n            ambiguous.append({\n                'player_eid':eid,\n                'club_eids':clubs,\n                'reason':'multiple_current_squad_records',\n                'quarantined_from_fantasy_selection':True,\n                'candidate_clubs':[{'club_eid':ce,'name':selected_clubs[ce].name,'short':selected_clubs[ce].short} for ce in clubs if ce in selected_clubs],\n                'person_evidence':{\n                    'legal_name':person.name,\n                    'display_name':getattr(person,'display_name',None),\n                    'common_name':person.common_name,\n                    'first_name':getattr(person,'first_name',None),\n                    'surname_name':getattr(person,'surname_name',None),\n                    'first_name_id':getattr(person,'first_name_id',None),\n                    'surname_name_id':getattr(person,'surname_name_id',None),\n                    'common_name_id':getattr(person,'common_name_id',None),\n                    'positions':list(person.positions or []),\n                    'current_ability':person.current_ability,\n                    'potential_ability':person.potential_ability,\n                },\n            })\n            continue\n"""
    if old not in py:
        if 'quarantined_from_fantasy_selection' not in py:
            raise RuntimeError('v68 ambiguous build_players anchor missing')
    else:
        py=py.replace(old,new,1)

    blocker="""    if ambiguous:\n        raise RuntimeError(f\"Current club membership is ambiguous for {len(ambiguous)} player(s); import blocked instead of resolving from match/opponent history.\")\n"""
    replacement="""    # v72: ambiguity is evidence, not permission to guess and not a reason to lose\n    # the rest of an otherwise valid league import. Ambiguous people are absent from\n    # `players` (therefore cannot be selected) and remain in `ambiguous` for debugging\n    # and future current-database-only resolver paths.\n"""
    if blocker in py:
        py=py.replace(blocker,replacement,1)
    elif 'import blocked instead of resolving from match/opponent history' in py:
        raise RuntimeError('unexpected ambiguity blocker shape')

    marker="'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68'"
    if marker not in py:raise RuntimeError('current squad policy meta marker missing')
    if "'current_squad_ambiguity_policy':'v72-quarantine-preserve-evidence-no-history-guess'" not in py:
        py=py.replace(marker,marker+",'current_squad_ambiguity_policy':'v72-quarantine-preserve-evidence-no-history-guess','current_squad_ambiguous_players_quarantined':len(ambiguous)",1)

    required=[
        'strict_current_db_membership_only_v68',
        'strict-db-membership-only-no-history-mutation-v68',
        'quarantined_from_fantasy_selection',
        'v72-quarantine-preserve-evidence-no-history-guess',
        'candidate_clubs',
        'person_evidence',
    ]
    for token in required:
        if token not in py:raise RuntimeError('missing required invariant '+token)
    forbidden=[
        'import blocked instead of resolving from match/opponent history',
        'if played_club.get(eid) in clubs: ceid=played_club[eid]',
    ]
    for token in forbidden:
        if token in py:raise RuntimeError('unsafe/obsolete invariant remains '+token)
    compile(py,'fm_importer_v72.py','exec')
    return py


def main():
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    patched_py=patch_source(py)
    if patched_py==py:
        print('v72 already applied')
        return
    patched=html[:m.start(1)]+base64.b64encode(patched_py.encode()).decode()+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v72: ambiguous current-squad players quarantined with full evidence; valid remainder preserved')

if __name__=='__main__':main()
