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
if 'def confirmed_id_fixture_conditioned_pair_pass():' not in py:
    raise RuntimeError('v113 fixture-conditioned ID path must exist before v114')

anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_fixture_conditioned_global_pass():
        # v114: preserve locally ambiguous candidates from v113 as graph edges. Every edge still
        # requires two-sided historical PID support and an exact-score authoritative fixture.
        # A component is accepted only when the candidate<->fixture assignment is mathematically unique.
        pid_clubs=collections.defaultdict(set)
        for eid,cohorts in confirmed_side_cohorts.items():
            for cohort in cohorts:
                for pid in cohort:pid_clubs[int(pid)].add(eid)
        if not pid_clubs:return 0

        def side_support(ids,target_eid):
            ids={int(x) for x in ids if int(x)>0};target=0;usable=0;other=collections.Counter()
            for pid in ids:
                owners=pid_clubs.get(pid,set())
                # Multi-club/transfer IDs remain neutral exactly as in v113.
                if len(owners)!=1:continue
                usable+=1;owner=next(iter(owners))
                if owner==target_eid:target+=1
                else:other[owner]+=1
            if target<4 or usable<4:return None
            if target/max(1,usable)<0.80:return None
            other_n=max(other.values()) if other else 0
            if target-other_n<3:return None
            direct=direct_anchor_club(ids)
            if direct is not None and direct!=target_eid:
                diagnostics['confirmed_id_fixture_global_current_conflicts_rejected']+=1;return None
            return target,usable,other_n

        edges={};opts={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            if len(lids)<9 or len(rids)<9:continue
            lscore,rscore=score_of(c);local={};orientation_conflict=set()
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                if lscore==hs and rscore==as_:
                    ls=side_support(lids,heid);rs=side_support(rids,aeid)
                    if ls and rs and heid!=aeid:local[fk]=(f,False,heid,aeid,ls,rs)
                if lscore==as_ and rscore==hs:
                    ls=side_support(lids,aeid);rs=side_support(rids,heid)
                    if ls and rs and heid!=aeid:
                        cur=(f,True,aeid,heid,ls,rs);prev=local.get(fk)
                        if prev and (prev[2],prev[3])!=(cur[2],cur[3]):
                            orientation_conflict.add(fk);local.pop(fk,None)
                        elif not prev:local[fk]=cur
            if orientation_conflict:
                diagnostics['confirmed_id_fixture_global_orientation_conflicts']+=len(orientation_conflict)
            # v113 already consumes locally unique cases; v114 handles true bounded ambiguity only.
            if 2<=len(local)<=8:
                edges[ci]=set(local)
                for fk,opt in local.items():opts[(ci,fk)]=opt

        if not edges:return 0
        fixture_to_candidates=collections.defaultdict(set)
        for ci,fks in edges.items():
            for fk in fks:fixture_to_candidates[fk].add(ci)
        unseen=set(edges);components=[]
        while unseen:
            seed=unseen.pop();cs={seed};fs=set();queue=[seed]
            while queue:
                x=queue.pop()
                for fk in edges.get(x,set()):
                    if fk not in fs:
                        fs.add(fk)
                        for y in fixture_to_candidates.get(fk,set()):
                            if y not in cs:
                                cs.add(y);unseen.discard(y);queue.append(y)
            components.append((cs,fs))

        def perfect_matching(cs,forbidden=None):
            order=sorted(cs,key=lambda ci:len(edges[ci]));match_f={}
            def augment(ci,seen):
                for fk in sorted(edges[ci],key=repr):
                    if forbidden==(ci,fk) or fk in seen:continue
                    seen.add(fk)
                    if fk not in match_f or augment(match_f[fk],seen):
                        match_f[fk]=ci;return True
                return False
            for ci in order:
                if not augment(ci,set()):return None
            return {ci:fk for fk,ci in match_f.items()}

        accepted=[]
        for cs,fs in components:
            if len(cs)<2:continue
            if len(cs)>12:
                diagnostics['confirmed_id_fixture_global_oversized_components_rejected']+=1;continue
            if len(cs)!=len(fs):
                diagnostics['confirmed_id_fixture_global_unbalanced_components_rejected']+=1;continue
            chosen=perfect_matching(cs)
            if not chosen or len(chosen)!=len(cs):
                diagnostics['confirmed_id_fixture_global_no_perfect_match_rejected']+=1;continue
            unique=True
            for ci,fk in chosen.items():
                alt=perfect_matching(cs,(ci,fk))
                if alt and len(alt)==len(cs):unique=False;break
            if not unique:
                diagnostics['confirmed_id_fixture_global_nonunique_components_rejected']+=1;continue
            diagnostics['confirmed_id_fixture_global_unique_components']+=1
            accepted.extend(chosen.items())

        ranked=[]
        for ci,fk in accepted:
            opt=opts.get((ci,fk))
            if not opt:continue
            f,rev,leid,reid,ls,rs=opt
            ranked.append((min(ls[0],rs[0]),ls[0]+rs[0],ci,f,rev,leid,reid))
        ranked.sort(reverse=True);added=0
        for _strength,_coverage,ci,f,rev,leid,reid in ranked:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_fixture_conditioned_confirmed_id_global_v114'):
                added+=1;diagnostics['confirmed_id_fixture_global_matches']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_fixture_conditioned_global_pass():' not in py:
    if anchor not in py:raise RuntimeError('v114 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag="    diagnostics.setdefault('confirmed_id_fixture_conditioned_pair_matches',0)\n"
extra=(diag+
"    diagnostics.setdefault('confirmed_id_fixture_global_matches',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_unique_components',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_nonunique_components_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_unbalanced_components_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_no_perfect_match_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_oversized_components_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_current_conflicts_rejected',0)\n"
"    diagnostics.setdefault('confirmed_id_fixture_global_orientation_conflicts',0)\n")
if "diagnostics.setdefault('confirmed_id_fixture_global_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v114 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old=';y=confirmed_name_roster_global_constraint_pass();p=confirmed_id_fixture_conditioned_pair_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
new=';y=confirmed_name_roster_global_constraint_pass();p=confirmed_id_fixture_conditioned_pair_pass();d=confirmed_id_fixture_conditioned_global_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
if 'd=confirmed_id_fixture_conditioned_global_pass()' not in py:
    if old not in py:raise RuntimeError('v114 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or p or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+p+l+t+z+u+v\n"
new="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or p or d or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+p+d+l+t+z+u+v\n"
if '+y+p+d+l+t+z+u+v' not in py:
    if old not in py:raise RuntimeError('v114 fixed-point total anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_id_fixture_conditioned_pair_matches':member_rich_diag.get('confirmed_id_fixture_conditioned_pair_matches',0),"
extra=(handoff+
"'unlabelled_rich_confirmed_id_fixture_global_matches':member_rich_diag.get('confirmed_id_fixture_global_matches',0),"
"'unlabelled_rich_confirmed_id_fixture_global_unique_components':member_rich_diag.get('confirmed_id_fixture_global_unique_components',0),"
"'unlabelled_rich_confirmed_id_fixture_global_nonunique_components_rejected':member_rich_diag.get('confirmed_id_fixture_global_nonunique_components_rejected',0),"
"'unlabelled_rich_confirmed_id_fixture_global_unbalanced_components_rejected':member_rich_diag.get('confirmed_id_fixture_global_unbalanced_components_rejected',0),"
"'unlabelled_rich_confirmed_id_fixture_global_no_perfect_match_rejected':member_rich_diag.get('confirmed_id_fixture_global_no_perfect_match_rejected',0),"
"'unlabelled_rich_confirmed_id_fixture_global_oversized_components_rejected':member_rich_diag.get('confirmed_id_fixture_global_oversized_components_rejected',0),"
"'unlabelled_rich_confirmed_id_fixture_global_current_conflicts_rejected':member_rich_diag.get('confirmed_id_fixture_global_current_conflicts_rejected',0),"
"'unlabelled_rich_confirmed_id_fixture_global_orientation_conflicts':member_rich_diag.get('confirmed_id_fixture_global_orientation_conflicts',0),")
if 'unlabelled_rich_confirmed_id_fixture_global_matches' not in py:
    if handoff not in py:raise RuntimeError('v114 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_id_fixture_conditioned_global_pass():',
    'if target<4 or usable<4:return None',
    'if target/max(1,usable)<0.80:return None',
    'if target-other_n<3:return None',
    '2<=len(local)<=8',
    'if len(cs)!=len(fs):',
    'alt=perfect_matching(cs,(ci,fk))',
    "'unlabelled_retained_fixture_conditioned_confirmed_id_global_v114'",
    'd=confirmed_id_fixture_conditioned_global_pass()',
    'unlabelled_rich_confirmed_id_fixture_global_matches',
    'def confirmed_id_fixture_conditioned_pair_pass():',
    'def confirmed_id_local_anchor_pass():',
    'def confirmed_id_transitive_graph_pass():'
]:assert s in cpy,s
print('v114 globally constrained fixture-conditioned confirmed-ID recovery applied')
