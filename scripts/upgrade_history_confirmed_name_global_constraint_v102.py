from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
def reconstruct():return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()
def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode();step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))];assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')
html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def confirmed_name_one_side_pass():' not in py or 'def confirmed_name_club(rows,ids):' not in py:
    raise RuntimeError('v99-v101 exact retained-name decoders must exist before v102')

anchor="    def single_side_bridge_pass():\n"
insert="""    def confirmed_name_global_constraint_pass():
        # v102: v101 deliberately rejects one-name-side candidates when known club + exact
        # score still fits multiple unused authoritative fixtures. Do not guess locally. Build
        # the candidate<->fixture ambiguity graph and accept only a mathematically UNIQUE
        # complete one-to-one assignment, using the same edge-removal proof as v97.
        edge_options={};strengths={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            ln=confirmed_name_club(c['left'],lids);rn=confirmed_name_club(c['right'],rids)
            # v99 handles two known sides; v101 handles individually unique one-known sides.
            if bool(ln)==bool(rn):continue
            lscore,rscore=score_of(c);options=[]
            if ln:
                known=int(ln[0]);strength=float(ln[1])
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==heid and lscore==hs and rscore==as_:options.append((f,False,heid,aeid))
                    elif known==aeid and lscore==as_ and rscore==hs:options.append((f,True,aeid,heid))
            else:
                known=int(rn[0]);strength=float(rn[1])
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==aeid and lscore==hs and rscore==as_:options.append((f,False,heid,aeid))
                    elif known==heid and lscore==as_ and rscore==hs:options.append((f,True,aeid,heid))
            uniq={fixture_identity(o[0]):o for o in options}
            # Exactly-one belongs to v101. Very broad ambiguity remains unresolved.
            if 2<=len(uniq)<=8:
                edge_options[ci]=uniq;strengths[ci]=strength
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
                    fs.add(fk);stack.extend(x for x in fixture_to_candidates[fk] if x not in cs)
            components.append((cs,fs))

        def perfect_matching(cands,blocked=None):
            match_f={}
            def aug(ci,seen):
                for fk in sorted(edge_options[ci],key=repr):
                    if blocked is not None and blocked==(ci,fk):continue
                    if fk in seen:continue
                    seen.add(fk);prev=match_f.get(fk)
                    if prev is None or aug(prev,seen):match_f[fk]=ci;return True
                return False
            for ci in sorted(cands,key=lambda x:(len(edge_options[x]),-strengths.get(x,0.0),x)):
                if not aug(ci,set()):return None
            return {ci:fk for fk,ci in match_f.items()}

        accepted=[]
        for cs,fs in components:
            if len(cs)<2:continue
            if len(cs)>12:
                diagnostics['confirmed_name_global_oversized_components_rejected']+=1;continue
            if len(cs)!=len(fs):
                diagnostics['confirmed_name_global_unbalanced_components_rejected']+=1;continue
            match=perfect_matching(cs)
            if match is None:
                diagnostics['confirmed_name_global_no_perfect_match_rejected']+=1;continue
            unique=True
            for ci,fk in match.items():
                if perfect_matching(cs,(ci,fk)) is not None:
                    unique=False;break
            if not unique:
                diagnostics['confirmed_name_global_nonunique_components_rejected']+=1;continue
            diagnostics['confirmed_name_global_unique_components']+=1
            for ci,fk in match.items():accepted.append((strengths.get(ci,0.0),ci,edge_options[ci][fk]))
        accepted.sort(key=lambda x:x[0],reverse=True);added=0
        for _strength,ci,opt in accepted:
            f,rev,leid,reid=opt
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_exact_name_global_unique'):
                added+=1;diagnostics['confirmed_name_global_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_global_constraint_pass():' not in py:
    if anchor not in py:raise RuntimeError('v102 pass anchor missing')
    py=py.replace(anchor,insert,1)

diag="    diagnostics.setdefault('confirmed_name_one_side_ambiguities_rejected',0)\n"
add=diag+"    diagnostics.setdefault('confirmed_name_global_unique_components',0)\n    diagnostics.setdefault('confirmed_name_global_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_global_oversized_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_global_unbalanced_components_rejected',0)\n    diagnostics.setdefault('confirmed_name_global_no_perfect_match_rejected',0)\n    diagnostics.setdefault('confirmed_name_global_nonunique_components_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_global_fixture_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v102 diagnostic anchor missing')
    py=py.replace(diag,add,1)

old_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h\n"
new_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j\n"
if 'j=confirmed_name_global_constraint_pass()' not in py:
    if old_loop not in py:raise RuntimeError('v102 fixed-point loop anchor missing')
    py=py.replace(old_loop,new_loop,1)

handoff="'unlabelled_rich_confirmed_name_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_name_one_side_ambiguities_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_name_global_unique_components':member_rich_diag.get('confirmed_name_global_unique_components',0),'unlabelled_rich_confirmed_name_global_fixture_matches':member_rich_diag.get('confirmed_name_global_fixture_matches',0),'unlabelled_rich_confirmed_name_global_oversized_components_rejected':member_rich_diag.get('confirmed_name_global_oversized_components_rejected',0),'unlabelled_rich_confirmed_name_global_unbalanced_components_rejected':member_rich_diag.get('confirmed_name_global_unbalanced_components_rejected',0),'unlabelled_rich_confirmed_name_global_no_perfect_match_rejected':member_rich_diag.get('confirmed_name_global_no_perfect_match_rejected',0),'unlabelled_rich_confirmed_name_global_nonunique_components_rejected':member_rich_diag.get('confirmed_name_global_nonunique_components_rejected',0),"
if 'unlabelled_rich_confirmed_name_global_fixture_matches' not in py:
    if handoff not in py:raise RuntimeError('v102 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec');new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_name_global_constraint_pass():','2<=len(uniq)<=8','if len(cs)!=len(fs):','perfect_matching(cs,(ci,fk))',"'unlabelled_retained_confirmed_exact_name_global_unique'",'j=confirmed_name_global_constraint_pass()','unlabelled_rich_confirmed_name_global_fixture_matches','def confirmed_name_one_side_pass():','confirmed_name_transfer_support_uses']:
    assert s in cpy,s
print('v102 globally unique exact-name retained recovery applied')