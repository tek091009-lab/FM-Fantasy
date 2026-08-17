from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# v60: v59 only collapses scanner-window duplicates when the two player-id sets are exactly
# equal. In practice adjacent retained-stat windows can gain/lose one or two edge rows while
# still describing the same logical match block. Those copies survive and compete against one
# another in fixture ranking, lowering the uniqueness margin. Extend normalization conservatively:
# same archive member + near-identical byte span + same aggregate score + both sides have very
# high player-set overlap. The exact-set v59 path remains first and is counted separately.
old_diag="        'near_duplicate_candidate_pairs_collapsed':0\n"
new_diag="        'near_duplicate_candidate_pairs_collapsed':0,'near_duplicate_candidate_pairs_soft_collapsed':0\n"
if s.count(old_diag)!=1:
    raise RuntimeError('v60 diagnostic insertion anchor missing or duplicated')
s=s.replace(old_diag,new_diag,1)

old="""    # Normalize near-identical scanner windows before any identity inference. A save may\n    # contain several candidate windows around the same retained player block; allowing all\n    # of them into proposal ranking artificially lowers uniqueness margins. Do not collapse\n    # by lineup alone: two real matches can reuse an XI. Require the same source member, the\n    # same two player-id sets and a near-identical byte span (<= 2048 bytes at both ends).\n    if cached:\n        compact=[];seen_near=collections.defaultdict(list)\n        for c in cached:\n            lids=tuple(sorted(int(x.get('player_id') or 0) for x in c['left'] if int(x.get('player_id') or 0)>0))\n            rids=tuple(sorted(int(x.get('player_id') or 0) for x in c['right'] if int(x.get('player_id') or 0)>0))\n            pair_key=tuple(sorted((lids,rids)))\n            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))\n            end=max(int(c['left'][-1]['offset']),int(c['right'][-1]['offset']))\n            sig=(c['name'],pair_key)\n            duplicate=False\n            for ps,pe in seen_near[sig]:\n                if abs(start-ps)<=2048 and abs(end-pe)<=2048:\n                    duplicate=True;break\n            if duplicate:\n                diagnostics['near_duplicate_candidate_pairs_collapsed']+=1\n                continue\n            seen_near[sig].append((start,end));compact.append(c)\n        cached=compact\n"""
new="""    # Normalize near-identical scanner windows before any identity inference. A save may\n    # contain several candidate windows around the same retained player block; allowing all\n    # of them into proposal ranking artificially lowers uniqueness margins. v59's exact-set\n    # path remains first. A second conservative path handles adjacent windows which gained or\n    # lost one/two edge player rows: same source member, same aggregate score, near-identical\n    # byte span and >=88% Jaccard overlap on both sides (allowing side orientation to flip).\n    if cached:\n        compact=[];seen_exact=collections.defaultdict(list);seen_member=collections.defaultdict(list)\n        def _norm_ids(rows):\n            return frozenset(int(x.get('player_id') or 0) for x in rows if int(x.get('player_id') or 0)>0)\n        def _jac(a,b):\n            u=len(a|b)\n            return (len(a&b)/u) if u else 0.0\n        def _pair_score_inline(c):\n            left,right=c['left'],c['right']\n            return (sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right),\n                    sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left))\n        for c in cached:\n            lids=_norm_ids(c['left']);rids=_norm_ids(c['right'])\n            pair_key=tuple(sorted((tuple(sorted(lids)),tuple(sorted(rids)))))\n            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))\n            end=max(int(c['left'][-1]['offset']),int(c['right'][-1]['offset']))\n            score=_pair_score_inline(c)\n            sig=(c['name'],pair_key)\n            duplicate=False\n            for ps,pe in seen_exact[sig]:\n                if abs(start-ps)<=2048 and abs(end-pe)<=2048:\n                    duplicate=True;break\n            if duplicate:\n                diagnostics['near_duplicate_candidate_pairs_collapsed']+=1\n                continue\n            # Soft duplicate path. Byte locality is mandatory, so two genuine matches which\n            # reuse almost the same XI do not collapse just because their lineups look alike.\n            for prev in seen_member[c['name']]:\n                if abs(start-prev['start'])>2048 or abs(end-prev['end'])>2048:continue\n                ps=prev['score']\n                same_score=(score==ps or score==(ps[1],ps[0]))\n                if not same_score:continue\n                pl,pr=prev['lids'],prev['rids']\n                direct=min(_jac(lids,pl),_jac(rids,pr))\n                flipped=min(_jac(lids,pr),_jac(rids,pl))\n                best=max(direct,flipped)\n                if best<0.88:continue\n                # Also cap total player-set drift. This keeps the fallback targeted at\n                # neighbouring scanner windows rather than merely similar rotated lineups.\n                if direct>=flipped:\n                    drift=len(lids^pl)+len(rids^pr)\n                else:\n                    drift=len(lids^pr)+len(rids^pl)\n                if drift>4:continue\n                duplicate=True;diagnostics['near_duplicate_candidate_pairs_soft_collapsed']+=1;break\n            if duplicate:continue\n            seen_exact[sig].append((start,end))\n            seen_member[c['name']].append({'start':start,'end':end,'score':score,'lids':lids,'rids':rids})\n            compact.append(c)\n        cached=compact\n"""
if s.count(old)!=1:
    raise RuntimeError('v60 normalization block anchor missing or duplicated')
s=s.replace(old,new,1)

for needle in [
    'def fixture_identity(f):',
    "fixture_identity(f) in used_fixtures",
    "diagnostics['adaptive_cluster_edges']",
    "diagnostics['transfer_conflict_neutralized_players']",
    "diagnostics['near_duplicate_candidate_pairs_collapsed']",
    "diagnostics['near_duplicate_candidate_pairs_soft_collapsed']",
    "best=max(direct,flipped)",
    "if drift>4:continue"
]:
    if needle not in s:
        raise RuntimeError(f'v60 invariant missing: {needle}')

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print('v60: added soft adjacent-window retained-candidate normalization')
