from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
def html():return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()
def repack(s):
 p=base64.b64encode(gzip.compress(s.encode(),9,mtime=0)).decode();step=(len(p)+len(PARTS)-1)//len(PARTS)
 for i,f in enumerate(PARTS):f.write_text(p[i*step:(i+1)*step]+'\n')
def patch(py):
 old="""    out={};diag={'fallbacks':[],'missing_club_eids':[],'rich_augmented_players':0,\n                 'policy':'strict_current_db_membership_only_v68','rejected_options':0}\n\n    def choose_options(options):\n        valid=[]\n        for p,vals,kind in options:\n            if not (12<=len(vals)<=45):\n                diag['rejected_options']+=1;continue\n            priority=2 if kind=='strict' else 1\n            valid.append(((priority,-abs(len(vals)-28),-p),p,vals,kind))\n        if not valid:return None\n        valid.sort(reverse=True)\n        return valid[0][1:]\n"""
 new="""    out={};diag={'fallbacks':[],'missing_club_eids':[],'rich_augmented_players':0,\n                 'policy':'strict_current_db_membership_only_v68','rejected_options':0,\n                 'ambiguous_squad_blocks':[],'consensus_squad_blocks':0}\n    conflicted_clubs=set()\n\n    def choose_options(eid,options):\n        valid=[]\n        for p,vals,kind in options:\n            if not (12<=len(vals)<=45):\n                diag['rejected_options']+=1;continue\n            priority=2 if kind=='strict' else 1\n            valid.append((priority,p,vals,kind))\n        if not valid:return None\n        best_priority=max(x[0] for x in valid)\n        peers=[x for x in valid if x[0]==best_priority]\n        byset=collections.defaultdict(list)\n        for priority,p,vals,kind in peers:byset[tuple(sorted(set(vals)))].append((p,vals,kind))\n        if len(byset)==1:\n            group=next(iter(byset.values()))\n            if len(group)>1:diag['consensus_squad_blocks']+=1\n            group.sort(key=lambda x:(abs(len(x[1])-28),x[0]))\n            return group[0]\n        # v74: equally-authoritative current-DB blocks that disagree on membership are\n        # evidence of schema ambiguity, not permission to select the earliest/28-sized block.\n        conflicted_clubs.add(eid)\n        diag['ambiguous_squad_blocks'].append({'club_eid':eid,'priority':best_priority,'candidates':[{'offset':p,'kind':kind,'players':len(vals),'sample_player_eids':list(vals[:8])} for _,p,vals,kind in peers]})\n        return None\n"""
 if old not in py:
  if 'ambiguous_squad_blocks' not in py:raise RuntimeError('v74 anchor missing')
 else:py=py.replace(old,new,1)
 py=py.replace('chosen=choose_options(options)','chosen=choose_options(eid,options)')
 oldfb="""    for eid,c in selected_clubs.items():\n        if eid in out:continue\n"""
 newfb="""    for eid,c in selected_clubs.items():\n        if eid in out or eid in conflicted_clubs:continue\n"""
 if oldfb in py:py=py.replace(oldfb,newfb,1)
 marker="'current_squad_ambiguity_policy':'v72-quarantine-preserve-evidence-no-history-guess'"
 if marker in py and "current_squad_block_policy" not in py:py=py.replace(marker,marker+",'current_squad_block_policy':'v74-require-current-db-block-consensus-no-heuristic-tiebreak'",1)
 for t in ['ambiguous_squad_blocks','consensus_squad_blocks','v74-require-current-db-block-consensus-no-heuristic-tiebreak']:
  if t not in py:raise RuntimeError('missing '+t)
 compile(py,'fm_importer_v74.py','exec');return py
def main():
 h=html();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',h);assert m
 py=base64.b64decode(m.group(1)).decode();new=patch(py)
 if new==py:print('v74 already applied');return
 h=h[:m.start(1)]+base64.b64encode(new.encode()).decode()+h[m.end(1):];repack(h);assert html()==h
 print('v74 applied: conflicting equally-authoritative current squad blocks are quarantined; exact repeated blocks act as consensus')
if __name__=='__main__':main()
