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
for req in ['def confirmed_id_fixture_conditioned_pair_pass():','def confirmed_id_fixture_conditioned_global_pass():','confirmed_side_cohorts=collections.defaultdict(list)']:
    if req not in py:raise RuntimeError('v115 prerequisite missing: '+req)

# v115 targets a binary side-boundary failure mode: an otherwise-correct retained side window can
# contain one or two edge rows from the neighbouring side/window. We never remove interior rows.
# A trim is allowed only when removed historically-owned IDs are NOT uniquely owned by the proposed
# target club. Both sides still have to support the same exact-score authoritative fixture, and at
# least one side must genuinely require trimming. Exactly one fixture+orientation may survive.
anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_edge_trim_pair_pass():
        pid_clubs=collections.defaultdict(set)
        for eid,cohorts in confirmed_side_cohorts.items():
            for cohort in cohorts:
                for pid in cohort:pid_clubs[int(pid)].add(eid)
        if not pid_clubs:return 0

        def row_pid(row):
            try:
                if isinstance(row,dict):
                    for k in ('player_id','pid','id','eid'):
                        if k in row and row[k] is not None:return int(row[k])
                return int(row) if isinstance(row,(int,float)) else None
            except Exception:return None

        def support_ids(ids,target_eid):
            ids={int(x) for x in ids if int(x)>0};target=0;usable=0;other=collections.Counter()
            for pid in ids:
                owners=pid_clubs.get(pid,set())
                if len(owners)!=1:continue
                usable+=1;owner=next(iter(owners))
                if owner==target_eid:target+=1
                else:other[owner]+=1
            if target<4 or usable<4:return None
            if target/max(1,usable)<0.80:return None
            other_n=max(other.values()) if other else 0
            if target-other_n<3:return None
            return target,usable,other_n

        def best_trim(rows,target_eid):
            rows=list(rows or [])
            if len(rows)<9:return None
            candidates=[]
            # total edge removal is bounded to <=2; (0,0) is retained only to compare whether
            # trimming was actually necessary. No interior deletion is ever considered.
            for cut_l,cut_r in ((0,0),(1,0),(0,1),(2,0),(1,1),(0,2)):
                if cut_l+cut_r>=len(rows):continue
                kept=rows[cut_l:len(rows)-cut_r if cut_r else None]
                if len(kept)<9:continue
                removed=rows[:cut_l]+(rows[len(rows)-cut_r:] if cut_r else [])
                safe=True
                for rr in removed:
                    pid=row_pid(rr)
                    if not pid:continue
                    owners=pid_clubs.get(pid,set())
                    # Never trim away a player already uniquely proven for the proposed club.
                    if len(owners)==1 and target_eid in owners:
                        safe=False;break
                if not safe:continue
                sup=support_ids(ids_of(kept),target_eid)
                if sup:candidates.append((cut_l+cut_r,-sup[0],-sup[1],cut_l,cut_r,sup))
            if not candidates:return None
            candidates.sort();best=candidates[0]
            return {'trim':best[0],'left_cut':best[3],'right_cut':best[4],'support':best[5]}

        cache={}
        def side_eval(ci,is_left,target_eid):
            key=(ci,is_left,target_eid)
            if key in cache:return cache[key]
            c=cached[ci];rows=c['left'] if is_left else c['right']
            out=best_trim(rows,target_eid);cache[key]=out;return out

        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            if len(ids_of(c['left']))<9 or len(ids_of(c['right']))<9:continue
            lscore,rscore=score_of(c);valid={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                if lscore==hs and rscore==as_:
                    ls=side_eval(ci,True,heid);rs=side_eval(ci,False,aeid)
                    if ls and rs and heid!=aeid and (ls['trim']>0 or rs['trim']>0):
                        dl=direct_anchor_club(ids_of(c['left']));dr=direct_anchor_club(ids_of(c['right']))
                        if (dl is None or dl==heid) and (dr is None or dr==aeid):
                            valid[(fk,False)]=(f,False,heid,aeid,ls,rs)
                        else:diagnostics['confirmed_id_edge_trim_current_conflicts_rejected']+=1
                if lscore==as_ and rscore==hs:
                    ls=side_eval(ci,True,aeid);rs=side_eval(ci,False,heid)
                    if ls and rs and heid!=aeid and (ls['trim']>0 or rs['trim']>0):
                        dl=direct_anchor_club(ids_of(c['left']));dr=direct_anchor_club(ids_of(c['right']))
                        if (dl is None or dl==aeid) and (dr is None or dr==heid):
                            valid[(fk,True)]=(f,True,aeid,heid,ls,rs)
                        else:diagnostics['confirmed_id_edge_trim_current_conflicts_rejected']+=1
            if len(valid)==1:
                f,rev,leid,reid,ls,rs=next(iter(valid.values()))
                trims=ls['trim']+rs['trim'];strength=min(ls['support'][0],rs['support'][0])
                proposals.append((-trims,strength,ci,f,rev,leid,reid,ls,rs))
            elif len(valid)>1:
                diagnostics['confirmed_id_edge_trim_ambiguities_rejected']+=1

        proposals.sort(reverse=True);added=0
        for _negtrim,_strength,ci,f,rev,leid,reid,ls,rs in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_trim_v115'):
                added+=1
                diagnostics['confirmed_id_edge_trim_matches']+=1
                diagnostics['confirmed_id_edge_trim_rows_removed']+=ls['trim']+rs['trim']
                if ls['trim'] and rs['trim']:diagnostics['confirmed_id_edge_trim_both_sides']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_edge_trim_pair_pass():' not in py:
    if anchor not in py:raise RuntimeError('v115 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag="    diagnostics.setdefault('confirmed_id_fixture_global_matches',0)\n"
extra=(diag+
"    diagnostics.setdefault('confirmed_id_edge_trim_matches',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_trim_rows_removed',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_trim_both_sides',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_trim_ambiguities_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_trim_current_conflicts_rejected',0)\n")
if "diagnostics.setdefault('confirmed_id_edge_trim_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v115 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old=';y=confirmed_name_roster_global_constraint_pass();p=confirmed_id_fixture_conditioned_pair_pass();d=confirmed_id_fixture_conditioned_global_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
new=';y=confirmed_name_roster_global_constraint_pass();p=confirmed_id_fixture_conditioned_pair_pass();d=confirmed_id_fixture_conditioned_global_pass();e=confirmed_id_edge_trim_pair_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
if 'e=confirmed_id_edge_trim_pair_pass()' not in py:
    if old not in py:raise RuntimeError('v115 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or p or d or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+p+d+l+t+z+u+v\n"
new="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or p or d or e or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+p+d+e+l+t+z+u+v\n"
if '+p+d+e+l+t+z+u+v' not in py:
    if old not in py:raise RuntimeError('v115 fixed-point total anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_id_fixture_global_matches':member_rich_diag.get('confirmed_id_fixture_global_matches',0),"
extra=(handoff+
"'unlabelled_rich_confirmed_id_edge_trim_matches':member_rich_diag.get('confirmed_id_edge_trim_matches',0),"
"'unlabelled_rich_confirmed_id_edge_trim_rows_removed':member_rich_diag.get('confirmed_id_edge_trim_rows_removed',0),"
"'unlabelled_rich_confirmed_id_edge_trim_both_sides':member_rich_diag.get('confirmed_id_edge_trim_both_sides',0),"
"'unlabelled_rich_confirmed_id_edge_trim_ambiguities_rejected':member_rich_diag.get('confirmed_id_edge_trim_ambiguities_rejected',0),"
"'unlabelled_rich_confirmed_id_edge_trim_current_conflicts_rejected':member_rich_diag.get('confirmed_id_edge_trim_current_conflicts_rejected',0),")
if 'unlabelled_rich_confirmed_id_edge_trim_matches' not in py:
    if handoff not in py:raise RuntimeError('v115 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_id_edge_trim_pair_pass():',
    "for cut_l,cut_r in ((0,0),(1,0),(0,1),(2,0),(1,1),(0,2)):",
    'if len(owners)==1 and target_eid in owners:',
    "(ls['trim']>0 or rs['trim']>0)",
    "'unlabelled_retained_confirmed_id_edge_trim_v115'",
    'e=confirmed_id_edge_trim_pair_pass()',
    'unlabelled_rich_confirmed_id_edge_trim_matches',
    'def confirmed_id_fixture_conditioned_global_pass():'
]:assert s in cpy,s
print('v115 bounded edge-trim retained-ID recovery applied')