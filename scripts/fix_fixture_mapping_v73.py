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
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

def replace_function(src:str,start_name:str,next_name:str,new_block:str)->str:
    pat=re.compile(r'^'+re.escape(start_name)+r'.*?(?=^'+re.escape(next_name)+r')',re.M|re.S)
    m=pat.search(src)
    if not m: raise RuntimeError(f'function block not found: {start_name} -> {next_name}')
    return src[:m.start()]+new_block.rstrip()+'\n\n'+src[m.end():]

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

new_select=r'''def select_championship_fixtures(fix:bytes,clubs:dict[int,Club],expected_names:set[str]|None=None,
                                 expected_league:str|None=None,db:bytes|None=None)->tuple[list[dict[str,Any]],dict[str,Any]]:
    """Select the current supported domestic league and PROVE its fixture-team -> club mapping.

    v73: a 20/24-team calendar shape is not club identity evidence.  Every candidate fixture
    mapping must also decode a plausible CURRENT senior squad for every selected club from
    game_db.dat. Retained match history is never used to move/select current clubs.
    """
    groups=scan_fixture_groups(fix)
    exact_all=[g for g in groups if g['exact']]
    if not exact_all:
        near=sorted(groups,key=lambda g:(abs(len(g['teams'])-24),-g['season_start']))[:10]
        summary='; '.join(f"comp={g['competition_id']} season={g['season_start']} fixtures={len(g['rows'])} teams={len(g['teams'])} gws={len(g['gws'])} shape={g.get('league_shape')}" for g in near)
        raise RuntimeError('No supported full league season could be identified. Candidates: '+summary)

    requested=expected_league if expected_league in SUPPORTED_LEAGUES else None
    if requested:
        exact=[g for g in exact_all if g.get('league_shape')==requested]
        if not exact:
            raise RuntimeError(f'Manual league selection was {requested}, but no complete {requested} season exists in this save. The selection will not be overridden.')
        newest=max(g['season_start'] for g in exact)
        exact=[g for g in exact if g['season_start']==newest]
        selection_mode='user_preference_locked'
    else:
        newest=max(g['season_start'] for g in exact_all)
        exact=[g for g in exact_all if g['season_start']==newest]
        shapes={g.get('league_shape') for g in exact}
        if len(shapes)>1:
            summary=', '.join(sorted(str(x) for x in shapes))
            raise RuntimeError(f'Current season {newest}/{str(newest+1)[-2:]} contains both supported English leagues ({summary}). Historical retained-match identity is deliberately ignored because a promoted/relegated human club may have old division data. Choose the current league once; the choice will be locked for this import.')
        selection_mode='auto_latest_season'

    if db is None:
        raise RuntimeError('Current-season club identity validation requires game_db.dat; unsafe fixture-only mapping is disabled.')

    scored=[]
    candidate_debug=[]
    for g in exact:
        try:
            shifts=_fixture_to_club_shift_candidates(g['teams'],clubs)
        except Exception as e:
            candidate_debug.append({'competition_id':g['competition_id'],'season_start':g['season_start'],
                                    'league_shape':g.get('league_shape'),'error':str(e)})
            continue
        for sh in shifts:
            try:
                ev=_fixture_shift_current_squad_evidence(g['teams'],clubs,sh,db,expected_names if requested else None)
                ev.update({'competition_id':g['competition_id'],'season_start':g['season_start'],'league_shape':g.get('league_shape')})
                candidate_debug.append(ev)
                # The exact same squad-size invariant enforced at publish time is required BEFORE
                # a shift is eligible.  A nearby English club entity (the v72 +1-EID failure)
                # therefore cannot win merely because it is English.
                if ev['safe_squad_clubs'] != len(g['teams']):
                    continue
                overlap=ev['expected_name_overlap']
                legacy_hint=1 if (g.get('league_shape')=='EFL Championship' and g['competition_id']==CHAMPIONSHIP_FIXTURE_COMP_ID) else 0
                # Prefer fewer duplicated current-list memberships, then any direct expected-name
                # evidence, then the legacy competition hint only as a late deterministic tie-break.
                score=(ev['safe_squad_clubs'],-ev['duplicate_current_memberships'],overlap,legacy_hint,-abs(sh),-g['competition_id'])
                scored.append((score,g,sh,ev))
            except Exception as e:
                candidate_debug.append({'competition_id':g['competition_id'],'season_start':g['season_start'],
                                        'league_shape':g.get('league_shape'),'shift':sh,'error':str(e)})
    if not scored:
        summary='; '.join(
            f"comp={x.get('competition_id')} shift={x.get('shift')} safe={x.get('safe_squad_clubs','?')}/{x.get('team_count','?')} missing={','.join(x.get('unsafe_squad_names',[])[:4]) or '-'}"
            for x in candidate_debug[:16]
        )
        raise RuntimeError('Supported fixture calendars were found, but no fixture-to-club mapping passed current first-team squad validation. '+summary)
    scored.sort(key=lambda x:x[0],reverse=True)
    score,g,shift,chosen_ev=scored[0]
    # If two mappings are equally proven through all identity evidence, do not guess.
    if len(scored)>1 and scored[1][0]==score and scored[1][2]!=shift:
        raise RuntimeError(f'Fixture-to-club identity remains ambiguous between shifts {shift} and {scored[1][2]}; import blocked rather than guessing.')
    rows=g['rows'];gw_info=_normalize_gameweeks(rows);spec=SUPPORTED_LEAGUES[g['league_shape']]
    info={'competition_id':g['competition_id'],'season_start':g['season_start'],'fixture_to_club_shift':shift,
          'candidate_groups':len(groups),'exact_candidate_groups':len(exact_all),
          'current_season_candidate_groups':len(exact),'current_season_candidates':candidate_debug[:48],
          'requested_league':requested,'selection_mode':selection_mode,
          'rich_name_overlap':chosen_ev['expected_name_overlap'],'competition':g['league_shape'],'competition_code':spec['code'],
          'team_count':spec['teams'],'total_gameweeks':spec['rounds'],'fixture_count':spec['fixtures'],
          'fixture_club_mapping_policy':'current-squad-validated-shift-v73',
          'selected_mapping_evidence':chosen_ev,
          'gameweek_relabels':gw_info['raw_round_relabels'],'calendar_gameweek_windows':gw_info['calendar_windows'],
          'calendar_reassigned_count':gw_info['calendar_reassigned_count'],
          'calendar_reassigned_examples':gw_info['calendar_reassigned_examples']}
    return rows,info'''

new_derive=r'''def _fixture_to_club_shift_candidates(team_ids:set[int],clubs:dict[int,Club])->list[int]:
    """Return every constant shift that maps ALL fixture team ids to decoded English clubs."""
    english={eid for eid,c in clubs.items() if c.nation_id==139}
    counts=collections.Counter()
    for shift in range(-512,513):
        n=sum(1 for tid in team_ids if tid-shift in english)
        if n:counts[shift]=n
    if not counts:raise RuntimeError('Could not link fixture team ids to club entity ids')
    full=sorted(sh for sh,n in counts.items() if n==len(team_ids))
    if not full:
        best=max(counts.values())
        raise RuntimeError(f'Fixture→club identity mapping incomplete ({best}/{len(team_ids)})')
    return full


def derive_fixture_to_club_shift(team_ids:set[int],clubs:dict[int,Club],expected_names:set[str]|None=None)->int:
    """Compatibility helper. Production selection validates each full shift against current squads."""
    tied=_fixture_to_club_shift_candidates(team_ids,clubs)
    if expected_names:
        def score(sh):
            mapped={normalize_club_name(clubs[tid-sh].short or clubs[tid-sh].name) for tid in team_ids}
            return len(mapped & expected_names)
        tied.sort(key=lambda sh:(score(sh),-abs(sh)),reverse=True)
    return tied[0]


def _fixture_shift_current_squad_evidence(team_ids:set[int],clubs:dict[int,Club],shift:int,db:bytes,
                                           expected_names:set[str]|None=None)->dict[str,Any]:
    selected={tid-shift:clubs[tid-shift] for tid in team_ids if tid-shift in clubs}
    if len(selected)!=len(team_ids):
        raise RuntimeError(f'shift {shift} does not map every fixture team to a club')
    mapped={normalize_club_name(c.short or c.name) for c in selected.values()}
    squads,diag=scan_first_team_squads(db,selected,None)
    sizes={eid:len(squads.get(eid,[])) for eid in selected}
    safe={eid:n for eid,n in sizes.items() if 12<=n<=45}
    unsafe=[normalize_club_name(selected[eid].short or selected[eid].name) for eid,n in sizes.items() if not (12<=n<=45)]
    memberships=collections.Counter()
    for vals in squads.values():
        for pid in set(vals):memberships[pid]+=1
    dup=sum(1 for n in memberships.values() if n>1)
    return {
        'shift':shift,
        'team_count':len(team_ids),
        'mapped_clubs':sorted(mapped),
        'safe_squad_clubs':len(safe),
        'unsafe_squad_names':sorted(unsafe),
        'squad_sizes':{normalize_club_name(selected[eid].short or selected[eid].name):n for eid,n in sorted(sizes.items())},
        'duplicate_current_memberships':dup,
        'expected_name_overlap':len(mapped & expected_names) if expected_names else 0,
        'squad_policy':diag.get('policy'),
        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),
        'mapping_proof':'all-fixture-teams-map-to-English-clubs + every-current-senior-squad-size-12..45-v73',
    }'''

py=replace_function(py,'def select_championship_fixtures','def scan_clubs',new_select)
py=replace_function(py,'def derive_fixture_to_club_shift','def read_squad_list',new_derive)
old_call="select_championship_fixtures(fix,all_clubs,expected_names,requested_league)"
new_call="select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)"
if old_call in py:py=py.replace(old_call,new_call,1)
elif new_call not in py:raise RuntimeError('browser fixture selector call not found')

# Add production policy markers to payload meta. These are read by updateguard.js and Supabase.
needle="'league_selection_source':fixture_info.get('selection_mode',('user_preference_locked' if requested_league else 'auto_latest_season'))"
replacement=needle+",'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','fixture_club_mapping_policy':fixture_info.get('fixture_club_mapping_policy'),'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence')"
if needle in py and "'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence')" not in py:
    py=py.replace(needle,replacement,1)
elif "'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence')" not in py:
    raise RuntimeError('payload meta insertion point missing')

compile(py,'fm_importer_v73.py','exec')
for tok in [
    'current-squad-validated-shift-v73','_fixture_to_club_shift_candidates','_fixture_shift_current_squad_evidence',
    'every-current-senior-squad-size-12..45-v73','select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)',
    "'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68'",
    "'rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69'",
]:
    if tok not in py:raise RuntimeError('V73 invariant missing '+tok)

new_b64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('v73: fixture->club shift is now proven by current first-team squad records before selection')
