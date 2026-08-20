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
for req in ['def confirmed_id_edge_trim_pair_pass():','confirmed_id_edge_trim_target_duplicate_matches','def confirmed_id_fixture_conditioned_pair_pass():']:
    if req not in py:raise RuntimeError('v119 prerequisite missing: '+req)

# v119 targets a different boundary failure from v117/v118. Sometimes an edge row is not junk:
# the scanner split is shifted and the row actually belongs to the opposite retained side. Simply
# trimming it repairs identity but loses that footballer's minutes/goals/cards. This pass only moves
# an edge row across the side boundary when the row's stable PID is already uniquely confirmed for
# the opposite target club. It never moves interior rows and never infers ownership from the candidate.
anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_edge_transfer_pair_pass():
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

        def support_ids(rows,target_eid):
            ids={int(x) for x in ids_of(rows) if int(x)>0};target=0;usable=0;other=collections.Counter()
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

        cuts=((0,0),(1,0),(0,1),(2,0),(1,1),(0,2))
        def split_rows(rows,cut_l,cut_r):
            rows=list(rows or [])
            if cut_l+cut_r>=len(rows):return None,None
            kept=rows[cut_l:len(rows)-cut_r if cut_r else None]
            removed=rows[:cut_l]+(rows[len(rows)-cut_r:] if cut_r else [])
            return kept,removed

        def classify_removed(removed,kept,own_eid,opposite_eid):
            kept_ids={row_pid(r) for r in kept};kept_ids.discard(None)
            transfer=[];dropped=0
            for rr in removed:
                pid=row_pid(rr)
                if not pid:
                    dropped+=1;continue
                owners=pid_clubs.get(pid,set())
                if len(owners)==1 and own_eid in owners:
                    # Own-club rows are protected unless the exact PID remains in the kept side.
                    if pid in kept_ids:
                        dropped+=1;continue
                    return None
                if len(owners)==1 and opposite_eid in owners:
                    transfer.append(rr);continue
                # Unknown / transfer-ambiguous boundary rows may be discarded exactly as in v117,
                # but they never count as evidence that a boundary transfer happened.
                dropped+=1
            return transfer,dropped

        def repaired_states(c,leid,reid):
            left=list(c.get('left') or []);right=list(c.get('right') or [])
            out=[]
            for ll,lr in cuts:
                lkeep,lrem=split_rows(left,ll,lr)
                if lkeep is None or len(lkeep)<9:continue
                lclass=classify_removed(lrem,lkeep,leid,reid)
                if lclass is None:continue
                ltor,_ldrop=lclass
                for rl,rr in cuts:
                    rkeep,rrem=split_rows(right,rl,rr)
                    if rkeep is None or len(rkeep)<9:continue
                    rclass=classify_removed(rrem,rkeep,reid,leid)
                    if rclass is None:continue
                    rtol,_rdrop=rclass
                    if not ltor and not rtol:continue
                    ldest_ids={row_pid(x) for x in lkeep};ldest_ids.discard(None)
                    rdest_ids={row_pid(x) for x in rkeep};rdest_ids.discard(None)
                    # If the transferred PID already exists on the destination side, it is a duplicate
                    # representation rather than a missing row. v118 already handles duplicate drops.
                    if any(row_pid(x) in rdest_ids for x in ltor):continue
                    if any(row_pid(x) in ldest_ids for x in rtol):continue
                    repaired_left=list(lkeep)+list(rtol)
                    repaired_right=list(rkeep)+list(ltor)
                    if len(repaired_left)<9 or len(repaired_right)<9:continue
                    ls=support_ids(repaired_left,leid);rs=support_ids(repaired_right,reid)
                    if not ls or not rs:continue
                    dl=direct_anchor_club(ids_of(repaired_left));dr=direct_anchor_club(ids_of(repaired_right))
                    if (dl is not None and dl!=leid) or (dr is not None and dr!=reid):
                        diagnostics['confirmed_id_edge_transfer_current_conflicts_rejected']+=1;continue
                    moved=len(ltor)+len(rtol);trimmed=ll+lr+rl+rr
                    strength=min(ls[0],rs[0])
                    out.append((trimmed,-moved,-strength,ll,lr,rl,rr,repaired_left,repaired_right,moved))
            out.sort(key=lambda x:x[:7])
            return out

        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            if len(ids_of(c.get('left') or []))<9 or len(ids_of(c.get('right') or []))<9:continue
            valid={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                for rev,leid,reid in ((False,heid,aeid),(True,aeid,heid)):
                    states=repaired_states(c,leid,reid)
                    for state in states:
                        repaired_left,repaired_right=state[7],state[8]
                        repaired=dict(c);repaired['left']=repaired_left;repaired['right']=repaired_right
                        lscore,rscore=score_of(repaired)
                        score_ok=(lscore==as_ and rscore==hs) if rev else (lscore==hs and rscore==as_)
                        if not score_ok:continue
                        key=(fk,rev)
                        if key not in valid or state[:7]<valid[key][0][:7]:
                            valid[key]=(state,f,rev,leid,reid,(lscore,rscore),score_of(c))
            if len(valid)==1:
                state,f,rev,leid,reid,repaired_score,original_score=next(iter(valid.values()))
                proposals.append((state[0],-state[9],state[2],ci,f,rev,leid,reid,state,repaired_score,original_score))
            elif len(valid)>1:
                diagnostics['confirmed_id_edge_transfer_ambiguities_rejected']+=1

        proposals.sort(key=lambda x:(x[0],x[1],x[2],x[3]));added=0
        for _trim,_negmoved,_negstrength,ci,f,rev,leid,reid,state,repaired_score,original_score in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            original=cached[ci]
            repaired=dict(original);repaired['left']=list(state[7]);repaired['right']=list(state[8])
            cached[ci]=repaired
            try:
                ok=register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_transfer_v119')
            finally:
                cached[ci]=original
            if ok:
                added+=1
                diagnostics['confirmed_id_edge_transfer_matches']+=1
                diagnostics['confirmed_id_edge_transfer_rows_moved']+=state[9]
                diagnostics['confirmed_id_edge_transfer_rows_trimmed']+=state[0]
                if original_score!=repaired_score:diagnostics['confirmed_id_edge_transfer_score_changed_matches']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_edge_transfer_pair_pass():' not in py:
    if anchor not in py:raise RuntimeError('v119 insertion anchor missing')
    py=py.replace(anchor,insert,1)

# Add counters next to the existing edge-trim diagnostics.
diag="    diagnostics.setdefault('confirmed_id_edge_trim_target_duplicate_matches',0)\n"
extra=(diag+
"    diagnostics.setdefault('confirmed_id_edge_transfer_matches',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_transfer_rows_moved',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_transfer_rows_trimmed',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_transfer_score_changed_matches',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_transfer_ambiguities_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_transfer_current_conflicts_rejected',0)\n")
if "diagnostics.setdefault('confirmed_id_edge_transfer_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v119 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

# Run v119 immediately after v117/v118 edge trimming inside the same fixed-point loop.
old=';p=confirmed_id_fixture_conditioned_pair_pass();d=confirmed_id_fixture_conditioned_global_pass();e=confirmed_id_edge_trim_pair_pass();l=confirmed_id_local_anchor_pass();'
new=';p=confirmed_id_fixture_conditioned_pair_pass();d=confirmed_id_fixture_conditioned_global_pass();e=confirmed_id_edge_trim_pair_pass();f=confirmed_id_edge_transfer_pair_pass();l=confirmed_id_local_anchor_pass();'
if 'f=confirmed_id_edge_transfer_pair_pass()' not in py:
    if old not in py:raise RuntimeError('v119 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old2=' or p or d or e or l or t or z or u or v:'
new2=' or p or d or e or f or l or t or z or u or v:'
if ' or p or d or e or f or l or t or z or u or v:' not in py:
    if old2 not in py:raise RuntimeError('v119 fixed-point condition anchor missing')
    py=py.replace(old2,new2,1)
old3='+p+d+e+l+t+z+u+v'
new3='+p+d+e+f+l+t+z+u+v'
if '+p+d+e+f+l+t+z+u+v' not in py:
    if old3 not in py:raise RuntimeError('v119 fixed-point total anchor missing')
    py=py.replace(old3,new3,1)

handoff="'unlabelled_rich_confirmed_id_edge_trim_target_duplicate_matches':member_rich_diag.get('confirmed_id_edge_trim_target_duplicate_matches',0),"
extra=(handoff+
"'unlabelled_rich_confirmed_id_edge_transfer_matches':member_rich_diag.get('confirmed_id_edge_transfer_matches',0),"
"'unlabelled_rich_confirmed_id_edge_transfer_rows_moved':member_rich_diag.get('confirmed_id_edge_transfer_rows_moved',0),"
"'unlabelled_rich_confirmed_id_edge_transfer_rows_trimmed':member_rich_diag.get('confirmed_id_edge_transfer_rows_trimmed',0),"
"'unlabelled_rich_confirmed_id_edge_transfer_score_changed_matches':member_rich_diag.get('confirmed_id_edge_transfer_score_changed_matches',0),"
"'unlabelled_rich_confirmed_id_edge_transfer_ambiguities_rejected':member_rich_diag.get('confirmed_id_edge_transfer_ambiguities_rejected',0),"
"'unlabelled_rich_confirmed_id_edge_transfer_current_conflicts_rejected':member_rich_diag.get('confirmed_id_edge_transfer_current_conflicts_rejected',0),")
if 'unlabelled_rich_confirmed_id_edge_transfer_matches' not in py:
    if handoff not in py:raise RuntimeError('v119 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_id_edge_transfer_pair_pass():',
    'if len(owners)==1 and opposite_eid in owners:',
    'if any(row_pid(x) in rdest_ids for x in ltor):continue',
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_transfer_v119')",
    'f=confirmed_id_edge_transfer_pair_pass()',
    'confirmed_id_edge_transfer_rows_moved',
    'unlabelled_rich_confirmed_id_edge_transfer_matches',
]:assert s in cpy,s
print('v119 opposite-club retained edge-row transfer recovery applied')
