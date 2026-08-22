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
for req in ['def _retained_side_name_set(rows):','confirmed_retained_name_side_cohorts=collections.defaultdict(list)','def confirmed_name_roster_global_constraint_pass():']:
    if req not in py:raise RuntimeError('v109 prerequisite missing: '+req)

# v109 attacks a specific rotation failure left after v106-v108: an unresolved side may not
# overlap any ONE confirmed lineup/accumulated roster enough, even though it is connected to
# confirmed lineups through a chain of very-high-overlap retained sides. We build that graph
# without assigning club labels to speculative sides. Club authority comes ONLY from confirmed
# cohorts created after register_match(). A component is usable only when >=2 confirmed anchor
# cohorts agree on exactly one club and NO confirmed anchor from another club is present.
anchor='    def confirmed_name_cohort_fixture_pass():\n'
insert="""    def confirmed_name_transitive_graph_pass():
        # Build unresolved side nodes plus authoritative confirmed name-cohort anchors.
        side_nodes=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            for is_left,key in ((True,'left'),(False,'right')):
                names=_retained_side_name_set(c[key])
                if len(names)>=10:
                    side_nodes.append({'ci':ci,'left':is_left,'names':names,'ids':ids_of(c[key]),'anchor':None})
        anchor_nodes=[]
        for eid,cohorts in confirmed_retained_name_side_cohorts.items():
            for names in cohorts:
                if len(names)>=10:
                    anchor_nodes.append({'ci':None,'left':None,'names':set(names),'ids':set(),'anchor':eid})
        nodes=side_nodes+anchor_nodes
        if len(side_nodes)<1 or len(anchor_nodes)<2:return 0

        # Inverted-name index avoids an O(N^2) all-pairs pass. Only pairs sharing >=10 exact
        # canonical football names can form an edge, and they must also overlap >=55% of the
        # smaller side. Ten-player bridges cannot be created by one/two transferred players.
        by_name=collections.defaultdict(list)
        for ni,node in enumerate(nodes):
            for nm in node['names']:by_name[nm].append(ni)
        pair_shared=collections.Counter()
        for idxs in by_name.values():
            if len(idxs)>80:continue
            for a_pos in range(len(idxs)):
                a=idxs[a_pos]
                for b in idxs[a_pos+1:]:
                    if a>b:a,b=b,a
                    pair_shared[(a,b)]+=1
        parent=list(range(len(nodes)))
        def find(x):
            while parent[x]!=x:
                parent[x]=parent[parent[x]];x=parent[x]
            return x
        def union(a,b):
            ra,rb=find(a),find(b)
            if ra!=rb:parent[rb]=ra
        for (a,b),shared in pair_shared.items():
            if shared<10:continue
            denom=max(1,min(len(nodes[a]['names']),len(nodes[b]['names'])))
            if shared/denom<0.55:continue
            union(a,b)

        comp_anchor_counts=collections.defaultdict(collections.Counter)
        comp_sizes=collections.Counter()
        for ni,node in enumerate(nodes):
            r=find(ni);comp_sizes[r]+=1
            if node['anchor'] is not None:comp_anchor_counts[r][node['anchor']]+=1
        side_label={};conflict_components=set();qualified_components=set()
        for ni,node in enumerate(side_nodes):
            r=find(ni);anchors=comp_anchor_counts.get(r,collections.Counter())
            if not anchors:continue
            # Any authoritative cross-club anchor conflict makes the whole component unusable.
            if len(anchors)!=1:
                conflict_components.add(r);continue
            eid,n_anchor=next(iter(anchors.items()))
            if n_anchor<2:continue
            direct=direct_anchor_club(node['ids'])
            if direct is not None and direct!=eid:
                diagnostics['confirmed_name_transitive_conflicts_rejected']+=1;continue
            side_label[(node['ci'],node['left'])]=(eid,n_anchor,comp_sizes[r])
            qualified_components.add(r)
        diagnostics['confirmed_name_transitive_conflict_components_rejected']+=len(conflict_components)
        diagnostics['confirmed_name_transitive_qualified_components']+=len(qualified_components)
        if not side_label:return 0

        # First recover only when BOTH sides independently land in single-club anchored components.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if not lc or not rc:continue
            leid,la,_ls=lc;reid,ra,_rs=rc
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(la,ra),la+ra,ci,f,rev,le,re))
        proposals.sort(reverse=True);added=0
        for _mn,_sum,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_transitive_graph_v109'):
                added+=1;diagnostics['confirmed_name_transitive_fixture_matches']+=1

        # Then permit exactly-one-known-side cases only when club+exact score has ONE authoritative
        # unused fixture. The opponent is supplied by the calendar; graph inference never invents it.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc);eid,n_anchor,_sz=known
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
                f,rev,leid,reid=next(iter(local.values()));proposals.append((n_anchor,ci,f,rev,leid,reid))
            elif len(local)>1:diagnostics['confirmed_name_transitive_one_side_ambiguities_rejected']+=1
        proposals.sort(reverse=True)
        for _na,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_transitive_graph_one_side_v109'):
                added+=1;diagnostics['confirmed_name_transitive_one_side_fixture_matches']+=1
        return added

    def confirmed_name_cohort_fixture_pass():
"""
if 'def confirmed_name_transitive_graph_pass():' not in py:
    if anchor not in py:raise RuntimeError('v109 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_name_roster_global_nonunique_components_rejected',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_transitive_qualified_components',0)\n    diagnostics.setdefault('confirmed_name_transitive_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_transitive_one_side_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_transitive_one_side_ambiguities_rejected',0)\n    diagnostics.setdefault('confirmed_name_transitive_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_name_transitive_conflict_components_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_transitive_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v109 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=";w=confirmed_name_roster_fixture_pass();x=confirmed_name_roster_one_side_pass();y=confirmed_name_roster_global_constraint_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+u+v\n"
new=";w=confirmed_name_roster_fixture_pass();x=confirmed_name_roster_one_side_pass();y=confirmed_name_roster_global_constraint_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+z+u+v\n"
if 'z=confirmed_name_transitive_graph_pass()' not in py:
    if old not in py:raise RuntimeError('v109 fixed-point loop anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_name_roster_global_nonunique_components_rejected':member_rich_diag.get('confirmed_name_roster_global_nonunique_components_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_transitive_qualified_components':member_rich_diag.get('confirmed_name_transitive_qualified_components',0),'unlabelled_rich_confirmed_name_transitive_fixture_matches':member_rich_diag.get('confirmed_name_transitive_fixture_matches',0),'unlabelled_rich_confirmed_name_transitive_one_side_fixture_matches':member_rich_diag.get('confirmed_name_transitive_one_side_fixture_matches',0),'unlabelled_rich_confirmed_name_transitive_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_name_transitive_one_side_ambiguities_rejected',0),'unlabelled_rich_confirmed_name_transitive_conflicts_rejected':member_rich_diag.get('confirmed_name_transitive_conflicts_rejected',0),'unlabelled_rich_confirmed_name_transitive_conflict_components_rejected':member_rich_diag.get('confirmed_name_transitive_conflict_components_rejected',0),"
if 'unlabelled_rich_confirmed_name_transitive_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v109 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def confirmed_name_transitive_graph_pass():',
    "shared<10",
    'shared/denom<0.55',
    'if len(anchors)!=1:',
    'if n_anchor<2:continue',
    "'unlabelled_retained_confirmed_name_transitive_graph_v109'",
    "'unlabelled_retained_confirmed_name_transitive_graph_one_side_v109'",
    'z=confirmed_name_transitive_graph_pass()',
    'unlabelled_rich_confirmed_name_transitive_fixture_matches',
    'def confirmed_name_roster_global_constraint_pass():',
]:assert s in cpy,s
print('v109 transitive retained-name cohort graph recovery applied')