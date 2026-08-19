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

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def confirmed_name_fixture_conditioned_pair_pass():' not in py:
    raise RuntimeError('v103 fixture-conditioned exact-name path must exist before v104')

anchor="    def single_side_bridge_pass():\n"
insert="""    def _fixture_conditioned_sparse_name_support(rows,ids,target_eid):
        # v104 is intentionally narrower semantically than v103 even though the raw seed is
        # three names instead of four: every uniquely-owned exact alias on the side must agree
        # with the proposed club. Multi-club aliases are ignored for the decisive seed and can
        # never create an edge. This helper only proposes graph edges; it cannot register a match.
        unique_votes=collections.Counter();seen=set();usable_unique=0
        for row in rows:
            key=_retained_name_key(row)
            if not key or key in seen:continue
            seen.add(key)
            owners=confirmed_retained_name_clubs.get(key,set())
            if len(owners)==1:
                usable_unique+=1;unique_votes[next(iter(owners))]+=1
        target_n=unique_votes.get(target_eid,0)
        other_n=sum(n for eid,n in unique_votes.items() if eid!=target_eid)
        # Three independently confirmed exact names, with ZERO contradictory unique aliases.
        if target_n<3 or usable_unique<3:return None
        if other_n:return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=target_eid:
            diagnostics['confirmed_name_sparse_global_conflicts_rejected']+=1;return None
        if target_n/max(1,len(rows))<0.14:return None
        return target_n,usable_unique

    def confirmed_name_fixture_conditioned_global_pass():
        # v104: locally ambiguous sparse exact-name candidates are admitted only as graph edges.
        # The component is recovered iff ALL candidates and fixtures form one mathematically
        # unique perfect matching. This never does score-only matching and never lowers v103's
        # direct acceptance threshold.
        edges={};opts_by_pair={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right']);lscore,rscore=score_of(c)
            local={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                if lscore==hs and rscore==as_:
                    ls=_fixture_conditioned_sparse_name_support(c['left'],lids,heid)
                    rs=_fixture_conditioned_sparse_name_support(c['right'],rids,aeid)
                    if ls and rs:local[fk]=(f,False,heid,aeid,ls,rs)
                if lscore==as_ and rscore==hs:
                    ls=_fixture_conditioned_sparse_name_support(c['left'],lids,aeid)
                    rs=_fixture_conditioned_sparse_name_support(c['right'],rids,heid)
                    if ls and rs:
                        # If both orientations somehow map the same authoritative fixture, do
                        # not silently pick an orientation unless they imply the same side clubs.
                        prev=local.get(fk)
                        cur=(f,True,aeid,heid,ls,rs)
                        if prev and (prev[2],prev[3])!=(cur[2],cur[3]):
                            local.pop(fk,None);diagnostics['confirmed_name_sparse_global_orientation_conflicts']+=1
                        elif not prev:local[fk]=cur
            # v103 already handles locally unique four-name cases. v104 exists only for true
            # ambiguity and keeps each candidate degree bounded to make uniqueness proof cheap.
            if 2<=len(local)<=8:
                edges[ci]=set(local);opts_by_pair.update({(ci,fk):opt for fk,opt in local.items()})

        if not edges:return 0
        # Build connected candidate<->fixture components.
        fixture_to_candidates=collections.defaultdict(set)
        for ci,fks in edges.items():
            for fk in fks:fixture_to_candidates[fk].add(ci)
        unseen=set(edges);components=[]
        while unseen:
            seed=unseen.pop();cs={seed};fs=set();cq=[seed]
            while cq:
                x=cq.pop()
                for fk in edges.get(x,set()):
                    if fk not in fs:
                        fs.add(fk)
                        for y in fixture_to_candidates.get(fk,set()):
                            if y not in cs:
                                cs.add(y);unseen.discard(y);cq.append(y)
            components.append((cs,fs))

        def perfect_matching(cs,forbidden=None):
            order=sorted(cs,key=lambda ci:len(edges[ci]));match_f={}
            def aug(ci,seen):
                for fk in sorted(edges[ci],key=repr):
                    if forbidden==(ci,fk) or fk in seen:continue
                    seen.add(fk)
                    if fk not in match_f or aug(match_f[fk],seen):
                        match_f[fk]=ci;return True
                return False
            for ci in order:
                if not aug(ci,set()):return None
            return {ci:fk for fk,ci in match_f.items()}

        accepted=[]
        for cs,fs in components:
            if len(cs)<2:continue
            if len(cs)>12:
                diagnostics['confirmed_name_sparse_global_oversized_components_rejected']+=1;continue
            if len(cs)!=len(fs):
                diagnostics['confirmed_name_sparse_global_unbalanced_components_rejected']+=1;continue
            chosen=perfect_matching(cs)
            if not chosen or len(chosen)!=len(cs):
                diagnostics['confirmed_name_sparse_global_no_perfect_match_rejected']+=1;continue
            # Prove uniqueness: deleting ANY chosen edge must destroy complete matchability.
            unique=True
            for ci,fk in chosen.items():
                alt=perfect_matching(cs,(ci,fk))
                if alt and len(alt)==len(cs):unique=False;break
            if not unique:
                diagnostics['confirmed_name_sparse_global_nonunique_components_rejected']+=1;continue
            diagnostics['confirmed_name_sparse_global_unique_components']+=1
            accepted.extend((ci,fk) for ci,fk in chosen.items())

        added=0
        # Register strongest sparse-name edges first; each still passes authoritative register_match.
        ranked=[]
        for ci,fk in accepted:
            opt=opts_by_pair.get((ci,fk))
            if not opt:continue
            f,rev,leid,reid,ls,rs=opt
            ranked.append((ls[0]+rs[0],ci,f,rev,leid,reid))
        ranked.sort(reverse=True,key=lambda x:x[0])
        for _support,ci,f,rev,leid,reid in ranked:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_fixture_conditioned_exact_name_global_v104'):
                added+=1;diagnostics['confirmed_name_sparse_global_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_fixture_conditioned_global_pass():' not in py:
    if anchor not in py:raise RuntimeError('v104 pass anchor missing')
    py=py.replace(anchor,insert,1)

diag="    diagnostics.setdefault('confirmed_name_fixture_conditioned_decisive_name_uses',0)\n"
extra=diag+"    diagnostics.setdefault('confirmed_name_sparse_global_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_unique_components',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_nonunique_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_unbalanced_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_no_perfect_match_rejected',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_oversized_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_name_sparse_global_orientation_conflicts',0)\n"
if "diagnostics.setdefault('confirmed_name_sparse_global_fixture_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v104 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();k=confirmed_name_fixture_conditioned_pair_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k\n"
new_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();k=confirmed_name_fixture_conditioned_pair_pass();s=confirmed_name_fixture_conditioned_global_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s\n"
if 's=confirmed_name_fixture_conditioned_global_pass()' not in py:
    if old_loop not in py:raise RuntimeError('v104 fixed-point loop anchor missing')
    py=py.replace(old_loop,new_loop,1)

handoff="'unlabelled_rich_confirmed_name_fixture_conditioned_decisive_name_uses':member_rich_diag.get('confirmed_name_fixture_conditioned_decisive_name_uses',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_sparse_global_fixture_matches':member_rich_diag.get('confirmed_name_sparse_global_fixture_matches',0),'unlabelled_rich_confirmed_name_sparse_global_unique_components':member_rich_diag.get('confirmed_name_sparse_global_unique_components',0),'unlabelled_rich_confirmed_name_sparse_global_nonunique_components_rejected':member_rich_diag.get('confirmed_name_sparse_global_nonunique_components_rejected',0),'unlabelled_rich_confirmed_name_sparse_global_unbalanced_components_rejected':member_rich_diag.get('confirmed_name_sparse_global_unbalanced_components_rejected',0),'unlabelled_rich_confirmed_name_sparse_global_no_perfect_match_rejected':member_rich_diag.get('confirmed_name_sparse_global_no_perfect_match_rejected',0),'unlabelled_rich_confirmed_name_sparse_global_oversized_components_rejected':member_rich_diag.get('confirmed_name_sparse_global_oversized_components_rejected',0),'unlabelled_rich_confirmed_name_sparse_global_conflicts_rejected':member_rich_diag.get('confirmed_name_sparse_global_conflicts_rejected',0),'unlabelled_rich_confirmed_name_sparse_global_orientation_conflicts':member_rich_diag.get('confirmed_name_sparse_global_orientation_conflicts',0),"
if 'unlabelled_rich_confirmed_name_sparse_global_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v104 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def _fixture_conditioned_sparse_name_support(rows,ids,target_eid):',
    'if target_n<3 or usable_unique<3:return None',
    'if other_n:return None',
    'def confirmed_name_fixture_conditioned_global_pass():',
    '2<=len(local)<=8',
    'if len(cs)!=len(fs):',
    'alt=perfect_matching(cs,(ci,fk))',
    "'unlabelled_retained_fixture_conditioned_exact_name_global_v104'",
    's=confirmed_name_fixture_conditioned_global_pass()',
    'unlabelled_rich_confirmed_name_sparse_global_fixture_matches',
    'def confirmed_name_fixture_conditioned_pair_pass():',
    'def confirmed_name_global_constraint_pass():',
    'def confirmed_roster_global_constraint_pass():'
]:assert s in cpy,s
print('v104 globally constrained sparse exact-name fixture recovery applied')