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
for req in ['confirmed_side_cohorts=collections.defaultdict(list)','def confirmed_id_transitive_graph_pass():','def confirmed_name_transitive_graph_pass():']:
    if req not in py:raise RuntimeError('v112 prerequisite missing: '+req)

# v112 targets a safe over-rejection in v111. A long transitive retained-ID component can be
# poisoned by one distant cross-club bridge and v111 correctly rejects the whole component.
# v112 does NOT relax that rule. Instead it separately labels an unresolved side only when that
# side itself has strong direct overlap with >=2 already-authoritative cohorts from exactly one
# club and with zero qualifying cohorts from every other club. This local proof is independent of
# the wider graph topology. It can therefore rescue locally certain sides from globally conflicted
# components without letting an unresolved/speculative side teach club identity.
anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_local_anchor_pass():
        # Build only from cohorts created after authoritative register_match() success.
        anchor_by_club={}
        for eid,cohorts in confirmed_side_cohorts.items():
            good=[set(ids) for ids in cohorts if len(ids)>=9]
            if len(good)>=2:anchor_by_club[eid]=good
        if not anchor_by_club:return 0

        side_label={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            for is_left,key in ((True,'left'),(False,'right')):
                ids=set(ids_of(c[key]))
                if len(ids)<9:continue
                qualifying=[]
                for eid,cohorts in anchor_by_club.items():
                    matches=[]
                    for cohort in cohorts:
                        shared=len(ids & cohort)
                        denom=max(1,min(len(ids),len(cohort)))
                        # Each supporting cohort must independently be a strong local lineup match.
                        if shared>=7 and shared/denom>=0.40:
                            matches.append(shared)
                    if len(matches)>=2:
                        qualifying.append((eid,len(matches),sum(matches),max(matches)))
                # Exact local exclusivity: one club only. Any second qualifying club rejects.
                if len(qualifying)!=1:
                    if len(qualifying)>1:diagnostics['confirmed_id_local_anchor_cross_club_rejected']+=1
                    continue
                eid,nmatch,total,best=qualifying[0]
                direct=direct_anchor_club(ids)
                if direct is not None and direct!=eid:
                    diagnostics['confirmed_id_local_anchor_current_conflicts_rejected']+=1;continue
                side_label[(ci,is_left)]=(eid,nmatch,total,best)
        if not side_label:return 0

        added=0
        # Strongest route first: both sides independently prove different clubs locally.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if not lc or not rc:continue
            leid,ln,lt,lb=lc;reid,rn,rt,rb=rc
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:
                if len(opts)>1:diagnostics['confirmed_id_local_anchor_fixture_ambiguities_rejected']+=1
                continue
            f,rev,le,re=opts[0]
            proposals.append((min(ln,rn),lt+rt,min(lb,rb),ci,f,rev,le,re))
        proposals.sort(reverse=True)
        for _n,_sum,_best,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_local_anchor_v112'):
                added+=1;diagnostics['confirmed_id_local_anchor_fixture_matches']+=1

        # Conservative one-side bridge: one locally certain club + exact score must leave exactly
        # one unused authoritative fixture. The calendar supplies the opponent; no ID guess does.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc);eid,nmatch,total,best=known
            lscore,rscore=score_of(c);local={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                opt=None
                if known_left:
                    if eid==heid and lscore==hs and rscore==as_:opt=(f,False,heid,aeid)
                    elif eid==aeid and lscore==as_ and rscore==hs:opt=(f,True,aeid,heid)
                else:
                    if eid==aeid and lscore==hs and rscore==as_:opt=(f,False,heid,aeid)
                    elif eid==heid and lscore==as_ and rscore==hs:opt=(f,True,aeid,heid)
                if opt is not None:local[fk]=opt
            if len(local)==1:
                f,rev,leid,reid=next(iter(local.values()));proposals.append((nmatch,total,best,ci,f,rev,leid,reid))
            elif len(local)>1:diagnostics['confirmed_id_local_anchor_one_side_ambiguities_rejected']+=1
        proposals.sort(reverse=True)
        for _n,_sum,_best,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_local_anchor_one_side_v112'):
                added+=1;diagnostics['confirmed_id_local_anchor_one_side_fixture_matches']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_local_anchor_pass():' not in py:
    if anchor not in py:raise RuntimeError('v112 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_id_transitive_qualified_components',0)\n"
diag_new=("    diagnostics.setdefault('confirmed_id_local_anchor_fixture_matches',0)\n"
          "    diagnostics.setdefault('confirmed_id_local_anchor_one_side_fixture_matches',0)\n"
          "    diagnostics.setdefault('confirmed_id_local_anchor_cross_club_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_local_anchor_current_conflicts_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_local_anchor_fixture_ambiguities_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_local_anchor_one_side_ambiguities_rejected',0)\n"+diag_anchor)
if "diagnostics.setdefault('confirmed_id_local_anchor_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v112 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=';y=confirmed_name_roster_global_constraint_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
new=';y=confirmed_name_roster_global_constraint_pass();l=confirmed_id_local_anchor_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
if 'l=confirmed_id_local_anchor_pass()' not in py:
    if old not in py:raise RuntimeError('v112 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+t+z+u+v\n"
new="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or l or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+l+t+z+u+v\n"
if '+y+l+t+z+u+v' not in py:
    if old not in py:raise RuntimeError('v112 fixed-point total anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_id_transitive_qualified_components':member_rich_diag.get('confirmed_id_transitive_qualified_components',0),"
extra=("'unlabelled_rich_confirmed_id_local_anchor_fixture_matches':member_rich_diag.get('confirmed_id_local_anchor_fixture_matches',0),"
       "'unlabelled_rich_confirmed_id_local_anchor_one_side_fixture_matches':member_rich_diag.get('confirmed_id_local_anchor_one_side_fixture_matches',0),"
       "'unlabelled_rich_confirmed_id_local_anchor_cross_club_rejected':member_rich_diag.get('confirmed_id_local_anchor_cross_club_rejected',0),"
       "'unlabelled_rich_confirmed_id_local_anchor_current_conflicts_rejected':member_rich_diag.get('confirmed_id_local_anchor_current_conflicts_rejected',0),"
       "'unlabelled_rich_confirmed_id_local_anchor_fixture_ambiguities_rejected':member_rich_diag.get('confirmed_id_local_anchor_fixture_ambiguities_rejected',0),"
       "'unlabelled_rich_confirmed_id_local_anchor_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_id_local_anchor_one_side_ambiguities_rejected',0),"+handoff)
if 'unlabelled_rich_confirmed_id_local_anchor_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v112 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_id_local_anchor_pass():','shared>=7 and shared/denom>=0.40','if len(matches)>=2:','if len(qualifying)!=1:',"'unlabelled_retained_confirmed_id_local_anchor_v112'","'unlabelled_retained_confirmed_id_local_anchor_one_side_v112'",'l=confirmed_id_local_anchor_pass()','unlabelled_rich_confirmed_id_local_anchor_fixture_matches','def confirmed_id_transitive_graph_pass():']:
    assert s in cpy,s
print('v112 local retained-ID authoritative-anchor recovery applied')
