from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# Universal-history safety: current squad decoders can legitimately associate one player ID
# with more than one club (transfers, stale squad structures, relaxed schema fallbacks). Such
# IDs must not be allowed to seed a historical side identity for either club.
old="""    club_sets={eid:set(int(x) for x in squads.get(eid,[])) for eid in selected_clubs}\n    club_names={eid:normalize_club_name(c.short or c.name) for eid,c in selected_clubs.items()}\n"""
new="""    club_sets={eid:set(int(x) for x in squads.get(eid,[])) for eid in selected_clubs}\n    membership_owners=collections.defaultdict(set)\n    for _eid,_pids in club_sets.items():\n        for _pid in _pids:membership_owners[int(_pid)].add(_eid)\n    unique_club_sets={eid:{pid for pid in pids if len(membership_owners.get(int(pid),()))==1}\n                      for eid,pids in club_sets.items()}\n    ambiguous_seed_player_ids={pid for pid,owners in membership_owners.items() if len(owners)>1}\n    club_names={eid:normalize_club_name(c.short or c.name) for eid,c in selected_clubs.items()}\n"""
if old not in s: raise RuntimeError('club-set marker not found')
s=s.replace(old,new,1)

s=s.replace("        'identity_rounds':0\n", "        'identity_rounds':0,'ambiguous_seed_player_ids':0,'transfer_conflict_neutralized_players':0\n",1)

old="""    player_votes=collections.defaultdict(lambda:collections.Counter())\n    for eid,pids in club_sets.items():\n        for pid in pids:player_votes[int(pid)][eid]+=4.0\n\n    def player_club_weight(pid,eid):\n        votes=player_votes.get(int(pid))\n        if not votes:return 0.0\n        total=sum(votes.values())\n        if total<=0:return 0.0\n        top=votes.most_common(2)\n        if len(top)>1 and abs(top[0][1]-top[1][1])<0.75 and eid in (top[0][0],top[1][0]):\n            return 0.0\n        return min(1.0,float(votes.get(eid,0.0))/max(1.0,total)*1.35)\n"""
new="""    player_votes=collections.defaultdict(lambda:collections.Counter())\n    diagnostics['ambiguous_seed_player_ids']=len(ambiguous_seed_player_ids)\n    for eid,pids in unique_club_sets.items():\n        for pid in pids:player_votes[int(pid)][eid]+=4.0\n    transfer_conflicts=set()\n\n    def player_club_weight(pid,eid):\n        votes=player_votes.get(int(pid))\n        if not votes:return 0.0\n        total=sum(votes.values())\n        if total<=0:return 0.0\n        top=votes.most_common(3)\n        # Once the same player has meaningful evidence for two clubs, treat that player as\n        # transfer/identity-ambiguous for historical side labelling. Teammate cohorts still\n        # identify the side, but this individual can no longer drag an old match toward his\n        # present-day club. Confirmed match rows remain available for fantasy scoring.\n        meaningful=[(ceid,v) for ceid,v in top if v>=1.75]\n        if len(meaningful)>1:\n            transfer_conflicts.add(int(pid));diagnostics['transfer_conflict_neutralized_players']=len(transfer_conflicts)\n            return 0.0\n        if len(top)>1 and abs(top[0][1]-top[1][1])<0.75 and eid in (top[0][0],top[1][0]):\n            return 0.0\n        return min(1.0,float(votes.get(eid,0.0))/max(1.0,total)*1.35)\n"""
if old not in s: raise RuntimeError('player-vote marker not found')
s=s.replace(old,new,1)

s=s.replace("            direct=len(ids & club_sets[eid])\n", "            direct=len(ids & unique_club_sets[eid])\n",1)
s=s.replace("            lo=len(lids&sset);ro=len(rids&sset)\n", "            uset=unique_club_sets.get(eid,set());lo=len(lids&uset);ro=len(rids&uset)\n",1)

# Make the new diagnostics visible in exported import debug.
needle="'unlabelled_rich_identity_rounds':member_rich_diag.get('identity_rounds',0),"
# The main upgrade script will run after this fragment edit and rebuild the embedded importer.
p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print('v55: ambiguous current-membership anchors removed; transfer-conflicting player votes neutralized')
