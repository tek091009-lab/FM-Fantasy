from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

NEW=r'''def _choose_current_squad_option_v75(db:bytes,eid:int,options:list[tuple[int,list[int],str]],diag:dict[str,Any]):
    """Resolve multiple CURRENT-DB squad blocks without using retained match history.

    Exact copies are consensus. Near-identical current snapshots may be unioned. Truly
    different blocks (e.g. senior vs development team) are resolved only when current
    person records provide a clear senior-quality separation; otherwise remain ambiguous.
    """
    priority={'strict':3,'paired_uid_v75':2,'relaxed_uid':1}
    valid=[]
    for p,vals,kind in options:
        if not (12<=len(vals)<=45):
            diag['rejected_options']+=1;continue
        vals=list(dict.fromkeys(int(x) for x in vals if int(x)>0))
        if not (12<=len(vals)<=45):
            diag['rejected_options']+=1;continue
        valid.append((priority.get(kind,0),p,vals,kind))
    if not valid:return None
    best=max(x[0] for x in valid);peers=[x for x in valid if x[0]==best]
    byset=collections.defaultdict(list)
    for pr,p,vals,kind in peers:byset[tuple(sorted(set(vals)))].append((p,vals,kind))
    if len(byset)==1:
        group=next(iter(byset.values()))
        if len(group)>1:diag['consensus_squad_blocks']+=1
        group.sort(key=lambda x:(abs(len(x[1])-28),x[0]))
        return group[0]

    sets=[set(vals) for _pr,_p,vals,_kind in peers]
    union=set().union(*sets)
    min_j=1.0
    for i,a in enumerate(sets):
        for b in sets[i+1:]:
            j=len(a&b)/max(1,len(a|b));min_j=min(min_j,j)
    # Registration/snapshot variants for the same senior team often differ only by a few
    # fringe players. Treat strong structural agreement as consensus, not ambiguity.
    if len(sets)>=2 and min_j>=0.72 and 12<=len(union)<=45:
        diag['overlap_union_squad_blocks']+=1
        diag['resolved_squad_blocks'].append({'club_eid':eid,'method':'high_overlap_current_db_union_v75','candidates':len(sets),'union_players':len(union),'min_jaccard':round(min_j,3)})
        return (-1,sorted(union),'current_db_overlap_union_v75')

    # Distinct blocks need stronger evidence. Resolve their player EIDs against the current
    # person table and prefer a block only when its senior-quality profile is clearly higher.
    people={}
    try:people=bind_target_people(db,union)
    except Exception as e:
        diag['current_person_resolution_errors'].append({'club_eid':eid,'error':str(e)[:180]})
    metrics=[]
    for pr,p,vals,kind in peers:
        cas=[];resolved=0
        for pid in vals:
            person=people.get(pid)
            if not person:continue
            resolved+=1
            ca=getattr(person,'current_ability',None)
            if isinstance(ca,(int,float)) and ca>0:cas.append(float(ca))
        cas.sort(reverse=True)
        top=cas[:min(16,len(cas))]
        topavg=sum(top)/len(top) if top else 0.0
        med=(sorted(cas)[len(cas)//2] if cas else 0.0)
        ratio=resolved/max(1,len(vals))
        metrics.append({'priority':pr,'offset':p,'vals':vals,'kind':kind,'resolved':resolved,'ratio':ratio,'cas':len(cas),'top16avg':topavg,'median_ca':med,'high_ca':sum(1 for x in cas if x>=100)})
    viable=[x for x in metrics if x['resolved']>=8 and x['ratio']>=0.65 and x['cas']>=8]
    if viable:
        viable.sort(key=lambda x:(x['top16avg'],x['median_ca'],x['high_ca'],x['ratio'],len(x['vals'])) ,reverse=True)
        one=viable[0];two=viable[1] if len(viable)>1 else None
        clear=two is None or (one['top16avg']-two['top16avg']>=6.0) or (one['median_ca']-two['median_ca']>=8.0 and one['top16avg']>=two['top16avg']+3.0)
        if clear:
            diag['resolved_squad_blocks'].append({'club_eid':eid,'method':'current_person_senior_quality_v75','players':len(one['vals']),'resolved_people':one['resolved'],'top16avg':round(one['top16avg'],1),'median_ca':round(one['median_ca'],1),'runner_up_top16avg':round(two['top16avg'],1) if two else None})
            return (one['offset'],one['vals'],one['kind'])

    diag['ambiguous_squad_blocks'].append({'club_eid':eid,'priority':best,'candidates':[{'offset':x['offset'],'kind':x['kind'],'players':len(x['vals']),'resolved_people':x['resolved'],'top16avg':round(x['top16avg'],1),'median_ca':round(x['median_ca'],1),'sample_player_eids':x['vals'][:8]} for x in metrics]})
    return None


def scan_first_team_squads(db: bytes, selected_clubs: dict[int,Club], rich:list[dict[str,Any]]|None=None):
    """Decode CURRENT senior squad membership from club/team records only (v75).

    No retained match/opponent evidence can add, move or select current members.
    """
    heads=[]
    for eid,c in selected_clubs.items():
        needle=struct.pack('<I',eid)+b'\x00'*10;p=0
        while True:
            p=db.find(needle,p)
            if p<0:break
            if p+26<=len(db) and u32(db,p+18)==c.uid and u32(db,p+22)==c.uid:heads.append((p,eid,'strict'))
            p+=1
    heads.sort();byclub=collections.defaultdict(list)
    for p,eid,kind in heads:byclub[eid].append((p,kind))
    all_heads=sorted(p for ps in byclub.values() for p,_ in ps)
    out={};diag={'fallbacks':[],'missing_club_eids':[],'rich_augmented_players':0,
                 'policy':'strict_current_db_membership_only_v68','block_policy':'v75-current-db-structural-senior-resolution-no-history',
                 'rejected_options':0,'ambiguous_squad_blocks':[],'consensus_squad_blocks':0,
                 'overlap_union_squad_blocks':0,'resolved_squad_blocks':[],'current_person_resolution_errors':[]}

    # First, exact duplicated-UID team headers.
    unresolved=[]
    for eid in selected_clubs:
        options=[]
        for p,kind in byclub.get(eid,[]):
            i=bisect.bisect_right(all_heads,p);nxt=all_heads[i] if i<len(all_heads) else None
            vals=read_squad_list(db,p,nxt)
            if vals:options.append((p,vals,kind))
        chosen=_choose_current_squad_option_v75(db,eid,options,diag)
        if chosen:
            _p,vals,_kind=chosen;out[eid]=vals
        else:unresolved.append(eid)

    # Second, recover schema variants where the same club EID and duplicated club UID are
    # present in a wider record window. This is still current game_db evidence only.
    for eid in unresolved:
        if eid in out:continue
        c=selected_clubs[eid];options=[];needle=struct.pack('<I',eid);uidb=struct.pack('<I',c.uid);p=0;seen=set()
        while True:
            p=db.find(needle,p)
            if p<0:break
            if p in seen:p+=1;continue
            seen.add(p)
            lo=max(0,p-48);hi=min(len(db),p+320);window=db[lo:hi]
            uid_hits=window.count(uidb)
            if uid_hits>=2:
                vals=read_squad_list(db,p,None)
                if vals:options.append((p,vals,'paired_uid_v75'))
            p+=1
        chosen=_choose_current_squad_option_v75(db,eid,options,diag)
        if chosen:
            _p,vals,kind=chosen;out[eid]=vals;diag['fallbacks'].append({'club_eid':eid,'method':kind,'players':len(vals)})

    # Final narrow compatibility fallback: one nearby current club UID, never history.
    for eid,c in selected_clubs.items():
        if eid in out:continue
        options=[];needle=struct.pack('<I',eid);p=0;seen=set();uidb=struct.pack('<I',c.uid)
        while True:
            p=db.find(needle,p)
            if p<0:break
            if p in seen:p+=1;continue
            seen.add(p);window=db[p:min(len(db),p+96)]
            if uidb not in window:p+=1;continue
            vals=read_squad_list(db,p,None)
            if vals:options.append((p,vals,'relaxed_uid'))
            p+=1
        chosen=_choose_current_squad_option_v75(db,eid,options,diag)
        if chosen:
            _p,vals,kind=chosen;out[eid]=vals;diag['fallbacks'].append({'club_eid':eid,'method':kind,'players':len(vals)})

    for eid in selected_clubs:
        if eid not in out:out[eid]=[];diag['missing_club_eids'].append(eid)
    return out,diag
'''

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
pat=re.compile(r'^def scan_first_team_squads\(.*?(?=^HEADER_PAT=)',re.M|re.S)
mm=pat.search(py)
if not mm:raise RuntimeError('current squad scanner block missing')
py=py[:mm.start()]+NEW+'\n'+py[mm.end():]
# expose diagnostics in fixture mapping evidence
old="'squad_policy':diag.get('policy'),\n        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),"
new="'squad_policy':diag.get('policy'),\n        'squad_resolution_policy':diag.get('block_policy'),\n        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),\n        'squad_resolution_evidence':{'fallbacks':diag.get('fallbacks',[]),'resolved':diag.get('resolved_squad_blocks',[]),'ambiguous':diag.get('ambiguous_squad_blocks',[]),'rejected_options':diag.get('rejected_options',0),'overlap_unions':diag.get('overlap_union_squad_blocks',0)},"
if old in py:py=py.replace(old,new,1)
elif "'squad_resolution_policy':diag.get('block_policy')" not in py:raise RuntimeError('fixture evidence insertion point missing')
compile(py,'fm_importer_v75.py','exec')
for t in ['v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75','squad_resolution_policy']:
    if t not in py:raise RuntimeError('missing V75 token '+t)
newb64=base64.b64encode(py.encode('utf-8')).decode();html=html[:m.start(1)]+newb64+html[m.end(1):];repack(html);assert reconstruct()==html
print('v75 structural current-squad resolver applied')
