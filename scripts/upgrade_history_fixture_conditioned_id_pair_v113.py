from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
for req in ['confirmed_side_cohorts=collections.defaultdict(list)','def confirmed_id_local_anchor_pass():','def confirmed_id_transitive_graph_pass():']:
    if req not in py:raise RuntimeError('v113 prerequisite missing: '+req)

# v113 is a fixture-conditioned numeric-ID path. It does NOT try to label a retained side
# globally first. Instead, for each exact-score authoritative fixture, each retained side must
# independently contain enough player IDs whose historical club ownership has already been
# proven by earlier register_match() successes. Multi-club/transfer IDs are neutral and cannot
# create support. Exactly one fixture+orientation must satisfy both sides.
anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_fixture_conditioned_pair_pass():
        # Build historical PID ownership exclusively from already-authoritative retained matches.
        pid_clubs=collections.defaultdict(set)
        for eid,cohorts in confirmed_side_cohorts.items():
            for cohort in cohorts:
                for pid in cohort:pid_clubs[int(pid)].add(eid)
        if not pid_clubs:return 0

        def side_support(ids,target_eid):
            ids={int(x) for x in ids if int(x)>0}
            target=0;usable=0;other=collections.Counter()
            for pid in ids:
                owners=pid_clubs.get(pid,set())
                # Transfer/multi-club IDs are deliberately neutral.
                if len(owners)!=1:continue
                usable+=1
                owner=next(iter(owners))
                if owner==target_eid:target+=1
                else:other[owner]+=1
            # Lower than v95's accumulated-roster threshold only because BOTH sides must pass
            # independently against the same exact-score fixture and the final fixture is unique.
            if target<4 or usable<4:return None
            if target/max(1,usable)<0.80:return None
            other_n=max(other.values()) if other else 0
            if target-other_n<3:return None
            return target,usable,other_n

        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            if len(lids)<9 or len(rids)<9:continue
            lscore,rscore=score_of(c);valid={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                # Natural retained orientation.
                if lscore==hs and rscore==as_:
                    ls=side_support(lids,heid);rs=side_support(rids,aeid)
                    if ls and rs and heid!=aeid:
                        # Existing strong CURRENT-squad anchors remain vetoes, never positive proof.
                        dl=direct_anchor_club(lids);dr=direct_anchor_club(rids)
                        if (dl is None or dl==heid) and (dr is None or dr==aeid):
                            valid[(fk,False)]=(f,False,heid,aeid,ls,rs)
                        else:diagnostics['confirmed_id_fixture_conditioned_current_conflicts_rejected']+=1
                # Reversed retained orientation.
                if lscore==as_ and rscore==hs:
                    ls=side_support(lids,aeid);rs=side_support(rids,heid)
                    if ls and rs and heid!=aeid:
                        dl=direct_anchor_club(lids);dr=direct_anchor_club(rids)
                        if (dl is None or dl==aeid) and (dr is None or dr==heid):
                            valid[(fk,True)]=(f,True,aeid,heid,ls,rs)
                        else:diagnostics['confirmed_id_fixture_conditioned_current_conflicts_rejected']+=1
            # One authoritative fixture+orientation only. Any ambiguity is preserved.
            if len(valid)==1:
                f,rev,leid,reid,ls,rs=next(iter(valid.values()))
                strength=min(ls[0],rs[0]);coverage=ls[0]+rs[0]
                proposals.append((strength,coverage,ci,f,rev,leid,reid))
            elif len(valid)>1:
                diagnostics['confirmed_id_fixture_conditioned_ambiguities_rejected']+=1

        proposals.sort(reverse=True);added=0
        for _strength,_coverage,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_fixture_conditioned_confirmed_id_pair_v113'):
                added+=1;diagnostics['confirmed_id_fixture_conditioned_pair_matches']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_fixture_conditioned_pair_pass():' not in py:
    if anchor not in py:raise RuntimeError('v113 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_id_local_anchor_fixture_matches',0)\n"
diag_new=("    diagnostics.setdefault('confirmed_id_fixture_conditioned_pair_matches',0)\n"
          "    diagnostics.setdefault('confirmed_id_fixture_conditioned_ambiguities_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_fixture_conditioned_current_conflicts_rejected',0)\n"+diag_anchor)
if "diagnostics.setdefault('confirmed_id_fixture_conditioned_pair_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v113 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=';y=confirmed_name_roster_global_constraint_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
new=';y=confirmed_name_roster_global_constraint_pass();p=confirmed_id_fixture_conditioned_pair_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
if 'p=confirmed_id_fixture_conditioned_pair_pass()' not in py:
    if old not in py:raise RuntimeError('v113 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+l+t+z+u+v\n"
new="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or p or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+p+l+t+z+u+v\n"
if '+y+p+l+t+z+u+v' not in py:
    if old not in py:raise RuntimeError('v113 fixed-point total anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_id_local_anchor_fixture_matches':member_rich_diag.get('confirmed_id_local_anchor_fixture_matches',0),"
extra=("'unlabelled_rich_confirmed_id_fixture_conditioned_pair_matches':member_rich_diag.get('confirmed_id_fixture_conditioned_pair_matches',0),"
       "'unlabelled_rich_confirmed_id_fixture_conditioned_ambiguities_rejected':member_rich_diag.get('confirmed_id_fixture_conditioned_ambiguities_rejected',0),"
       "'unlabelled_rich_confirmed_id_fixture_conditioned_current_conflicts_rejected':member_rich_diag.get('confirmed_id_fixture_conditioned_current_conflicts_rejected',0),"+handoff)
if 'unlabelled_rich_confirmed_id_fixture_conditioned_pair_matches' not in py:
    if handoff not in py:raise RuntimeError('v113 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_id_fixture_conditioned_pair_pass():','if target<4 or usable<4:return None','if target/max(1,usable)<0.80:return None','if target-other_n<3:return None',"'unlabelled_retained_fixture_conditioned_confirmed_id_pair_v113'",'p=confirmed_id_fixture_conditioned_pair_pass()','unlabelled_rich_confirmed_id_fixture_conditioned_pair_matches','def confirmed_id_local_anchor_pass():','def confirmed_id_transitive_graph_pass():']:
    assert s in cpy,s
print('v113 fixture-conditioned confirmed-ID pair recovery applied')
