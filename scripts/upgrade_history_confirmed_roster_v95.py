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
old="    def best_side_club(ids,min_score=3.0,min_margin=1.15):\n"
new="""    def confirmed_roster_club(ids):
        ranked=[]
        for eid,cohorts in confirmed_side_cohorts.items():
            if len(cohorts)<2:continue
            freq=collections.Counter(pid for cohort in cohorts for pid in cohort)
            shared_ids=ids & set(freq);shared=len(shared_ids)
            repeated=sum(1 for pid in shared_ids if freq[pid]>=2)
            coverage=shared/max(1,len(ids))
            if shared<8 or repeated<4 or coverage<0.44:continue
            weighted=shared+0.65*repeated+min(1.5,coverage*1.5)
            ranked.append((weighted,shared,repeated,coverage,eid))
        ranked.sort(reverse=True)
        if not ranked:return None
        top=ranked[0];second=ranked[1] if len(ranked)>1 else (0.0,0,0,0.0,None)
        if top[1]-second[1]<2 and top[0]-second[0]<2.5:
            diagnostics['confirmed_roster_conflicts_rejected']+=1;return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top[4]:
            diagnostics['confirmed_roster_conflicts_rejected']+=1;return None
        return top[4],top[1],top[2],top[3],top[0]

    def best_side_club(ids,min_score=3.0,min_margin=1.15):
"""
if 'def confirmed_roster_club(ids):' not in py:
    if old not in py:raise RuntimeError('v95 helper anchor missing')
    py=py.replace(old,new,1)
old="    def single_side_bridge_pass():\n"
new="""    def confirmed_roster_fixture_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_cohort_club(lids);rc=confirmed_cohort_club(rids)
            lr=confirmed_roster_club(lids);rr=confirmed_roster_club(rids)
            if lc:leid,lshared,_=lc;lstrength=float(lshared);lsource='cohort'
            elif lr:leid,lshared,_lr,_lc,lstrength=lr;lsource='roster'
            else:continue
            if rc:reid,rshared,_=rc;rstrength=float(rshared);rsource='cohort'
            elif rr:reid,rshared,_rr,_rc,rstrength=rr;rsource='roster'
            else:continue
            if lsource!='roster' and rsource!='roster':continue
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0];proposals.append((min(lstrength,rstrength),lstrength+rstrength,ci,f,rev,le,re,lsource,rsource))
        proposals.sort(key=lambda x:(x[0],x[1]),reverse=True);added=0
        for _a,_b,ci,f,rev,leid,reid,lsource,rsource in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_roster_fixture'):
                added+=1;diagnostics['confirmed_roster_fixture_matches']+=1
                diagnostics['confirmed_roster_side_uses']+=(lsource=='roster')+(rsource=='roster')
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_roster_fixture_pass():' not in py:
    if old not in py:raise RuntimeError('v95 pass anchor missing')
    py=py.replace(old,new,1)
py=py.replace("    diagnostics.setdefault('confirmed_cohort_fixture_matches',0)\n","    diagnostics.setdefault('confirmed_cohort_fixture_matches',0)\n    diagnostics.setdefault('confirmed_roster_fixture_matches',0)\n    diagnostics.setdefault('confirmed_roster_side_uses',0)\n    diagnostics.setdefault('confirmed_roster_conflicts_rejected',0)\n",1)
old="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c\n"
new="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c or r:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r\n"
if 'r=confirmed_roster_fixture_pass()' not in py:
    if old not in py:raise RuntimeError('v95 loop anchor missing')
    py=py.replace(old,new,1)
anchor="'unlabelled_rich_confirmed_cohort_fixture_matches':member_rich_diag.get('confirmed_cohort_fixture_matches',0),"
addition=anchor+"'unlabelled_rich_confirmed_roster_fixture_matches':member_rich_diag.get('confirmed_roster_fixture_matches',0),'unlabelled_rich_confirmed_roster_side_uses':member_rich_diag.get('confirmed_roster_side_uses',0),'unlabelled_rich_confirmed_roster_conflicts_rejected':member_rich_diag.get('confirmed_roster_conflicts_rejected',0),"
if 'unlabelled_rich_confirmed_roster_fixture_matches' not in py:
    if anchor not in py:raise RuntimeError('v95 handoff anchor missing')
    py=py.replace(anchor,addition,1)
compile(py,'fm_importer.py','exec');new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in ['def confirmed_roster_club(ids):','shared<8 or repeated<4 or coverage<0.44','def confirmed_roster_fixture_pass():','r=confirmed_roster_fixture_pass()','unlabelled_rich_confirmed_roster_fixture_matches']:assert s in cpy,s
print('v95 accumulated confirmed-roster recovery applied')
