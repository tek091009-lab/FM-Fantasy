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
if 'def confirmed_name_global_constraint_pass():' not in py or 'confirmed_retained_name_clubs=collections.defaultdict(set)' not in py:
    raise RuntimeError('v99-v102 exact-name stack must exist before v103')

anchor="    def single_side_bridge_pass():\n"
insert="""    def _fixture_conditioned_name_support(rows,ids,target_eid):
        # v103: test exact retained-name evidence AGAINST a proposed authoritative fixture club
        # rather than requiring the side to choose a club in isolation first. This is useful when
        # neither side reaches v100's independent five-name seed, but BOTH sides strongly support
        # one real fixture. Multi-club/transfer aliases can reinforce only after unique aliases have
        # already supported target_eid; they can never establish the target club themselves.
        unique_votes=collections.Counter();ambiguous=[];seen=set();usable_unique=0
        for row in rows:
            key=_retained_name_key(row)
            if not key or key in seen:continue
            seen.add(key)
            owners=confirmed_retained_name_clubs.get(key,set())
            if len(owners)==1:
                usable_unique+=1;unique_votes[next(iter(owners))]+=1
            elif len(owners)>1:
                ambiguous.append(owners)
        target_n=unique_votes.get(target_eid,0)
        other_n=max((n for eid,n in unique_votes.items() if eid!=target_eid),default=0)
        # Four independently confirmed exact names per side. Require >=80% agreement among
        # uniquely-owned aliases and a three-name lead. This is weaker than v100 only in raw seed
        # count, but v103 requires the SAME proof on both sides plus one authoritative fixture.
        if target_n<4 or usable_unique<4:return None
        if target_n/max(1,usable_unique)<0.80:return None
        if target_n-other_n<3:return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=target_eid:
            diagnostics['confirmed_name_fixture_conditioned_conflicts_rejected']+=1;return None
        transfer_support=sum(1 for owners in ambiguous if target_eid in owners)
        total=target_n+transfer_support
        # Keep useful coverage across the side; transfer-compatible aliases cannot satisfy the
        # four-name decisive seed above.
        if total/max(1,len(rows))<0.24:return None
        return total,target_n,usable_unique

    def confirmed_name_fixture_conditioned_pair_pass():
        # Evaluate unresolved retained candidates against unused authoritative played fixtures
        # with the exact retained score. Accept only when exactly ONE fixture is supported on BOTH
        # sides. No fuzzy names, score-only matching, or speculative aliases are allowed.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right']);lscore,rscore=score_of(c)
            passing=[]
            for heid,aeid,hs,as_,f in played:
                if fixture_identity(f) in used_fixtures:continue
                # Native orientation.
                if lscore==hs and rscore==as_:
                    ls=_fixture_conditioned_name_support(c['left'],lids,heid)
                    rs=_fixture_conditioned_name_support(c['right'],rids,aeid)
                    if ls and rs:passing.append((f,False,heid,aeid,ls,rs))
                # Reversed retained-side orientation.
                if lscore==as_ and rscore==hs:
                    ls=_fixture_conditioned_name_support(c['left'],lids,aeid)
                    rs=_fixture_conditioned_name_support(c['right'],rids,heid)
                    if ls and rs:passing.append((f,True,aeid,heid,ls,rs))
            uniq={fixture_identity(x[0]):x for x in passing}
            if len(uniq)==1:
                opt=next(iter(uniq.values()));ls,rs=opt[4],opt[5]
                decisive_total=ls[1]+rs[1];support_total=ls[0]+rs[0]
                proposals.append((decisive_total,support_total,ci,opt))
            elif len(uniq)>1:
                diagnostics['confirmed_name_fixture_conditioned_ambiguities_rejected']+=1
        proposals.sort(reverse=True);added=0
        for _decisive,_support,ci,opt in proposals:
            f,rev,leid,reid,ls,rs=opt
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_fixture_conditioned_exact_name_pair'):
                added+=1
                diagnostics['confirmed_name_fixture_conditioned_pair_matches']+=1
                diagnostics['confirmed_name_fixture_conditioned_decisive_name_uses']+=ls[1]+rs[1]
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_fixture_conditioned_pair_pass():' not in py:
    if anchor not in py:raise RuntimeError('v103 pass anchor missing')
    py=py.replace(anchor,insert,1)

diag="    diagnostics.setdefault('confirmed_name_global_nonunique_components_rejected',0)\n"
extra=diag+"    diagnostics.setdefault('confirmed_name_fixture_conditioned_pair_matches',0)\n    diagnostics.setdefault('confirmed_name_fixture_conditioned_ambiguities_rejected',0)\n    diagnostics.setdefault('confirmed_name_fixture_conditioned_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_name_fixture_conditioned_decisive_name_uses',0)\n"
if "diagnostics.setdefault('confirmed_name_fixture_conditioned_pair_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v103 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j\n"
new_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();k=confirmed_name_fixture_conditioned_pair_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k\n"
if 'k=confirmed_name_fixture_conditioned_pair_pass()' not in py:
    if old_loop not in py:raise RuntimeError('v103 fixed-point loop anchor missing')
    py=py.replace(old_loop,new_loop,1)

handoff="'unlabelled_rich_confirmed_name_global_nonunique_components_rejected':member_rich_diag.get('confirmed_name_global_nonunique_components_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_fixture_conditioned_pair_matches':member_rich_diag.get('confirmed_name_fixture_conditioned_pair_matches',0),'unlabelled_rich_confirmed_name_fixture_conditioned_ambiguities_rejected':member_rich_diag.get('confirmed_name_fixture_conditioned_ambiguities_rejected',0),'unlabelled_rich_confirmed_name_fixture_conditioned_conflicts_rejected':member_rich_diag.get('confirmed_name_fixture_conditioned_conflicts_rejected',0),'unlabelled_rich_confirmed_name_fixture_conditioned_decisive_name_uses':member_rich_diag.get('confirmed_name_fixture_conditioned_decisive_name_uses',0),"
if 'unlabelled_rich_confirmed_name_fixture_conditioned_pair_matches' not in py:
    if handoff not in py:raise RuntimeError('v103 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def _fixture_conditioned_name_support(rows,ids,target_eid):',
    'if target_n<4 or usable_unique<4:return None',
    'if target_n/max(1,usable_unique)<0.80:return None',
    'if target_n-other_n<3:return None',
    'def confirmed_name_fixture_conditioned_pair_pass():',
    "'unlabelled_retained_fixture_conditioned_exact_name_pair'",
    'k=confirmed_name_fixture_conditioned_pair_pass()',
    'unlabelled_rich_confirmed_name_fixture_conditioned_pair_matches',
    'def confirmed_name_global_constraint_pass():',
    'def confirmed_name_one_side_pass():',
    'confirmed_name_transfer_support_uses'
]:assert s in cpy,s
print('v103 fixture-conditioned exact-name pair recovery applied')