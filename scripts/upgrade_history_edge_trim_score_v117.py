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
for req in ['def confirmed_id_edge_trim_pair_pass():','proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)','def confirmed_id_fixture_conditioned_pair_pass():']:
    if req not in py:raise RuntimeError('v117 prerequisite missing: '+req)

start=py.find('    def confirmed_id_edge_trim_pair_pass():\n')
end=py.find('    def confirmed_name_transitive_graph_pass():\n',start)
if start<0 or end<0:raise RuntimeError('v117 edge-trim function boundaries missing')

# v117 repairs the other half of the boundary problem. v115/v116 could trim edge rows for
# club identity, but fixture matching and register_match still saw the original untrimmed rows.
# A stray neighbouring player carrying a goal/own-goal could therefore keep the retained score
# wrong even after identity was repaired. v117 evaluates score on each bounded safe trim state,
# and, only for the uniquely accepted fixture, temporarily presents that repaired candidate to
# register_match so the contaminating row cannot leak into recovered player statistics.
func="""    def confirmed_id_edge_trim_pair_pass():
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

        def trim_rows(rows,state):
            rows=list(rows or []);cl=state['left_cut'];cr=state['right_cut']
            return rows[cl:len(rows)-cr if cr else None]

        def trim_options(rows,target_eid):
            rows=list(rows or [])
            if len(rows)<9:return []
            out=[]
            # Boundary-only repair: <=2 edge rows total. No interior combinatorial deletion.
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
                    # Never trim away a player uniquely proven for the proposed target club.
                    if len(owners)==1 and target_eid in owners:
                        safe=False;break
                if not safe:continue
                sup=support_ids(ids_of(kept),target_eid)
                if sup:
                    out.append({'trim':cut_l+cut_r,'left_cut':cut_l,'right_cut':cut_r,'support':sup})
            return out

        option_cache={}
        def side_options(ci,is_left,target_eid):
            key=(ci,is_left,target_eid)
            if key not in option_cache:
                c=cached[ci];rows=c['left'] if is_left else c['right']
                option_cache[key]=trim_options(rows,target_eid)
            return option_cache[key]

        def orientation_repairs(ci,heid,aeid,hs,as_,rev):
            c=cached[ci]
            leid,reid=(aeid,heid) if rev else (heid,aeid)
            out=[]
            for ls in side_options(ci,True,leid):
                lrows=trim_rows(c['left'],ls)
                dl=direct_anchor_club(ids_of(lrows))
                if dl is not None and dl!=leid:
                    diagnostics['confirmed_id_edge_trim_current_conflicts_rejected']+=1;continue
                for rs in side_options(ci,False,reid):
                    if not (ls['trim']>0 or rs['trim']>0):continue
                    rrows=trim_rows(c['right'],rs)
                    dr=direct_anchor_club(ids_of(rrows))
                    if dr is not None and dr!=reid:
                        diagnostics['confirmed_id_edge_trim_current_conflicts_rejected']+=1;continue
                    repaired=dict(c);repaired['left']=lrows;repaired['right']=rrows
                    lscore,rscore=score_of(repaired)
                    score_ok=(lscore==as_ and rscore==hs) if rev else (lscore==hs and rscore==as_)
                    if not score_ok:continue
                    trims=ls['trim']+rs['trim']
                    strength=min(ls['support'][0],rs['support'][0])
                    out.append((trims,-strength,ls['left_cut'],ls['right_cut'],rs['left_cut'],rs['right_cut'],ls,rs,lrows,rrows,(lscore,rscore)))
            if not out:return None
            out.sort(key=lambda x:x[:6])
            return out[0]

        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            if len(ids_of(c['left']))<9 or len(ids_of(c['right']))<9:continue
            original_score=score_of(c);valid={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                normal=orientation_repairs(ci,heid,aeid,hs,as_,False)
                if normal:
                    trims,negstrength,*rest=normal
                    ls,rs,lrows,rrows,repaired_score=rest[-5:]
                    valid[(fk,False)]=(f,False,heid,aeid,ls,rs,lrows,rrows,repaired_score,original_score)
                reversed_=orientation_repairs(ci,heid,aeid,hs,as_,True)
                if reversed_:
                    trims,negstrength,*rest=reversed_
                    ls,rs,lrows,rrows,repaired_score=rest[-5:]
                    valid[(fk,True)]=(f,True,aeid,heid,ls,rs,lrows,rrows,repaired_score,original_score)
            if len(valid)==1:
                f,rev,leid,reid,ls,rs,lrows,rrows,repaired_score,original_score=next(iter(valid.values()))
                trims=ls['trim']+rs['trim'];strength=min(ls['support'][0],rs['support'][0])
                proposals.append((-trims,strength,ci,f,rev,leid,reid,ls,rs,lrows,rrows,repaired_score,original_score))
            elif len(valid)>1:
                diagnostics['confirmed_id_edge_trim_ambiguities_rejected']+=1

        # Deterministic scalar-only ordering from v116; fixture dictionaries never participate.
        proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True);added=0
        for _negtrim,_strength,ci,f,rev,leid,reid,ls,rs,lrows,rrows,repaired_score,original_score in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            original=cached[ci]
            repaired=dict(original);repaired['left']=list(lrows);repaired['right']=list(rrows)
            # register_match must validate and materialise the repaired representation, not the
            # contaminated scan window. Restore cached afterwards for audit/debug reproducibility.
            cached[ci]=repaired
            try:
                ok=register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_trim_score_v117')
            finally:
                cached[ci]=original
            if ok:
                added+=1
                diagnostics['confirmed_id_edge_trim_matches']+=1
                diagnostics['confirmed_id_edge_trim_score_recomputed_matches']+=1
                diagnostics['confirmed_id_edge_trim_rows_removed']+=ls['trim']+rs['trim']
                if original_score!=repaired_score:
                    diagnostics['confirmed_id_edge_trim_score_changed_matches']+=1
                if ls['trim'] and rs['trim']:diagnostics['confirmed_id_edge_trim_both_sides']+=1
        return added

"""
py=py[:start]+func+py[end:]

# Add v117-specific counters alongside existing v115 diagnostics.
diag="    diagnostics.setdefault('confirmed_id_edge_trim_matches',0)\n"
extra=(diag+
"    diagnostics.setdefault('confirmed_id_edge_trim_score_recomputed_matches',0)\n"
"    diagnostics.setdefault('confirmed_id_edge_trim_score_changed_matches',0)\n")
if "diagnostics.setdefault('confirmed_id_edge_trim_score_recomputed_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v117 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

handoff="'unlabelled_rich_confirmed_id_edge_trim_matches':member_rich_diag.get('confirmed_id_edge_trim_matches',0),"
extra=(handoff+
"'unlabelled_rich_confirmed_id_edge_trim_score_recomputed_matches':member_rich_diag.get('confirmed_id_edge_trim_score_recomputed_matches',0),"
"'unlabelled_rich_confirmed_id_edge_trim_score_changed_matches':member_rich_diag.get('confirmed_id_edge_trim_score_changed_matches',0),")
if 'unlabelled_rich_confirmed_id_edge_trim_score_recomputed_matches' not in py:
    if handoff not in py:raise RuntimeError('v117 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_id_edge_trim_pair_pass():',
    'def trim_options(rows,target_eid):',
    'def orientation_repairs(ci,heid,aeid,hs,as_,rev):',
    'repaired=dict(c);repaired[\'left\']=lrows;repaired[\'right\']=rrows',
    'lscore,rscore=score_of(repaired)',
    "cached[ci]=repaired",
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_trim_score_v117')",
    "cached[ci]=original",
    'confirmed_id_edge_trim_score_changed_matches',
    'proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)'
]:assert s in cpy,s
print('v117 boundary-repaired score and player rows applied')