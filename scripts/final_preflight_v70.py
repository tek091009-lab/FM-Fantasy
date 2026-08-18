from __future__ import annotations
import base64,gzip,json,re,traceback,sys,types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
OUT=ROOT/'_preflight_v70.json'

def main():
    result={'ok':False,'checks':{},'errors':[]}
    try:
        html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
        m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
        result['checks']['embedded_importer']=bool(m)
        if not m: raise RuntimeError('embedded importer missing')
        py=base64.b64decode(m.group(1)).decode('utf-8')
        required=[
            'strict_current_db_membership_only_v68','strict-db-membership-only-no-history-mutation-v68','v68_current-squad-authority_previous-gws-quarantined',
            'def _rich_candidate_twenty_pairs','named_header_candidate_v69','official-score-plus-strict-current-cohort-v69','rich_fixture_coverage','same_match_both_clubs',
            'HEADER_PAT=re.compile','current-squad-validated-shift-v73','def _fixture_to_club_shift_candidates','def _fixture_shift_current_squad_evidence',
            'every-current-senior-squad-size-12..45-v73','select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)',
            "'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68'",
            "'rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69'",
            "'fixture_club_mapping_policy':fixture_info.get('fixture_club_mapping_policy')",
        ]
        result['checks']['required_tokens']={x:(x in py) for x in required}
        forbidden=[
            "cur.extend(add);diag['rich_augmented_players']+=len(add)",
            'if played_club.get(eid) in clubs: ceid=played_club[eid]',
            'infer_hybrid_positions_from_match_markers(rich,players_by_eid)',
            "candidates=[f for f in candidates if f['home_score']==m['home_score'] and f['away_score']==m['away_score']] or candidates",
            'bounded 18-22 rows per side'
        ]
        result['checks']['forbidden_tokens']={x:(x in py) for x in forbidden}
        code=compile(py,'fm_importer_preflight_v73.py','exec');result['checks']['compile']=True
        module_name='fm_importer_preflight_v73';mod=types.ModuleType(module_name);mod.__file__='fm_importer_preflight_v73.py';sys.modules[module_name]=mod
        exec(code,mod.__dict__,mod.__dict__);ns=mod.__dict__
        result['checks']['candidate_function']=callable(ns.get('_rich_candidate_twenty_pairs'))
        result['checks']['header_pat_runtime_object']=hasattr(ns.get('HEADER_PAT'),'finditer')
        result['checks']['name_pool_function']=callable(ns.get('find_name_pool_index'))
        name_pool_probe=False
        if result['checks']['header_pat_runtime_object'] and result['checks']['name_pool_function']:
            try:
                ns['find_name_pool_index'](b'\x00'*4096)
            except RuntimeError as e:
                name_pool_probe='FM name string table not found' in str(e)
            except Exception:
                name_pool_probe=False
        result['checks']['name_pool_runtime_probe']=name_pool_probe

        def row(pid,off): return {'player_id':pid,'offset':off,'goals':0,'own_goals':0}
        left=[row(i+1,i*100) for i in range(20)];right=[row(101+i,5000+i*100) for i in range(20)]
        pairs=ns['_rich_candidate_twenty_pairs'](left+right) if callable(ns.get('_rich_candidate_twenty_pairs')) else []
        result['checks']['synthetic_20x20']=bool(pairs and len(pairs[0][0])==20 and len(pairs[0][1])==20)

        Club=ns.get('Club');shift_candidates=ns.get('_fixture_to_club_shift_candidates');shift_evidence=ns.get('_fixture_shift_current_squad_evidence')
        v73_ok=False;v73_detail={}
        if Club and callable(shift_candidates) and callable(shift_evidence):
            correct=[299,302,304,309,312,315,318,335,364,374,375,380,388,389,390,397,402,410,413,420,422,423,428,429]
            team_ids={eid+132 for eid in correct}
            clubs={eid:Club(eid,eid+1000,f'C{eid}',f'C{eid}',139) for eid in set(correct+[x+1 for x in correct])}
            original=ns['scan_first_team_squads']
            def fake_scan(_db,selected,_rich=None):
                is_correct=set(selected)==set(correct)
                out={}
                for i,eid in enumerate(selected):
                    n=28 if is_correct or i>=2 else 0
                    out[eid]=list(range(eid*100,eid*100+n))
                return out,{'policy':'strict_current_db_membership_only_v68','missing_club_eids':[]}
            ns['scan_first_team_squads']=fake_scan
            shifts=shift_candidates(team_ids,clubs)
            e131=shift_evidence(team_ids,clubs,131,b'x')
            e132=shift_evidence(team_ids,clubs,132,b'x')
            ns['scan_first_team_squads']=original
            v73_ok=(131 in shifts and 132 in shifts and e131.get('safe_squad_clubs')==22 and e132.get('safe_squad_clubs')==24)
            v73_detail={'shifts':shifts,'shift131_safe':e131.get('safe_squad_clubs'),'shift132_safe':e132.get('safe_squad_clubs')}
        result['checks']['fixture_mapping_v73_runtime']=v73_ok
        result['fixture_mapping_v73_detail']=v73_detail

        result['checks']['availability_tokens']={x:(x in py) for x in ['structural-v2-fixture-floor','fixture_floor','full<=save_date','expiry<=save_date']}
        start=html.find('function fmAvailabilityTruthDate(payload){');end=html.find('function fmBuildInitialNews(payload){',start)
        block=html[start:end] if start>=0 and end>start else ''
        result['checks']['availability_block']=bool(block)
        result['checks']['availability_direct']={x:(x in block) for x in ['discipline.dat/active-ban-v1','injury_manager.dat/current-window']}
        result['checks']['availability_forbidden']={x:(x in block) for x in ['5 yellow cards','second-yellow red','fmClubPlayedAfter(payload,p.club,inc.date)']}

        v72_tokens=[
            'fmFantasySeasonLeaguePreferenceV72',
            'fmLeagueAmbiguity=/Multiple supported English league seasons|contains both supported English leagues/i.test(msg)',
            'FM_PENDING_SEASON_LEAGUE=fmRememberLeaguePreference(chosen)',
            'explicitPreference!==undefined?fmNormaliseLeaguePreference(explicitPreference):fmCurrentLeaguePreference()',
            "return await sendFMImport(file,mode,true,chosen)",
        ]
        result['checks']['league_selector_v72']=all(x in html for x in v72_tokens)
        result['checks']['old_league_ambiguity_catch_absent']="if(mode==='season'&&!autoRetry&&!($('leagueImportPreference')?.value)&&msg.includes('Multiple supported English league seasons')){" not in html

        ug=(ROOT/'updateguard.js').read_text();cf=(ROOT/'clearfix.js').read_text();idx=(ROOT/'index.html').read_text()
        result['checks']['update_guard_v4']='world-update-guard-v4-fixture-club-proof' in ug and 'current-squad-validated-shift-v73' in ug
        result['checks']['backed_reset']='fmfantasy_reset_world_season' in cf and 'fmFantasyLastSeasonResetBackup' in cf
        result['checks']['reset_stale_state_guard']=all(x in cf for x in ['clearBrowserManagerSeason','resetLeagueSnapshots','__fmSeasonResetInProgress','fmRestoreManagerFromCloud'])
        result['checks']['index_versions']={x:(x in idx) for x in ['availabilitytruth.js?v=4','updateguard.js?v=4','clearfix.js?v=3']}

        values=[]
        for k,v in result['checks'].items():
            if isinstance(v,bool): values.append(v)
            elif isinstance(v,dict):
                if k in ('forbidden_tokens','availability_forbidden'): values.extend(not x for x in v.values())
                else: values.extend(v.values())
        result['ok']=all(values)
    except Exception as e:
        result['errors'].append(repr(e));result['traceback']=traceback.format_exc()
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
