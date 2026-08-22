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
for req in ['confirmed_side_cohorts=collections.defaultdict(list)','def confirmed_roster_club(ids):','def confirmed_name_transitive_graph_pass():']:
    if req not in py:raise RuntimeError('v111 prerequisite missing: '+req)

# v111 targets saves where retained football-name/header evidence is absent but player IDs are
# abundant and stable within retained history. It propagates club identity through chains of
# very-high-overlap retained ID lineups. Authority comes ONLY from cohorts created after an
# authoritative register_match() success; unresolved sides may connect the graph but never teach
# a club label. Any authoritative cross-club anchor in the same component rejects the component.
anchor='    def confirmed_name_transitive_graph_pass():\n'
insert="""    def confirmed_id_transitive_graph_pass():
        side_nodes=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            for is_left,key in ((True,'left'),(False,'right')):
                ids=ids_of(c[key])
                if len(ids)>=9:
                    side_nodes.append({'ci':ci,'left':is_left,'ids':set(ids),'anchor':None})
        anchor_nodes=[]
        for eid,cohorts in confirmed_side_cohorts.items():
            # >=2 cohorts means this club has been independently confirmed in >=2 distinct
            # authoritative fixtures because register_match() consumes a fixture once.
            if len(cohorts)<2:continue
            for ids in cohorts:
                if len(ids)>=9:
                    anchor_nodes.append({'ci':None,'left':None,'ids':set(ids),'anchor':eid})
        nodes=side_nodes+anchor_nodes
        if not side_nodes or len(anchor_nodes)<2:return 0

        by_pid=collections.defaultdict(list)
        for ni,node in enumerate(nodes):
            for pid in node['ids']:by_pid[pid].append(ni)
        pair_shared=collections.Counter()
        for idxs in by_pid.values():
            # A player appearing in implausibly many sides is non-discriminating evidence.
            if len(idxs)>80:continue
            for ap in range(len(idxs)):
                a=idxs[ap]
                for b in idxs[ap+1:]:
                    aa,bb=(a,b) if a<b else (b,a)
                    pair_shared[(aa,bb)]+=1

        parent=list(range(len(nodes)))
        def find(x):
            while parent[x]!=x:
                parent[x]=parent[parent[x]];x=parent[x]
            return x
        def union(a,b):
            ra,rb=find(a),find(b)
            if ra!=rb:parent[rb]=ra
        for (a,b),shared in pair_shared.items():
            if shared<8:continue
            denom=max(1,min(len(nodes[a]['ids']),len(nodes[b]['ids'])))
            if shared/denom<0.45:continue
            union(a,b)

        comp_anchors=collections.defaultdict(collections.Counter)
        comp_sizes=collections.Counter()
        for ni,node in enumerate(nodes):
            r=find(ni);comp_sizes[r]+=1
            if node['anchor'] is not None:comp_anchors[r][node['anchor']]+=1
        side_label={};conflicts=set();qualified=set()
        for ni,node in enumerate(side_nodes):
            r=find(ni);anchors=comp_anchors.get(r,collections.Counter())
            if not anchors:continue
            if len(anchors)!=1:
                conflicts.add(r);continue
            eid,n_anchor=next(iter(anchors.items()))
            if n_anchor<2:continue
            direct=direct_anchor_club(node['ids'])
            if direct is not None and direct!=eid:
                diagnostics['confirmed_id_transitive_conflicts_rejected']+=1;continue
            side_label[(node['ci'],node['left'])]=(eid,n_anchor,comp_sizes[r])
            qualified.add(r)
        diagnostics['confirmed_id_transitive_conflict_components_rejected']+=len(conflicts)
        diagnostics['confirmed_id_transitive_qualified_components']+=len(qualified)
        if not side_label:return 0

        # Strongest route: both sides independently inherit one authoritative club component,
        # then the club pair + exact retained score must leave one unused real fixture.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if not lc or not rc:continue
            leid,la,_=lc;reid,ra,_=rc
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(la,ra),la+ra,ci,f,rev,le,re))
        proposals.sort(reverse=True);added=0
        for _mn,_sum,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_transitive_graph_v111'):
                added+=1;diagnostics['confirmed_id_transitive_fixture_matches']+=1

        # Conservative one-side bridge: the graph supplies exactly one known club; the
        # authoritative calendar supplies the opponent only if club + exact score has ONE match.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lc=side_label.get((ci,True));rc=side_label.get((ci,False))
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc);eid,n_anchor,_=known
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
            elif len(local)>1:diagnostics['confirmed_id_transitive_one_side_ambiguities_rejected']+=1
        proposals.sort(reverse=True)
        for _na,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_transitive_graph_one_side_v111'):
                added+=1;diagnostics['confirmed_id_transitive_one_side_fixture_matches']+=1
        return added

    def confirmed_name_transitive_graph_pass():
"""
if 'def confirmed_id_transitive_graph_pass():' not in py:
    if anchor not in py:raise RuntimeError('v111 insertion anchor missing')
    py=py.replace(anchor,insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_name_transitive_qualified_components',0)\n"
diag_new=("    diagnostics.setdefault('confirmed_id_transitive_qualified_components',0)\n"
          "    diagnostics.setdefault('confirmed_id_transitive_fixture_matches',0)\n"
          "    diagnostics.setdefault('confirmed_id_transitive_one_side_fixture_matches',0)\n"
          "    diagnostics.setdefault('confirmed_id_transitive_one_side_ambiguities_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_transitive_conflicts_rejected',0)\n"
          "    diagnostics.setdefault('confirmed_id_transitive_conflict_components_rejected',0)\n"+diag_anchor)
if "diagnostics.setdefault('confirmed_id_transitive_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v111 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=';y=confirmed_name_roster_global_constraint_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
new=';y=confirmed_name_roster_global_constraint_pass();t=confirmed_id_transitive_graph_pass();z=confirmed_name_transitive_graph_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n'
if 't=confirmed_id_transitive_graph_pass()' not in py:
    if old not in py:raise RuntimeError('v111 fixed-point call anchor missing')
    py=py.replace(old,new,1)
old="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+z+u+v\n"
new="        if a or b or c or r or q or g or n or h or j or k or s or w or x or y or t or z or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+w+x+y+t+z+u+v\n"
if '+y+t+z+u+v' not in py:
    if old not in py:raise RuntimeError('v111 fixed-point total anchor missing')
    py=py.replace(old,new,1)

handoff="'unlabelled_rich_confirmed_name_transitive_qualified_components':member_rich_diag.get('confirmed_name_transitive_qualified_components',0),"
extra=("'unlabelled_rich_confirmed_id_transitive_qualified_components':member_rich_diag.get('confirmed_id_transitive_qualified_components',0),"
       "'unlabelled_rich_confirmed_id_transitive_fixture_matches':member_rich_diag.get('confirmed_id_transitive_fixture_matches',0),"
       "'unlabelled_rich_confirmed_id_transitive_one_side_fixture_matches':member_rich_diag.get('confirmed_id_transitive_one_side_fixture_matches',0),"
       "'unlabelled_rich_confirmed_id_transitive_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_id_transitive_one_side_ambiguities_rejected',0),"
       "'unlabelled_rich_confirmed_id_transitive_conflicts_rejected':member_rich_diag.get('confirmed_id_transitive_conflicts_rejected',0),"
       "'unlabelled_rich_confirmed_id_transitive_conflict_components_rejected':member_rich_diag.get('confirmed_id_transitive_conflict_components_rejected',0),"+handoff)
if 'unlabelled_rich_confirmed_id_transitive_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v111 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_id_transitive_graph_pass():','shared<8','shared/denom<0.45','if len(anchors)!=1:','if n_anchor<2:continue',"'unlabelled_retained_confirmed_id_transitive_graph_v111'",'t=confirmed_id_transitive_graph_pass()','unlabelled_rich_confirmed_id_transitive_fixture_matches','def confirmed_name_transitive_graph_pass():']:
    assert s in cpy,s
assert 'if a>b:a,b=b,a' not in cpy
print('v111 transitive retained-ID cohort graph recovery applied')
