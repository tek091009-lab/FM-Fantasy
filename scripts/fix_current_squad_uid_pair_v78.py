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

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')

marker="CURRENT_SQUAD_UID_PAIR_POLICY='duplicate-club-uid-team-header-v78'"
if marker not in py:
    future='from __future__ import annotations\n'
    if future not in py: raise RuntimeError('future import anchor missing')
    py=py.replace(future,future+marker+'\n',1)

anchor="""        # Schema-variant fallback: selected club EID with its duplicated current club UID
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
"""
insert="""        # Schema-variant fallback: selected club EID with its duplicated current club UID
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

        # v78: some FM saves use a distinct first-team entity id while still carrying the
        # club UID twice in the authoritative current-team header.  The earlier fallback
        # always started from the CLUB EID, so those records were invisible.  Search the
        # duplicated UID header directly and derive the same canonical head offset used by
        # the 23 already-decoded clubs.  This remains current game_db evidence only.
        uidb=struct.pack('<I',c.uid);pair=uidb+uidb;q=0;uid_pair_seen=set()
        while True:
            q=db.find(pair,q)
            if q<0:break
            head=q-18
            if head>=0 and head not in uid_pair_seen:
                uid_pair_seen.add(head)
                vals=read_squad_list(db,head,None)
                if not vals: vals=read_squad_list_legacy(db,head,None)
                if vals:add_weak(head,vals,'uid_pair_header_v78')
            q+=1

        accepted_ids=set()
"""
if anchor not in py: raise RuntimeError('v77 weak fallback anchor missing')
py=py.replace(anchor,insert,1)

anchor2="""        chosen=None;method=None
        groups=collections.defaultdict(list)
        for x in proven:groups[tuple(sorted(set(x['vals'])))].append(x)
        if len(groups)==1 and proven:
            chosen=proven[0]['vals'];method='single_missing_current_db_completion_v77'
"""
insert2="""        chosen=None;method=None
        # A duplicated club-UID header is stronger than generic legacy arrays because its
        # location is learned from the same current-team structure used by the 23 proven clubs.
        uid_proven=[x for x in proven if x.get('kind')=='uid_pair_header_v78']
        basis=uid_proven if uid_proven else proven
        groups=collections.defaultdict(list)
        for x in basis:groups[tuple(sorted(set(x['vals'])))].append(x)
        if len(groups)==1 and basis:
            chosen=basis[0]['vals'];method='single_missing_uid_pair_current_db_completion_v78' if uid_proven else 'single_missing_current_db_completion_v77'
"""
if anchor2 not in py: raise RuntimeError('v77 candidate grouping anchor missing')
py=py.replace(anchor2,insert2,1)

# Make failure diagnostics useful if the real save still exposes a new schema.
old_summary="""            f\"comp={x.get('competition_id')} shift={x.get('shift')} safe={x.get('safe_squad_clubs','?')}/{x.get('team_count','?')} missing={','.join(x.get('unsafe_squad_names',[])[:4]) or '-'}\"
"""
new_summary="""            f\"comp={x.get('competition_id')} shift={x.get('shift')} safe={x.get('safe_squad_clubs','?')}/{x.get('team_count','?')} missing={','.join(x.get('unsafe_squad_names',[])[:4]) or '-'} v78={x.get('squad_resolution_evidence',{}).get('single_missing_completion_evidence') or x.get('single_missing_completion_evidence') or '-'}\"
"""
if old_summary in py: py=py.replace(old_summary,new_summary,1)

# Ensure fixture evidence carries the current-squad diagnostics, including V78 proof.
old_ev="""        'squad_policy':diag.get('policy'),
        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),
        'mapping_proof':'all-fixture-teams-map-to-English-clubs + every-current-senior-squad-size-12..45-v73',
"""
new_ev="""        'squad_policy':diag.get('policy'),
        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),
        'squad_resolution_evidence':{
            'single_missing_completion_attempted':diag.get('single_missing_completion_attempted'),
            'single_missing_completion_accepted':diag.get('single_missing_completion_accepted'),
            'single_missing_completion_evidence':diag.get('single_missing_completion_evidence'),
            'fallbacks':diag.get('fallbacks',[]),
        },
        'mapping_proof':'all-fixture-teams-map-to-English-clubs + every-current-senior-squad-size-12..45-v73',
"""
if old_ev in py: py=py.replace(old_ev,new_ev,1)
elif "'squad_resolution_evidence':{" not in py: raise RuntimeError('fixture evidence anchor missing')

compile(py,'fm_importer_v78.py','exec')
for t in [marker,'uid_pair_header_v78','single_missing_uid_pair_current_db_completion_v78','squad_resolution_evidence']:
    if t not in py: raise RuntimeError('missing '+t)

newb64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+newb64+html[m.end(1):]
repack(html);assert reconstruct()==html
print('V78 current-team UID-pair fallback applied')
