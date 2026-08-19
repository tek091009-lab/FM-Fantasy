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
if 'def confirmed_name_roster_one_side_pass():' not in py or 'def confirmed_name_roster_club(rows,ids):' not in py:
    raise RuntimeError('v107 accumulated retained-name roster recovery must exist before v108')

# v108 keeps v107's strict historical roster identity thresholds, but recovers a bounded
# set of locally ambiguous one-known-side candidates only when their candidate<->fixture
# graph has exactly one complete one-to-one assignment. No edge exists without v107 club
# evidence + exact score/orientation against an unused authoritative played fixture.
anchor='    def confirmed_name_cohort_fixture_pass():\n'
insert="""    def confirmed_name_roster_global_constraint_pass():
        edge_options={};strengths={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_name_roster_club(c['left'],lids);rc=confirmed_name_roster_club(c['right'],rids)
            # Stronger v107 two-sided and individually-unique one-sided routes run first.
            # v108 only considers exactly-one-known-side cases that remain locally ambiguous.
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc)
            eid,shared,repeated,coverage,_cohort_n=known
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
            # len==1 belongs to v107. Broad ambiguity remains unresolved rather than guessed.
            if 2<=len(local)<=8:
                edge_options[ci]=local
                strengths[ci]=(int(shared),int(repeated),float(coverage))
        if not edge_options:return 0

        fixture_to_candidates=collections.defaultdict(set)
        for ci,opts in edge_options.items():
            for fk in opts:fixture_to_candidates[fk].add(ci)
        visited=set();components=[]
        for start in sorted(edge_options):
            if start in visited:continue
            cs=set();fs=set();stack=[start]
            while stack:
                ci=stack.pop()
                if ci in cs:continue
                cs.add(ci);visited.add(ci)
                for fk in edge_options[ci]:
                    if fk in fs:continue
                    fs.add(fk)
                    stack.extend(x for x in fixture_to_candidates[fk] if x not in cs)
            components.append((cs,fs))

        def perfect_matching(cands,blocked=None):
            match_f={}
            def aug(ci,seen):
                for fk in sorted(edge_options[ci],key=repr):
                    if blocked is not None and blocked==(ci,fk):continue
                    if fk in seen:continue
                    seen.add(fk);prev=match_f.get(fk)
                    if prev is None or aug(prev,seen):
                        match_f[fk]=ci;return True
                return False
            for ci in sorted(cands,key=lambda x:(len(edge_options[x]),-strengths[x][0],-strengths[x][1],-strengths[x][2],x)):
                if not aug(ci,set()):return None
            return {ci:fk for fk,ci in match_f.items()}

        accepted=[]
        for cs,fs in components:
            if len(cs)<2:continue
            if len(cs)>12:
                diagnostics['confirmed_name_roster_global_oversized_components_rejected']+=1;continue
            if len(cs)!=len(fs):
                diagnostics['confirmed_name_roster_global_unbalanced_components_rejected']+=1;continue
            match=perfect_matching(cs)
            if match is None:
                diagnostics['confirmed_name_roster_global_no_perfect_match_rejected']+=1;continue
            # Prove uniqueness: remove each selected edge. If any complete alternative survives,
            # reject the whole connected component rather than selecting an arbitrary matching.
            unique=True
            for ci,fk in match.items():
                if perfect_matching(cs,(ci,fk)) is not None:
                    unique=False;break
            if not unique:
                diagnostics['confirmed_name_roster_global_nonunique_components_rejected']+=1;continue
            diagnostics['confirmed_name_roster_global_unique_components']+=1
            for ci,fk in match.items():accepted.append((strengths[ci],ci,edge_options[ci][fk]))

        accepted.sort(key=lambda x:(x[0][0],x[0][1],x[0][2]),reverse=True);added=0
        for _strength,ci,opt in accepted:
            f,rev,leid,reid=opt
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_roster_global_unique_v108'):
                added+=1;diagnostics['confirmed_name_roster_global_fixture_matches']+=1
        return added

    def confirmed_name_cohort_fixture_pass():
"""
if 'def confirmed_name_roster_global_constraint_pass():' not in py:
    if anchor not in py:raise RuntimeError('v108 pass anchor missing')
    py=py.replace(anchor,insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_name_roster_conflicts_rejected',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_roster_global_unique_components',0)\n    diagnostics.setdefault('confirmed_name_roster_global_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_roster_global_oversized_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_roster_global_unbalanced_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_roster_global_no_perfect_match_rejected',0)\n    diagnostics.setdefault('confirmed_name_roster_global_nonunique_components_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_roster_global_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v108 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=";s=confirmed_name_fixture_conditioned_global_pass();w=confirmed_name_roster_fixture_pass();x=confirmed_name_roster_one_side_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or w or x or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+u+v\n"
new=";s=confirmed_name_fixture_conditioned_global_pass();w=confirmed_name_roster_fixture_pass();x=confirmed_name_roster_one_side_pass();y=confirmed_name_roster_global_constraint_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+u+v\n"
if 'y=confirmed_name_roster_global_constraint_pass()' not in py:
    if old not in py:raise RuntimeError('v108 fixed-point loop anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_name_roster_conflicts_rejected':member_rich_diag.get('confirmed_name_roster_conflicts_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_roster_global_unique_components':member_rich_diag.get('confirmed_name_roster_global_unique_components',0),'unlabelled_rich_confirmed_name_roster_global_fixture_matches':member_rich_diag.get('confirmed_name_roster_global_fixture_matches',0),'unlabelled_rich_confirmed_name_roster_global_oversized_components_rejected':member_rich_diag.get('confirmed_name_roster_global_oversized_components_rejected',0),'unlabelled_rich_confirmed_name_roster_global_unbalanced_components_rejected':member_rich_diag.get('confirmed_name_roster_global_unbalanced_components_rejected',0),'unlabelled_rich_confirmed_name_roster_global_no_perfect_match_rejected':member_rich_diag.get('confirmed_name_roster_global_no_perfect_match_rejected',0),'unlabelled_rich_confirmed_name_roster_global_nonunique_components_rejected':member_rich_diag.get('confirmed_name_roster_global_nonunique_components_rejected',0),"
if 'unlabelled_rich_confirmed_name_roster_global_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v108 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_name_roster_global_constraint_pass():',
    '2<=len(local)<=8',
    'if len(cs)!=len(fs):',
    'perfect_matching(cs,(ci,fk))',
    "'unlabelled_retained_confirmed_name_roster_global_unique_v108'",
    'y=confirmed_name_roster_global_constraint_pass()',
    'unlabelled_rich_confirmed_name_roster_global_fixture_matches',
    'def confirmed_name_roster_one_side_pass():',
    'len(shared)>=8 and repeated>=4 and coverage>=0.44',
]:assert s in cpy,s
print('v108 globally unique accumulated retained-name roster recovery applied')
