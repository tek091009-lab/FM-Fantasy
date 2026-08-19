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
if 'def confirmed_name_club(rows,ids):' not in py or 'def confirmed_name_fixture_pass():' not in py:
    raise RuntimeError('v99/v100 exact confirmed-name decoder must exist before v101')

old="    def single_side_bridge_pass():\n"
new="""    def confirmed_name_one_side_pass():
        # v101: exact retained football names are a genuinely separate identity representation
        # from numeric player IDs/current-squad anchors. If EXACTLY ONE retained side reaches the
        # strict v99/v100 confirmed-name standard, never guess the other side from names or IDs.
        # Instead require that known club + exact retained score leaves exactly one unused
        # authoritative played fixture; that fixture supplies the opponent identity.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            ln=confirmed_name_club(c['left'],lids);rn=confirmed_name_club(c['right'],rids)
            # Two-name-side recovery is stronger and remains handled first by v99.
            if bool(ln)==bool(rn):continue
            lscore,rscore=score_of(c);options=[]
            if ln:
                known=int(ln[0]);strength=float(ln[1]);known_side='left'
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==heid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==aeid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            else:
                known=int(rn[0]);strength=float(rn[1]);known_side='right'
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==aeid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==heid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            uniq={fixture_identity(o[0]):o for o in options}
            if len(uniq)!=1:
                if len(uniq)>1:diagnostics['confirmed_name_one_side_ambiguities_rejected']+=1
                continue
            f,rev,leid,reid=next(iter(uniq.values()))
            proposals.append((strength,ci,f,rev,leid,reid,known_side))
        proposals.sort(key=lambda x:x[0],reverse=True);added=0
        for _strength,ci,f,rev,leid,reid,known_side in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_exact_name_one_side'):
                added+=1;diagnostics['confirmed_name_one_side_fixture_matches']+=1
                diagnostics['confirmed_name_one_side_side_uses']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_one_side_pass():' not in py:
    if old not in py:raise RuntimeError('v101 pass anchor missing')
    py=py.replace(old,new,1)

diag="    diagnostics.setdefault('confirmed_name_ambiguous_aliases',0)\n"
add=diag+"    diagnostics.setdefault('confirmed_name_one_side_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_one_side_side_uses',0)\n    diagnostics.setdefault('confirmed_name_one_side_ambiguities_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_one_side_fixture_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v101 diagnostic anchor missing')
    py=py.replace(diag,add,1)

old_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n\n"
new_loop="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h\n"
if 'h=confirmed_name_one_side_pass()' not in py:
    if old_loop not in py:raise RuntimeError('v101 fixed-point loop anchor missing')
    py=py.replace(old_loop,new_loop,1)

anchor="'unlabelled_rich_confirmed_name_ambiguous_aliases':member_rich_diag.get('confirmed_name_ambiguous_aliases',0),"
addition=anchor+"'unlabelled_rich_confirmed_name_one_side_fixture_matches':member_rich_diag.get('confirmed_name_one_side_fixture_matches',0),'unlabelled_rich_confirmed_name_one_side_side_uses':member_rich_diag.get('confirmed_name_one_side_side_uses',0),'unlabelled_rich_confirmed_name_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_name_one_side_ambiguities_rejected',0),"
if 'unlabelled_rich_confirmed_name_one_side_fixture_matches' not in py:
    if anchor not in py:raise RuntimeError('v101 handoff anchor missing')
    py=py.replace(anchor,addition,1)

compile(py,'fm_importer.py','exec');new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_name_one_side_pass():','if bool(ln)==bool(rn):continue','uniq={fixture_identity(o[0]):o for o in options}',"'unlabelled_retained_confirmed_exact_name_one_side'",'h=confirmed_name_one_side_pass()','unlabelled_rich_confirmed_name_one_side_fixture_matches','def confirmed_name_fixture_pass():','confirmed_name_transfer_support_uses']:
    assert s in cpy,s
print('v101 one-side exact-name retained recovery applied')
