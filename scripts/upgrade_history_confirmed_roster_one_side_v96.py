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
if 'def confirmed_roster_club(ids):' not in py or 'def confirmed_roster_fixture_pass():' not in py:
    raise RuntimeError('v95 confirmed-roster decoder must exist before v96')
old="    def single_side_bridge_pass():\n"
new="""    def confirmed_roster_one_side_pass():
        # v96: use the strong accumulated-confirmed-roster identity when exactly one side
        # can be identified. The opposite side is NEVER guessed from player votes. Instead,
        # the known club + exact retained aggregate score must leave exactly one unused
        # authoritative played fixture, which supplies the opponent identity.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lr=confirmed_roster_club(lids);rr=confirmed_roster_club(rids)
            # Direct v95 two-sided recovery remains stronger and handles the both-known case.
            if bool(lr)==bool(rr):continue
            lscore,rscore=score_of(c);options=[]
            if lr:
                known=int(lr[0]);strength=float(lr[4]);known_side='left'
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==heid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==aeid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            else:
                known=int(rr[0]);strength=float(rr[4]);known_side='right'
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==aeid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==heid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            # Collapse only representations of the same authoritative fixture. Missing/zero
            # numeric fixture IDs remain safe because fixture_identity() has a structural key.
            uniq={fixture_identity(o[0]):o for o in options}
            if len(uniq)!=1:
                if len(uniq)>1:diagnostics['confirmed_roster_one_side_ambiguities_rejected']+=1
                continue
            f,rev,leid,reid=next(iter(uniq.values()))
            proposals.append((strength,ci,f,rev,leid,reid,known_side))
        proposals.sort(key=lambda x:x[0],reverse=True);added=0
        for _strength,ci,f,rev,leid,reid,known_side in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_roster_one_side'):
                added+=1;diagnostics['confirmed_roster_one_side_fixture_matches']+=1
                diagnostics['confirmed_roster_one_side_side_uses']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_roster_one_side_pass():' not in py:
    if old not in py:raise RuntimeError('v96 pass anchor missing')
    py=py.replace(old,new,1)
old="    diagnostics.setdefault('confirmed_roster_conflicts_rejected',0)\n"
new="    diagnostics.setdefault('confirmed_roster_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_roster_one_side_fixture_matches',0)\n    diagnostics.setdefault('confirmed_roster_one_side_side_uses',0)\n    diagnostics.setdefault('confirmed_roster_one_side_ambiguities_rejected',0)\n"
if "diagnostics.setdefault('confirmed_roster_one_side_fixture_matches',0)" not in py:
    if old not in py:raise RuntimeError('v96 diagnostic anchor missing')
    py=py.replace(old,new,1)
old="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c or r:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r\n"
new="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q\n"
if 'q=confirmed_roster_one_side_pass()' not in py:
    if old not in py:raise RuntimeError('v96 loop anchor missing')
    py=py.replace(old,new,1)
anchor="'unlabelled_rich_confirmed_roster_conflicts_rejected':member_rich_diag.get('confirmed_roster_conflicts_rejected',0),"
addition=anchor+"'unlabelled_rich_confirmed_roster_one_side_fixture_matches':member_rich_diag.get('confirmed_roster_one_side_fixture_matches',0),'unlabelled_rich_confirmed_roster_one_side_side_uses':member_rich_diag.get('confirmed_roster_one_side_side_uses',0),'unlabelled_rich_confirmed_roster_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_roster_one_side_ambiguities_rejected',0),"
if 'unlabelled_rich_confirmed_roster_one_side_fixture_matches' not in py:
    if anchor not in py:raise RuntimeError('v96 handoff anchor missing')
    py=py.replace(anchor,addition,1)
compile(py,'fm_importer.py','exec');new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_roster_one_side_pass():','if bool(lr)==bool(rr):continue',"'unlabelled_retained_confirmed_roster_one_side'",'uniq={fixture_identity(o[0]):o for o in options}','q=confirmed_roster_one_side_pass()','unlabelled_rich_confirmed_roster_one_side_fixture_matches']:assert s in cpy,s
print('v96 one-side confirmed-roster recovery applied')
