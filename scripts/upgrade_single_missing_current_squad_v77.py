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
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

anchor="""    for eid in selected_clubs:\n        if eid not in out:out[eid]=[];diag['missing_club_eids'].append(eid)\n    return out,diag\n"""
if anchor not in py:
    if 'single_missing_current_db_completion_v77' in py:
        print('v77 already applied')
        raise SystemExit(0)
    raise RuntimeError('v75 final missing-club anchor not found')

insert=r'''    # v77: near-complete current-DB mapping completion.
    # If and only if every other selected club already has a strong current senior squad,
    # allow the final club to use the legacy sentinel-footer decoder.  This does NOT use
    # retained match history.  The candidate must still be a sane senior-sized list, bind
    # overwhelmingly to real current person records, and share no player EIDs with any of
    # the 23 already-accepted current squads.  Wrong fixture shifts therefore cannot use
    # this path when two or more clubs are unresolved.
    strong_missing=[eid for eid in selected_clubs if eid not in out]
    diag['single_missing_completion_attempted']=False
    diag['single_missing_completion_accepted']=False
    diag['single_missing_completion_evidence']=None
    if len(strong_missing)==1 and len(out)==len(selected_clubs)-1:
        eid=strong_missing[0];c=selected_clubs[eid]
        diag['single_missing_completion_attempted']=True
        weak_options=[];seen_options=set()

        def add_weak(p:int,vals:list[int],kind:str):
            vals=list(dict.fromkeys(int(x) for x in vals if int(x)>0))
            key=tuple(sorted(vals))
            if not (12<=len(vals)<=45) or key in seen_options:return
            seen_options.add(key);weak_options.append((p,vals,kind))

        # Strongest weak path: exact team EID + duplicated club UID header, where the only
        # thing missing is a positive captain/vice footer marker.
        for p,_kind in byclub.get(eid,[]):
            i=bisect.bisect_right(all_heads,p);nxt=all_heads[i] if i<len(all_heads) else None
            vals=read_squad_list_legacy(db,p,nxt)
            if not vals:vals=read_squad_list_legacy(db,p,None)
            if vals:add_weak(p,vals,'legacy_exact_uid_header_v77')

        # Schema-variant fallback: selected club EID with its duplicated current club UID
        # nearby.  Still game_db-only and still subject to the person/overlap proof below.
        if not weak_options:
            needle=struct.pack('<I',eid);uidb=struct.pack('<I',c.uid);p=0;seen_pos=set()
            while True:
                p=db.find(needle,p)
                if p<0:break
                if p in seen_pos:p+=1;continue
                seen_pos.add(p)
                lo=max(0,p-48);hi=min(len(db),p+320);window=db[lo:hi]
                if window.count(uidb)>=2:
                    vals=read_squad_list_legacy(db,p,None)
                    if vals:add_weak(p,vals,'legacy_paired_uid_v77')
                p+=1

        accepted_ids=set()
        for _vals in out.values():accepted_ids.update(int(x) for x in _vals)
        proven=[];rejected=[]
        for p,vals,kind in weak_options:
            s=set(vals);overlap=len(s&accepted_ids)
            if overlap:
                rejected.append({'offset':p,'kind':kind,'players':len(vals),'reason':'overlap-with-accepted-current-squad','overlap':overlap});continue
            people={}
            try:people=bind_target_people(db,s)
            except Exception as e:
                rejected.append({'offset':p,'kind':kind,'players':len(vals),'reason':'person-binding-error','error':str(e)[:120]});continue
            resolved=len(people);ratio=resolved/max(1,len(vals))
            structural=sum(1 for x in people.values() if getattr(x,'positions',None) or (isinstance(getattr(x,'current_ability',None),(int,float)) and getattr(x,'current_ability',0)>0))
            required=max(12,(len(vals)*3+3)//4)
            structural_required=max(8,(len(vals)+2)//3)
            if resolved<required or ratio<0.75 or structural<structural_required:
                rejected.append({'offset':p,'kind':kind,'players':len(vals),'reason':'insufficient-current-person-proof','resolved':resolved,'ratio':round(ratio,3),'structural_people':structural,'required':required,'structural_required':structural_required});continue
            cas=sorted([float(getattr(x,'current_ability')) for x in people.values() if isinstance(getattr(x,'current_ability',None),(int,float)) and getattr(x,'current_ability',0)>0],reverse=True)
            top=cas[:min(16,len(cas))];topavg=sum(top)/len(top) if top else 0.0
            proven.append({'offset':p,'vals':vals,'kind':kind,'resolved':resolved,'ratio':ratio,'structural':structural,'topavg':topavg})

        # Exact membership consensus is accepted.  If schema variants differ only by a few
        # fringe players, a very-high-overlap union is also safe after re-validating it.
        chosen=None;method=None
        groups=collections.defaultdict(list)
        for x in proven:groups[tuple(sorted(set(x['vals'])))].append(x)
        if len(groups)==1 and proven:
            chosen=proven[0]['vals'];method='single_missing_current_db_completion_v77'
        elif len(groups)>1:
            sets=[set(k) for k in groups]
            union=set().union(*sets);min_j=1.0
            for i,a in enumerate(sets):
                for b in sets[i+1:]:min_j=min(min_j,len(a&b)/max(1,len(a|b)))
            if min_j>=0.85 and 12<=len(union)<=45 and not (union&accepted_ids):
                try:upeople=bind_target_people(db,union)
                except Exception:upeople={}
                uratio=len(upeople)/max(1,len(union));ustruct=sum(1 for x in upeople.values() if getattr(x,'positions',None) or (isinstance(getattr(x,'current_ability',None),(int,float)) and getattr(x,'current_ability',0)>0))
                if len(upeople)>=max(12,(len(union)*3+3)//4) and uratio>=0.75 and ustruct>=max(8,(len(union)+2)//3):
                    chosen=sorted(union);method='single_missing_high_overlap_union_v77'
        if chosen is not None:
            out[eid]=chosen;diag['single_missing_completion_accepted']=True
            diag['single_missing_completion_evidence']={'club_eid':eid,'method':method,'players':len(chosen),'proven_candidates':len(proven),'rejected_candidates':rejected}
            diag['fallbacks'].append({'club_eid':eid,'method':method,'players':len(chosen)})
        else:
            diag['single_missing_completion_evidence']={'club_eid':eid,'method':None,'weak_candidates':len(weak_options),'proven_candidates':len(proven),'rejected_candidates':rejected}

    for eid in selected_clubs:
        if eid not in out:out[eid]=[];diag['missing_club_eids'].append(eid)
    return out,diag
'''
py=py.replace(anchor,insert,1)

marker="CURRENT_SQUAD_SINGLE_MISSING_POLICY='23-of-24-strong-plus-current-person-proof-v77'"
if marker not in py:
    future='from __future__ import annotations\n'
    if future not in py:raise RuntimeError('future import anchor missing')
    py=py.replace(future,future+marker+'\n',1)

# Expose the proof in fixture-mapping diagnostics when that evidence object is present.
ev_anchor="'squad_resolution_evidence':{'fallbacks':diag.get('fallbacks',[]),'resolved':diag.get('resolved_squad_blocks',[]),'ambiguous':diag.get('ambiguous_squad_blocks',[]),'rejected_options':diag.get('rejected_options',0),'overlap_unions':diag.get('overlap_union_squad_blocks',0)},"
if ev_anchor in py:
    ev_new="'squad_resolution_evidence':{'fallbacks':diag.get('fallbacks',[]),'resolved':diag.get('resolved_squad_blocks',[]),'ambiguous':diag.get('ambiguous_squad_blocks',[]),'rejected_options':diag.get('rejected_options',0),'overlap_unions':diag.get('overlap_union_squad_blocks',0),'single_missing_attempted':diag.get('single_missing_completion_attempted',False),'single_missing_accepted':diag.get('single_missing_completion_accepted',False),'single_missing_evidence':diag.get('single_missing_completion_evidence')},"
    py=py.replace(ev_anchor,ev_new,1)

compile(py,'fm_importer_v77.py','exec')
for token in [marker,'single_missing_current_db_completion_v77','legacy_exact_uid_header_v77','overlap-with-accepted-current-squad','insufficient-current-person-proof']:
    assert token in py,token
# Safety invariants: retained rich history is not consulted by the completion path.
block=py[py.index('# v77: near-complete current-DB mapping completion.'):py.index('    for eid in selected_clubs:\n        if eid not in out:out[eid]=[];diag[\'missing_club_eids\'].append(eid)',py.index('# v77: near-complete current-DB mapping completion.'))]
for forbidden in ['_rich_members_by_club','rich_members','played_club','home_players','away_players']:
    assert forbidden not in block,forbidden

newb64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+newb64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('v77 single-missing current squad completion applied')
