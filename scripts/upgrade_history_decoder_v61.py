from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# v61: once a player has credible evidence for more than one club, the transfer-safe path
# correctly removes that player's date-agnostic club vote. That is safe but throws away useful
# information after we have confirmed appearances for that player on both sides of a transfer.
# Reintroduce only date-local evidence inside fixture proposal scoring. This does not create a
# match by itself: exact aggregate score, authoritative fixture, existing score thresholds and
# uniqueness margins still have to pass.
old_diag="        'near_duplicate_candidate_pairs_collapsed':0,'near_duplicate_candidate_pairs_soft_collapsed':0\n"
new_diag="        'near_duplicate_candidate_pairs_collapsed':0,'near_duplicate_candidate_pairs_soft_collapsed':0,\n        'temporal_transfer_fixture_evidence':0\n"
if s.count(old_diag)!=1:
    raise RuntimeError('v61 diagnostic anchor missing or duplicated')
s=s.replace(old_diag,new_diag,1)

old="""    transfer_conflicts=set()\n\n    def player_club_weight(pid,eid):\n"""
new="""    transfer_conflicts=set()\n    # Confirmed retained matches supply dated club appearances. Keep them separately from the\n    # ordinary player votes so transfer ambiguity can remain neutral by default while fixture\n    # scoring may use a very small nearest-date signal when BOTH clubs have confirmed dates.\n    confirmed_temporal_clubs=collections.defaultdict(list)\n    def _history_date_ordinal(v):\n        try:\n            y,m,d=(int(x) for x in str(v or '')[:10].split('-'))\n            return y*372+m*31+d\n        except Exception:\n            return 0\n\n    def player_club_weight(pid,eid):\n"""
if s.count(old)!=1:
    raise RuntimeError('v61 transfer-state anchor missing or duplicated')
s=s.replace(old,new,1)

old="""        used_fixtures.add(fid);used_candidates.add(ci)\n        out.append({'stadium':f.get('stadium'),'home':club_names[heid],'away':club_names[realaeid],\n"""
new="""        used_fixtures.add(fid);used_candidates.add(ci)\n        # Only accepted matches teach temporal membership. Speculative side labels never enter\n        # this table, preventing a guessed transfer timeline from reinforcing itself.\n        ford=_history_date_ordinal(f.get('date'))\n        if ford:\n            for pid in ids_of(H):confirmed_temporal_clubs[int(pid)].append((ford,heid))\n            for pid in ids_of(A):confirmed_temporal_clubs[int(pid)].append((ford,realaeid))\n        out.append({'stadium':f.get('stadium'),'home':club_names[heid],'away':club_names[realaeid],\n"""
if s.count(old)!=1:
    raise RuntimeError('v61 register-match anchor missing or duplicated')
s=s.replace(old,new,1)

old="""    def best_side_club(ids,min_score=3.0,min_margin=1.15):\n        scores=side_scores(ids)\n        if not scores or scores[0][0]<min_score:return None\n        second=scores[1][0] if len(scores)>1 else 0.0\n        if scores[0][0]-second<min_margin:return None\n        return scores[0][2],scores[0][0],second,scores[0][1]\n\n    cluster_labels={}\n"""
new="""    def best_side_club(ids,min_score=3.0,min_margin=1.15):\n        scores=side_scores(ids)\n        if not scores or scores[0][0]<min_score:return None\n        second=scores[1][0] if len(scores)>1 else 0.0\n        if scores[0][0]-second<min_margin:return None\n        return scores[0][2],scores[0][0],second,scores[0][1]\n\n    def temporal_side_evidence(ids,eid,date_value):\n        target=_history_date_ordinal(date_value)\n        if not target:return 0.0\n        value=0.0\n        for pid in ids:\n            pid=int(pid)\n            if pid not in transfer_conflicts:continue\n            recs=confirmed_temporal_clubs.get(pid,[])\n            # A single dated club is not enough: it may simply be the old club plus today's\n            # squad membership. Require confirmed retained appearances for at least two clubs.\n            if len({ceid for _ord,ceid in recs})<2:continue\n            nearest=min(recs,key=lambda x:abs(x[0]-target))\n            gap=abs(nearest[0]-target)\n            if gap>93:continue\n            closeness=1.0-(gap/94.0)\n            if nearest[1]==eid:value+=0.55*closeness\n            elif gap<=31:value-=0.45*(1.0-gap/32.0)\n        return value\n\n    cluster_labels={}\n"""
if s.count(old)!=1:
    raise RuntimeError('v61 temporal function anchor missing or duplicated')
s=s.replace(old,new,1)

old="""                    total=lsc+rsc+bonus+0.35*(ld+rd)\n                    rank.append((total,min(lsc,rsc),f,rev,leid,reid))\n"""
new="""                    temporal=temporal_side_evidence(lids,leid,f.get('date'))+temporal_side_evidence(rids,reid,f.get('date'))\n                    if abs(temporal)>=0.05:diagnostics['temporal_transfer_fixture_evidence']+=1\n                    total=lsc+rsc+bonus+0.35*(ld+rd)+temporal\n                    rank.append((total,min(lsc,rsc),f,rev,leid,reid))\n"""
if s.count(old)!=1:
    raise RuntimeError('v61 fixture-rank anchor missing or duplicated')
s=s.replace(old,new,1)

for needle in [
    'def fixture_identity(f):',
    'near_duplicate_candidate_pairs_soft_collapsed',
    'adaptive_cluster_edges',
    'transfer_conflict_neutralized_players',
    'confirmed_temporal_clubs=collections.defaultdict(list)',
    'def temporal_side_evidence(ids,eid,date_value):',
    "diagnostics['temporal_transfer_fixture_evidence']+=1",
    '+temporal'
]:
    if needle not in s:
        raise RuntimeError(f'v61 invariant missing: {needle}')

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print('v61: added confirmed-date transfer evidence to retained fixture scoring')
