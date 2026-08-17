from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# v59: retained-stat scanning can emit the same logical match pair more than once when
# neighbouring scan windows start/end a row or two apart. Exact offset signatures do not
# catch these near-duplicates, so they survive into fixture ranking and can make a genuinely
# unique historical fixture look ambiguous. Collapse only extremely conservative duplicates:
# same archive member, exactly the same two player-id sets (orientation independent), and
# nearly the same byte span. Distinct matches with the same lineup remain separate when their
# retained byte regions are materially different.
old_diag="        'adaptive_cluster_edges':0,'adaptive_cluster_edges_rejected_conflict':0\n"
new_diag="        'adaptive_cluster_edges':0,'adaptive_cluster_edges_rejected_conflict':0,\n        'near_duplicate_candidate_pairs_collapsed':0\n"
if s.count(old_diag)!=1:
    raise RuntimeError('v59 diagnostic insertion anchor missing or duplicated')
s=s.replace(old_diag,new_diag,1)

old="""    diagnostics['cached_candidate_pairs']=len(cached)\n    if not cached:return [],diagnostics\n\n    def ids_of(rows):\n"""
new="""    # Normalize near-identical scanner windows before any identity inference. A save may\n    # contain several candidate windows around the same retained player block; allowing all\n    # of them into proposal ranking artificially lowers uniqueness margins. Do not collapse\n    # by lineup alone: two real matches can reuse an XI. Require the same source member, the\n    # same two player-id sets and a near-identical byte span (<= 2048 bytes at both ends).\n    if cached:\n        compact=[];seen_near=collections.defaultdict(list)\n        for c in cached:\n            lids=tuple(sorted(int(x.get('player_id') or 0) for x in c['left'] if int(x.get('player_id') or 0)>0))\n            rids=tuple(sorted(int(x.get('player_id') or 0) for x in c['right'] if int(x.get('player_id') or 0)>0))\n            pair_key=tuple(sorted((lids,rids)))\n            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))\n            end=max(int(c['left'][-1]['offset']),int(c['right'][-1]['offset']))\n            sig=(c['name'],pair_key)\n            duplicate=False\n            for ps,pe in seen_near[sig]:\n                if abs(start-ps)<=2048 and abs(end-pe)<=2048:\n                    duplicate=True;break\n            if duplicate:\n                diagnostics['near_duplicate_candidate_pairs_collapsed']+=1\n                continue\n            seen_near[sig].append((start,end));compact.append(c)\n        cached=compact\n    diagnostics['cached_candidate_pairs']=len(cached)\n    if not cached:return [],diagnostics\n\n    def ids_of(rows):\n"""
if s.count(old)!=1:
    raise RuntimeError('v59 cached-candidate normalization anchor missing or duplicated')
s=s.replace(old,new,1)

# Invariants: preserve all older history paths and verify the new normalization is present.
for needle in [
    'def fixture_identity(f):',
    "fixture_identity(f) in used_fixtures",
    "diagnostics['adaptive_cluster_edges']",
    "diagnostics['transfer_conflict_neutralized_players']",
    "diagnostics['near_duplicate_candidate_pairs_collapsed']"
]:
    if needle not in s:
        raise RuntimeError(f'v59 invariant missing: {needle}')

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print('v59: added conservative retained-candidate near-duplicate normalization')
