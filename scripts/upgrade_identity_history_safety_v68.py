from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]


def reconstruct_html()->str:
    packed=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(packed)).decode('utf-8')


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    if len(chunks)<len(PARTS):chunks+=['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed:raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


def replace_def(src:str,name:str,new_body:str)->str:
    m=re.search(rf'^def {re.escape(name)}\(',src,re.M)
    if not m:raise RuntimeError(f'{name} not found')
    n=re.search(r'^def [A-Za-z0-9_]+\(',src[m.end():],re.M)
    end=m.end()+n.start() if n else len(src)
    return src[:m.start()]+new_body.rstrip()+'\n\n'+src[end:]


NEW_SCAN=r'''def scan_first_team_squads(db: bytes, selected_clubs: dict[int,Club], rich:list[dict[str,Any]]|None=None):
    """Decode CURRENT senior squad membership from club/team records only.

    Retained match history is deliberately forbidden from adding, moving, selecting or
    resolving current club membership. If a current first-team list cannot be decoded
    conservatively, the import must fail upstream rather than inventing a squad.
    """
    heads=[]
    for eid,c in selected_clubs.items():
        needle=struct.pack('<I',eid)+b'\x00'*10
        p=0
        while True:
            p=db.find(needle,p)
            if p<0:break
            if p+26<=len(db) and u32(db,p+18)==c.uid and u32(db,p+22)==c.uid:
                heads.append((p,eid,'strict'))
            p+=1
    heads.sort()
    byclub=collections.defaultdict(list)
    for p,eid,kind in heads:byclub[eid].append((p,kind))
    all_heads=sorted(p for ps in byclub.values() for p,_ in ps)
    out={};diag={'fallbacks':[],'missing_club_eids':[],'rich_augmented_players':0,
                 'policy':'strict_current_db_membership_only_v68','rejected_options':0}

    def choose_options(options):
        valid=[]
        for p,vals,kind in options:
            if not (12<=len(vals)<=45):
                diag['rejected_options']+=1;continue
            priority=2 if kind=='strict' else 1
            valid.append(((priority,-abs(len(vals)-28),-p),p,vals,kind))
        if not valid:return None
        valid.sort(reverse=True)
        return valid[0][1:]

    # Exact team-eid + duplicated club-uid header is the authoritative path.
    for eid in selected_clubs:
        options=[]
        for p,kind in byclub.get(eid,[]):
            i=bisect.bisect_right(all_heads,p);nxt=all_heads[i] if i<len(all_heads) else None
            vals=read_squad_list(db,p,nxt)
            if vals:options.append((p,vals,kind))
        chosen=choose_options(options)
        if chosen:
            _p,vals,_kind=chosen;out[eid]=vals

    # Conservative fallback: same selected team eid, its club uid nearby, plausible senior size.
    # No retained-match overlap is used for selection.
    for eid,c in selected_clubs.items():
        if eid in out:continue
        options=[];needle=struct.pack('<I',eid);p=0;seen=set();uidb=struct.pack('<I',c.uid)
        while True:
            p=db.find(needle,p)
            if p<0:break
            if p in seen:p+=1;continue
            seen.add(p)
            window=db[p:min(len(db),p+72)]
            if uidb not in window:
                p+=1;continue
            vals=read_squad_list(db,p,None)
            if vals:options.append((p,vals,'relaxed_uid'))
            p+=1
        chosen=choose_options(options)
        if chosen:
            _p,vals,kind=chosen;out[eid]=vals
            diag['fallbacks'].append({'club_eid':eid,'method':kind,'players':len(vals)})

    for eid in selected_clubs:
        if eid not in out:
            out[eid]=[];diag['missing_club_eids'].append(eid)
    return out,diag
'''


def patch_build_players(src:str)->str:
    start=src.index('def build_players(')
    end=src.index('\ndef aggregate_player_history(',start)
    block=src[start:end]
    old="""    played_club={}\n    if rich:\n        name_to_eid={normalize_club_name(c.name):eid for eid,c in selected_clubs.items()}\n        name_to_eid.update({normalize_club_name(c.short):eid for eid,c in selected_clubs.items()})\n        for m in rich:\n            for side,key in [('home','home_players'),('away','away_players')]:\n                ceid=name_to_eid.get(normalize_club_name(m[side]))\n                if ceid is None:continue\n                for r in m[key]: played_club[int(r['player_id'])]=ceid\n"""
    if old not in block:raise RuntimeError('played_club resolver block missing')
    block=block.replace(old,"    # v68: retained match history is never authoritative for CURRENT club membership.\n",1)
    old2="""        ceid=clubs[0]\n        if len(clubs)>1:\n            if played_club.get(eid) in clubs: ceid=played_club[eid]\n            else: ambiguous.append({'player_eid':eid,'club_eids':clubs})\n"""
    new2="""        clubs=sorted(set(clubs))\n        if len(clubs)!=1:\n            ambiguous.append({'player_eid':eid,'club_eids':clubs,'reason':'multiple_current_squad_records'})\n            continue\n        ceid=clubs[0]\n"""
    if old2 not in block:raise RuntimeError('ambiguous membership resolver block missing')
    block=block.replace(old2,new2,1)
    return src[:start]+block+src[end:]


def patch_aggregate(src:str)->str:
    start=src.index('def aggregate_player_history(')
    m=re.search(r'^def [A-Za-z0-9_]+\(',src[start+1:],re.M)
    end=start+1+m.start() if m else len(src)
    block=src[start:end]
    anchor="    byid={int(p['pid']):p for p in players}\n"
    if anchor not in block:raise RuntimeError('aggregate byid anchor missing')
    safety=r'''    byid={int(p['pid']):p for p in players}
    latest_gw=max((int(m.get('gameweek') or 0) for m in matches),default=0)
    occ=collections.defaultdict(list);unsafe_pids=set();unsafe_reasons=collections.defaultdict(set)
    side_seen={}
    for m in matches:
        mid=int(m.get('fixture_id') or m.get('match_id') or m.get('id') or 0)
        for key,sideclub in (('home_players',normalize_club_name(m.get('home',''))),('away_players',normalize_club_name(m.get('away','')))):
            for r in m.get(key,[]):
                pid=int(r.get('player_id') or 0)
                if pid<=0:continue
                club=normalize_club_name(r.get('club') or sideclub)
                date=str(m.get('date') or '')
                gw=int(r.get('gameweek') or m.get('gameweek') or 0)
                occ[pid].append((date,gw,mid,club))
                k=(mid,pid)
                prev=side_seen.get(k)
                if prev is not None and prev!=club:
                    unsafe_pids.add(pid);unsafe_reasons[pid].add('same_match_both_clubs')
                side_seen[k]=club
    for pid,recs in occ.items():
        bydate=collections.defaultdict(set)
        for date,gw,mid,club in recs:
            if date:bydate[date].add(club)
        if any(len(v)>1 for v in bydate.values()):
            unsafe_pids.add(pid);unsafe_reasons[pid].add('same_date_multiple_clubs')
        ordered=sorted(recs,key=lambda x:(x[0],x[1],x[2]))
        seq=[]
        for _date,_gw,_mid,club in ordered:
            if club and (not seq or seq[-1]!=club):seq.append(club)
        if len(seq)>2 or len(set(seq))>2:
            unsafe_pids.add(pid);unsafe_reasons[pid].add('impossible_multi_club_timeline')
        cur=normalize_club_name((byid.get(pid) or {}).get('club',''))
        if len(seq)>=2 and cur and seq[-1]!=cur:
            unsafe_pids.add(pid);unsafe_reasons[pid].add('history_does_not_end_at_current_club')
        if cur and cur in seq[:-1] and seq and seq[-1]!=cur:
            unsafe_pids.add(pid);unsafe_reasons[pid].add('club_reversion_pattern')
    history_identity_diag={'policy':'v68_current-squad-authority_previous-gws-quarantined','latest_gameweek':latest_gw,
        'unsafe_player_ids':sorted(unsafe_pids),'unsafe_players':len(unsafe_pids),'unsafe_reasons':{str(k):sorted(v) for k,v in unsafe_reasons.items()},
        'historical_rows_quarantined':0,'latest_rows_wrong_club_dropped':0,'duplicate_player_match_rows_dropped':0}
    seen_player_match=set()
'''
    block=block.replace(anchor,safety,1)
    old="""                p=byid.get(int(r['player_id']))\n                if not p:continue\n"""
    new=r'''                pid=int(r.get('player_id') or 0)
                gw=int(r.get('gameweek') or m.get('gameweek') or 0)
                rowclub=normalize_club_name(r.get('club') or (m.get('home') if key=='home_players' else m.get('away')) or '')
                curclub=normalize_club_name((byid.get(pid) or {}).get('club',''))
                if pid in unsafe_pids and gw<latest_gw:
                    history_identity_diag['historical_rows_quarantined']+=1;continue
                if pid in unsafe_pids and gw==latest_gw and curclub and rowclub!=curclub:
                    history_identity_diag['latest_rows_wrong_club_dropped']+=1;continue
                pm=(pid,int(m.get('fixture_id') or m.get('match_id') or m.get('id') or 0))
                if pm in seen_player_match:
                    history_identity_diag['duplicate_player_match_rows_dropped']+=1;continue
                seen_player_match.add(pm)
                p=byid.get(pid)
                if not p:continue
'''
    if old not in block:raise RuntimeError('aggregate player lookup anchor missing')
    block=block.replace(old,new,1)
    block=block.rstrip()+"\n    return history_identity_diag\n\n"
    return src[:start]+block+src[end:]


def patch_source(py:str)->str:
    py=replace_def(py,'scan_first_team_squads',NEW_SCAN)
    py=patch_build_players(py)
    py=patch_aggregate(py)
    # Retained match usage must not mutate current fantasy positions.
    py=py.replace("    infer_hybrid_positions_from_match_markers(rich,players_by_eid)\n","    # v68: retained history is diagnostic/scoring evidence only; current position comes from current person data.\n",1)
    # Preserve source provenance for direct labelled rich records and rows.
    py=py.replace("matches.append({**header,'competition':canonical,'competition_code':spec['code'],",
                  "matches.append({**header,'identity_source':'named_header','competition':canonical,'competition_code':spec['code'],",1)
    old="'status':'played','source':'fm_rich_stats'}"
    new="'status':'played','source':'fm_rich_stats','identity_source':m.get('identity_source','recovered_inference')}"
    if old not in py:raise RuntimeError('join match source anchor missing')
    py=py.replace(old,new,1)
    oldrow="'gameweek':fix['gameweek'],'match_id':mid})"
    newrow="'gameweek':fix['gameweek'],'match_id':mid,'identity_source':m.get('identity_source','recovered_inference')})"
    if oldrow not in py:raise RuntimeError('join row provenance anchor missing')
    py=py.replace(oldrow,newrow,1)
    # Current roster decoding must succeed for every selected first team before any history recovery is trusted.
    old="    squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)\n    game_db_rich,game_db_rich_diag=recover_game_db_rich_matches("
    new="""    squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)\n    bad_squads={eid:len(vals) for eid,vals in squads.items() if not (12<=len(vals)<=45)}\n    if squad_diag.get('missing_club_eids') or bad_squads:\n        raise RuntimeError(f\"Current first-team squad decode failed safely; missing={squad_diag.get('missing_club_eids',[])} invalid_sizes={bad_squads}. Import blocked rather than guessing from match history.\")\n    game_db_rich,game_db_rich_diag=recover_game_db_rich_matches("""
    if old not in py:raise RuntimeError('initial squad scan anchor missing')
    py=py.replace(old,new,1)
    # Remove the later history-influenced re-scan; current membership is immutable for this import.
    old="""        # Re-run squad selection with recovered participation as extra identity evidence.\n        squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)\n"""
    if old in py:py=py.replace(old,"        # v68: recovered match participation never changes current squad membership.\n",1)
    old="    players,unresolved,ambiguous=build_players(squads,selected,people,rich_raw)\n    pbyeid={int(p['pid']):p for p in players}\n"
    new="""    players,unresolved,ambiguous=build_players(squads,selected,people,rich_raw)\n    if ambiguous:\n        raise RuntimeError(f\"Current club membership is ambiguous for {len(ambiguous)} player(s); import blocked instead of resolving from match/opponent history.\")\n    pbyeid={int(p['pid']):p for p in players}\n"""
    if old not in py:raise RuntimeError('build players anchor missing')
    py=py.replace(old,new,1)
    old="    aggregate_player_history(players,rich_matches)\n"
    if old not in py:raise RuntimeError('aggregate call missing')
    py=py.replace(old,"    history_identity_diag=aggregate_player_history(players,rich_matches)\n",1)
    marker="'squad_rich_augmented_players':squad_diag['rich_augmented_players'],"
    repl=marker+"'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','history_identity_safety':history_identity_diag,"
    if marker not in py:raise RuntimeError('meta squad marker missing')
    py=py.replace(marker,repl,1)
    # Keep provenance in per-player history rows.
    oldkeys="'penalties_missed','match_position_marker']"
    newkeys="'penalties_missed','match_position_marker','identity_source']"
    if oldkeys not in py:raise RuntimeError('history key marker missing')
    py=py.replace(oldkeys,newkeys,1)
    compile(py,'fm_importer_v68.py','exec')
    return py


def main():
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    py=patch_source(py)
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v68 identity/history safety installed')

if __name__=='__main__':main()
