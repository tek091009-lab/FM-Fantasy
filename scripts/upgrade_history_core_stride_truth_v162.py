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

# v162 corrects an overclaim in v155.  A 145-byte core-only GAME_MATCH_PLAYER_STATS row is not
# universally fantasy-complete for an ACTIVE player: the current universal mapping obtains
# team_goals_conceded_while_on_pitch from +146, outside that core.  Zero-filling the tail therefore
# made goals_conceded look like a real zero.  Exact goalkeeper saves, however, are independently
# available in the proven core at +50/+51/+52 (the original extractor used their sum directly).
#
# We keep core-only rows useful without fabricating stats:
#   * exact saves are rebuilt from the three core save components;
#   * provably inactive/unrated bench rows remain safe to admit (0 minutes => no GC/CS scoring);
#   * active core-only rows stay as structural evidence but are quarantined from rich fantasy history
#     until a decoder recovers the missing on-pitch goals-conceded field.
for token in [
    'def _v155_prepare_core_fantasy_row(r):',
    "r['historical_fantasy_core_complete_v155']=True",
    "r=_v155_prepare_core_fantasy_row(r)",
    'def _v150_core_record_at(raw,p):',
]:
    if token not in py:raise RuntimeError('v162 prerequisite missing: '+token)

start=py.find('def _v155_prepare_core_fantasy_row(r):')
end=py.find('\ndef ',start+1)
if start<0 or end<0:raise RuntimeError('v162 v155 helper boundaries not found')
helper="""def _v155_prepare_core_fantasy_row(r):
    # v162 truth policy for the 145-byte core representation.
    r=dict(r)
    core_saves=sum(int(r.get(k,0) or 0) for k in (
        'save_component_legacy_1','save_component_legacy_2','save_component_legacy_3'))
    r['saves']=core_saves
    r['core_exact_saves_v155']=core_saves
    r['core_exact_saves_v162']=core_saves
    for k in ('possession_won_candidate','possession_lost_candidate','shots_on_target_faced',
              'team_goals_conceded_while_on_pitch','shots_on_target_against_team',
              'total_shots_on_target_against_team'):
        if k in r:r[k]=None
    r['historical_stats_complete_v154']=False
    r['historical_extended_stats_complete_v155']=False
    r['missing_extended_fields_v155']=('possession_won_candidate','possession_lost_candidate','shots_on_target_faced')
    inactive=bool(r.get('unrated_inactive_candidate'))
    if inactive:
        # This record is independently proven to contain no match activity. It is safe as an unused
        # bench row and is useful for completing retained squad arrays without inventing active stats.
        r['goals_conceded']=0
        r['saves']=0
        r['core_exact_goals_conceded_v155']=0
        r['historical_fantasy_core_complete_v155']=True
        r['historical_fantasy_core_complete_v162']=True
        r['core_stat_policy_v162']='inactive_core_row_safe; exact zero activity'
    else:
        # +146 is not physically present in the proven 145-byte core. Never turn its zero-fill into
        # a real goals-conceded value for an active player.
        r['goals_conceded']=None
        r['core_exact_goals_conceded_v155']=None
        r['historical_fantasy_core_complete_v155']=False
        r['historical_fantasy_core_complete_v162']=False
        r['core_missing_fantasy_field_v162']='team_goals_conceded_while_on_pitch'
        r['core_stat_policy_v162']='exact core saves retained; active GC unresolved/quarantined'
    return r

"""
py=py[:start]+helper+py[end+1:]

# Both retained scanners have the same v155 preparation call.  Only provably complete core rows may
# proceed to out.append()/rows.append(). Active core-only rows remain discoverable evidence but do not
# consume a fixture or enter fantasy history.
needle="                    r=_v155_prepare_core_fantasy_row(r)\n"
count=py.count(needle)
if count<2:raise RuntimeError(f'v162 expected both scanner prepare calls, found {count}')
replacement=(needle+
    "                    if not bool(r.get('historical_fantasy_core_complete_v162')):\n"
    "                        _v162_is_header=('rows' in locals() and isinstance(locals().get('rows'),list))\n"
    "                        _v162_key='_RICH_HEADER_CORE_ACTIVE_QUARANTINED_V162' if _v162_is_header else '_RICH_CORE_ACTIVE_QUARANTINED_V162'\n"
    "                        globals()[_v162_key]=int(globals().get(_v162_key,0))+1\n"
    "                        globals()['_RICH_CORE_ACTIVE_MISSING_FIELD_V162']='team_goals_conceded_while_on_pitch'\n"
    "                        p+=145;continue\n"
    "                    _v162_is_header=('rows' in locals() and isinstance(locals().get('rows'),list))\n"
    "                    _v162_key='_RICH_HEADER_CORE_INACTIVE_RESTORED_V162' if _v162_is_header else '_RICH_CORE_INACTIVE_RESTORED_V162'\n"
    "                    globals()[_v162_key]=int(globals().get(_v162_key,0))+1\n")
py=py.replace(needle,replacement)

# Export evidence if an existing debug dictionary anchor is available.
if 'unlabelled_rich_core_active_quarantined_v162' not in py:
    anchors=[
        "'unlabelled_rich_core_only_rows_restored_v155':int(globals().get('_RICH_CORE_ONLY_ROWS_RESTORED_V155',0)),",
        "'unlabelled_rich_core_stride_tail_rows_v152':int(globals().get('_RICH_CORE_STRIDE_TAIL_ROWS_V152',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_inactive_restored_v162':int(globals().get('_RICH_CORE_INACTIVE_RESTORED_V162',0)),"+
          "'unlabelled_rich_header_core_inactive_restored_v162':int(globals().get('_RICH_HEADER_CORE_INACTIVE_RESTORED_V162',0)),"+
          "'unlabelled_rich_core_active_quarantined_v162':int(globals().get('_RICH_CORE_ACTIVE_QUARANTINED_V162',0)),"+
          "'unlabelled_rich_header_core_active_quarantined_v162':int(globals().get('_RICH_HEADER_CORE_ACTIVE_QUARANTINED_V162',0)),"+
          "'unlabelled_rich_core_active_missing_field_v162':globals().get('_RICH_CORE_ACTIVE_MISSING_FIELD_V162'),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "r['core_exact_saves_v162']=core_saves",
    "r['historical_fantasy_core_complete_v162']=True",
    "r['historical_fantasy_core_complete_v162']=False",
    "r['goals_conceded']=None",
    "'_RICH_CORE_ACTIVE_QUARANTINED_V162'",
    "'_RICH_HEADER_CORE_ACTIVE_QUARANTINED_V162'",
    "'_RICH_CORE_INACTIVE_RESTORED_V162'",
]:assert token in cpy,token
print('v162 corrects short-stride fantasy completeness: exact core saves retained, inactive bench rows admitted, active core-only rows quarantined until +146 goals-conceded is decoded')