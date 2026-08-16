from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# FM can rotate enough of a starting XI/bench between retained matches that the original
# fixed "8 shared player IDs" cluster edge misses the same club. Add a second conservative
# edge path based on proportional overlap, while refusing to join sides whose unique current-
# squad anchors strongly point at different clubs. This augments, never replaces, the legacy edge.
s=s.replace(
"        'identity_rounds':0,'ambiguous_seed_player_ids':0,'transfer_conflict_neutralized_players':0\n",
"        'identity_rounds':0,'ambiguous_seed_player_ids':0,'transfer_conflict_neutralized_players':0,\n        'adaptive_cluster_edges':0,'adaptive_cluster_edges_rejected_conflict':0\n",1)

old="""    for (a,b),cnt in shared.items():\n        if cnt>=8:union(a,b)\n\n    clusters=collections.defaultdict(list)\n"""
new="""    def direct_anchor_club(ids):\n        rank=[]\n        for eid,pids in unique_club_sets.items():\n            n=len(ids & pids)\n            if n:rank.append((n,eid))\n        rank.sort(reverse=True)\n        if not rank or rank[0][0]<4:return None\n        if len(rank)>1 and rank[0][0]-rank[1][0]<2:return None\n        return rank[0][1]\n\n    for (a,b),cnt in shared.items():\n        if cnt>=8:\n            union(a,b);continue\n        # Rotation-safe fallback: six shared players can be highly significant when the\n        # two retained sides are 15-22 player matchday groups. Require a meaningful\n        # proportional overlap and block the edge when independent unique squad anchors\n        # confidently identify different clubs.\n        if cnt<6:continue\n        ia=sides[a]['ids'];ib=sides[b]['ids']\n        denom=max(1,min(len(ia),len(ib)))\n        overlap=float(cnt)/denom\n        if overlap<0.34:continue\n        ca=direct_anchor_club(ia);cb=direct_anchor_club(ib)\n        if ca is not None and cb is not None and ca!=cb:\n            diagnostics['adaptive_cluster_edges_rejected_conflict']+=1\n            continue\n        union(a,b);diagnostics['adaptive_cluster_edges']+=1\n\n    clusters=collections.defaultdict(list)\n"""
if old not in s: raise RuntimeError('cluster-edge marker not found')
s=s.replace(old,new,1)

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print('v56: added rotation-safe proportional side clustering with cross-club anchor conflict guard')
