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
if 'def confirmed_name_cohort_club(rows,ids):' not in py:
    raise RuntimeError('v106 retained-name cohort layer must exist before v107')

# v107 accumulates canonical retained names across multiple already-authoritative matches.
# This solves rotation where no single confirmed XI overlaps enough, while still forbidding
# speculative candidates from teaching the historical roster.
helper_anchor='    def confirmed_name_cohort_club(rows,ids):\n'
helper_insert="""    def _confirmed_name_roster_profiles():
        profiles={}
        for eid,cohorts in confirmed_retained_name_side_cohorts.items():
            if len(cohorts)<2:continue
            freq=collections.Counter()
            for cohort in cohorts:
                for name in cohort:freq[name]+=1
            profiles[eid]=(len(cohorts),set(freq),freq)
        return profiles

    def confirmed_name_roster_club(rows,ids):
        names=_retained_side_name_set(rows)
        if len(names)<8:return None
        ranked=[]
        for eid,(cohort_n,roster,freq) in _confirmed_name_roster_profiles().items():
            shared=names & roster
            repeated=sum(1 for n in shared if freq.get(n,0)>=2)
            coverage=len(shared)/max(1,len(names))
            # Require evidence accumulated over >=2 authoritative matches. Eight shared names,
            # four independently repeated names and 44% side coverage mirror the safe numeric-ID
            # accumulated-roster route while operating in the independent retained-name namespace.
            if len(shared)>=8 and repeated>=4 and coverage>=0.44:
                ranked.append((len(shared),repeated,coverage,cohort_n,eid))
        ranked.sort(reverse=True)
        if not ranked:return None
        top=ranked[0];second=ranked[1] if len(ranked)>1 else (0,0,0.0,0,None)
        # A close competing historical club remains unresolved.
        if top[0]-second[0]<3 and top[1]-second[1]<2 and top[2]-second[2]<0.15:
            diagnostics['confirmed_name_roster_conflicts_rejected']+=1;return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top[4]:
            diagnostics['confirmed_name_roster_conflicts_rejected']+=1;return None
        return top[4],top[0],top[1],top[2],top[3]

    def confirmed_name_cohort_club(rows,ids):
"""
if 'def confirmed_name_roster_club(rows,ids):' not in py:
    if helper_anchor not in py:raise RuntimeError('v107 helper anchor missing')
    py=py.replace(helper_anchor,helper_insert,1)

pass_anchor='    def confirmed_name_cohort_fixture_pass():\n'
pass_insert="""    def confirmed_name_roster_fixture_pass():
        # Two-sided route: both sides independently match accumulated name rosters, then exact
        # clubs+score must leave one unused authoritative fixture.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_name_roster_club(c['left'],lids);rc=confirmed_name_roster_club(c['right'],rids)
            if not lc or not rc:continue
            leid,lshared,lrep,_lcov,_ln=lc;reid,rshared,rrep,_rcov,_rn=rc
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(lshared,rshared),min(lrep,rrep),lshared+rshared,ci,f,rev,le,re))
        proposals.sort(reverse=True);added=0
        for _mn,_rep,_sum,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_roster_fixture_v107'):
                added+=1;diagnostics['confirmed_name_roster_fixture_matches']+=1
        return added

    def confirmed_name_roster_one_side_pass():
        # Exactly one accumulated-name-roster side may bridge only when club+exact score leaves
        # one real unused fixture; the authoritative fixture supplies the opponent.
        proposals=[];amb=0
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_name_roster_club(c['left'],lids);rc=confirmed_name_roster_club(c['right'],rids)
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc);eid,shared,repeated,_cov,_n=known
            lscore,rscore=score_of(c);local={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                if known_left:
                    if eid==heid and lscore==hs and rscore==as_:local[fk]=(f,False,heid,aeid)
                    if eid==aeid and lscore==as_ and rscore==hs:local[fk]=(f,True,aeid,heid)
                else:
                    if eid==aeid and lscore==hs and rscore==as_:local[fk]=(f,False,heid,aeid)
                    if eid==heid and lscore==as_ and rscore==hs:local[fk]=(f,True,aeid,heid)
            if len(local)==1:
                f,rev,leid,reid=next(iter(local.values()));proposals.append((shared,repeated,ci,f,rev,leid,reid))
            elif len(local)>1:amb+=1
        diagnostics['confirmed_name_roster_one_side_ambiguities_rejected']+=amb
        proposals.sort(reverse=True);added=0
        for _shared,_rep,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_roster_one_side_v107'):
                added+=1;diagnostics['confirmed_name_roster_one_side_fixture_matches']+=1
        return added

    def confirmed_name_cohort_fixture_pass():
"""
if 'def confirmed_name_roster_fixture_pass():' not in py:
    if pass_anchor not in py:raise RuntimeError('v107 pass anchor missing')
    py=py.replace(pass_anchor,pass_insert,1)

diag_anchor="    diagnostics.setdefault('confirmed_name_cohort_conflicts_rejected',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_roster_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_roster_one_side_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_roster_one_side_ambiguities_rejected',0)\n    diagnostics.setdefault('confirmed_name_roster_conflicts_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_roster_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v107 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

# Run v107 after stronger individual-name paths but before single-XI name-cohort fallbacks.
old=';s=confirmed_name_fixture_conditioned_global_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or u or v:\n            diagnostics[\'propagation_rounds\']+=1\n            diagnostics[\'propagation_matches\']+=a+b+c+r+q+g+n+h+j+k+s+u+v\n'
new=';s=confirmed_name_fixture_conditioned_global_pass();w=confirmed_name_roster_fixture_pass();x=confirmed_name_roster_one_side_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or w or x or u or v:\n            diagnostics[\'propagation_rounds\']+=1\n            diagnostics[\'propagation_matches\']+=a+b+c+r+q+g+n+h+j+k+s+w+x+u+v\n'
if 'w=confirmed_name_roster_fixture_pass()' not in py:
    if old not in py:raise RuntimeError('v107 fixed-point loop anchor missing')
    py=py.replace(old,new,1)

handoff_anchor="'unlabelled_rich_confirmed_name_cohort_conflicts_rejected':member_rich_diag.get('confirmed_name_cohort_conflicts_rejected',0),"
handoff_new=handoff_anchor+"'unlabelled_rich_confirmed_name_roster_fixture_matches':member_rich_diag.get('confirmed_name_roster_fixture_matches',0),'unlabelled_rich_confirmed_name_roster_one_side_fixture_matches':member_rich_diag.get('confirmed_name_roster_one_side_fixture_matches',0),'unlabelled_rich_confirmed_name_roster_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_name_roster_one_side_ambiguities_rejected',0),'unlabelled_rich_confirmed_name_roster_conflicts_rejected':member_rich_diag.get('confirmed_name_roster_conflicts_rejected',0),"
if 'unlabelled_rich_confirmed_name_roster_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v107 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def _confirmed_name_roster_profiles():',
    'def confirmed_name_roster_club(rows,ids):',
    'len(shared)>=8 and repeated>=4 and coverage>=0.44',
    'def confirmed_name_roster_fixture_pass():',
    'def confirmed_name_roster_one_side_pass():',
    "'unlabelled_retained_confirmed_name_roster_fixture_v107'",
    "'unlabelled_retained_confirmed_name_roster_one_side_v107'",
    'w=confirmed_name_roster_fixture_pass()',
    'x=confirmed_name_roster_one_side_pass()',
    'unlabelled_rich_confirmed_name_roster_fixture_matches',
    'def confirmed_name_cohort_fixture_pass():',
    'def confirmed_name_fixture_conditioned_global_pass():',
]:assert s in cpy,s
print('v107 accumulated retained-name roster recovery applied')
