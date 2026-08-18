from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def html_get():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def html_put(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS);chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    if len(chunks)<len(PARTS):chunks+=['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

def replace_def(src,name,body):
    m=re.search(rf'^def {re.escape(name)}\(',src,re.M)
    if not m:raise RuntimeError(f'{name} missing')
    n=re.search(r'^def [A-Za-z0-9_]+\(',src[m.end():],re.M);end=m.end()+n.start() if n else len(src)
    return src[:m.start()]+body.rstrip()+'\n\n'+src[end:]

NEW_PICK=r'''def _rich_pick_two_squads(stats:list[dict[str,Any]]):
    """Legacy single candidate helper retained for compatibility.

    v69 match extraction uses _rich_candidate_twenty_pairs so every plausible compact
    20+20 block can be checked later against the official fixture AND strict current squads.
    """
    pairs=_rich_candidate_twenty_pairs(stats)
    return pairs[0] if pairs else None


def _rich_candidate_twenty_pairs(stats:list[dict[str,Any]]):
    pairs=[]
    if len(stats)<40:return pairs
    seen=set()
    for j in range(19,len(stats)-20):
        gap=stats[j+1]['offset']-stats[j]['offset']
        left=stats[j-19:j+1];right=stats[j+1:j+21]
        max_l=max((left[k+1]['offset']-left[k]['offset'] for k in range(19)),default=0)
        max_r=max((right[k+1]['offset']-right[k]['offset'] for k in range(19)),default=0)
        if not (gap>500 and max_l<1500 and max_r<1500):continue
        lids=tuple(int(x.get('player_id') or 0) for x in left);rids=tuple(int(x.get('player_id') or 0) for x in right)
        if len(set(lids))!=20 or len(set(rids))!=20 or set(lids)&set(rids):continue
        sig=(lids,rids)
        if sig in seen:continue
        seen.add(sig);pairs.append((left,right))
    return pairs
'''

NEW_EXTRACT=r'''def _rich_extract_member(buf:bytes,rich_team_names:dict[int,str],source_member:str):
    matches=[]
    for canonical,spec in SUPPORTED_LEAGUES.items():
        for long_name in spec['long_names']:
            competition=long_name.encode('utf-8')
            comps=[];p=0
            while True:
                p=buf.find(competition,p)
                if p<0:break
                comps.append(p);p+=1
            for i,pos in enumerate(comps):
                header=_rich_header(buf,pos,rich_team_names,competition)
                if not header:continue
                nextpos=comps[i+1] if i+1<len(comps) else min(len(buf),pos+120_000)
                end=min(nextpos,pos+120_000)
                stats=_rich_scan_stats(buf,pos,end)
                # Do not pick the first plausible 20+20 region. Retained members can contain
                # several adjacent match/team blocks (including academy/women/transient copies).
                # Emit bounded candidates; join_rich_matches later chooses ONLY a unique block
                # that agrees with the official fixture score and strict current first-team cohorts.
                options=_rich_candidate_twenty_pairs(stats)[:32]
                for hs,as_ in options:
                    first_stat=min(hs[0]['offset'],as_[0]['offset'])
                    if first_stat<pos or first_stat-pos>8000:continue
                    home=_rich_decorate(hs);away=_rich_decorate(as_)
                    matches.append({**header,'identity_source':'named_header_candidate_v69','competition':canonical,'competition_code':spec['code'],
                        'home_score':sum(x['goals'] for x in home)+sum(x['own_goals'] for x in away),
                        'away_score':sum(x['goals'] for x in away)+sum(x['own_goals'] for x in home),
                        'home_players':home,'away_players':away,'offset':pos,'source_member':source_member})
    out=[];seen=set()
    for m in matches:
        k=(m['competition'],m['home_tid'],m['away_tid'],m['home_score'],m['away_score'],
           tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))
        if k in seen:continue
        seen.add(k);out.append(m)
    return out
'''

NEW_JOIN=r'''def join_rich_matches(rich:list[dict[str,Any]],fixtures:list[dict[str,Any]],players_by_eid:dict[int,dict[str,Any]]):
    # Current fantasy positions and clubs come from current person/squad records only.
    by_pair=collections.defaultdict(list)
    for f in fixtures:
        if f['status']=='played':by_pair[(f['home'],f['away'])].append(f)

    def current_club(pid):
        p=players_by_eid.get(int(pid or 0))
        return normalize_club_name(p.get('club','')) if p else ''

    def validate_sides(home_rows,away_rows,home,away,fix):
        if not (11<=len(home_rows)<=25 and 11<=len(away_rows)<=25):return None
        hi=[int(r.get('player_id') or 0) for r in home_rows];ai=[int(r.get('player_id') or 0) for r in away_rows]
        if any(x<=0 for x in hi+ai):return None
        if len(set(hi))!=len(hi) or len(set(ai))!=len(ai) or set(hi)&set(ai):return None
        calc_h=sum(int(r.get('goals',0) or 0) for r in home_rows)+sum(int(r.get('own_goals',0) or 0) for r in away_rows)
        calc_a=sum(int(r.get('goals',0) or 0) for r in away_rows)+sum(int(r.get('own_goals',0) or 0) for r in home_rows)
        if calc_h!=int(fix.get('home_score') or 0) or calc_a!=int(fix.get('away_score') or 0):return None
        hh=sum(1 for pid in hi if current_club(pid)==home);ho=sum(1 for pid in hi if current_club(pid) not in ('',home))
        ah=sum(1 for pid in ai if current_club(pid)==away);ao=sum(1 for pid in ai if current_club(pid) not in ('',away))
        # The candidate must look substantially more like the named current first team than
        # another league club. Historical transfers may reduce overlap, so do not require 100%.
        if hh<6 or ah<6:return None
        if hh<ho+3 or ah<ao+3:return None
        return {'home_current_hits':hh,'home_other_current_hits':ho,'away_current_hits':ah,'away_other_current_hits':ao,
                'score_exact':True,'side_sizes':[len(home_rows),len(away_rows)],
                'quality':hh+ah-2*(ho+ao)}

    proposals=collections.defaultdict(list)
    for m in rich:
        home=normalize_club_name(m.get('home',''));away=normalize_club_name(m.get('away',''))
        candidates=by_pair.get((home,away),[])
        if m.get('date'):
            dated=[f for f in candidates if f.get('date')==m.get('date')]
            if dated:candidates=dated
        # Never fall back to same-team fixture when the decoded score conflicts. Player-level
        # history is optional evidence; official result identity is not.
        exact=[f for f in candidates if int(f.get('home_score') or 0)==int(m.get('home_score') or 0) and int(f.get('away_score') or 0)==int(m.get('away_score') or 0)]
        if len(exact)!=1:continue
        fix=exact[0];home_rows=list(m.get('home_players') or []);away_rows=list(m.get('away_players') or [])
        val=validate_sides(home_rows,away_rows,home,away,fix)
        if not val:continue
        source=str(m.get('identity_source') or 'recovered_inference')
        source_bonus=4 if source.startswith('named_header') else 0
        ids_sig=(tuple(int(r.get('player_id') or 0) for r in home_rows),tuple(int(r.get('player_id') or 0) for r in away_rows))
        proposals[int(fix['fixture_id'])].append((val['quality']+source_bonus,source_bonus,ids_sig,m,fix,val,home,away))

    out=[];mid=0
    for fixture_id,opts in sorted(proposals.items()):
        opts.sort(key=lambda x:(x[0],x[1]),reverse=True)
        best=opts[0]
        # Collapse exact duplicate identities first. If two genuinely different player blocks
        # tie for best evidence, leave the fixture without player detail rather than guessing.
        unique=[];seen=set()
        for o in opts:
            if o[2] in seen:continue
            seen.add(o[2]);unique.append(o)
        if len(unique)>1 and unique[1][0]>=unique[0][0]:continue
        _q,_sb,_sig,m,fix,val,home,away=unique[0];mid+=1
        mm={'id':mid,'match_id':mid,'fixture_id':fix['fixture_id'],'gameweek':fix['gameweek'],'date':fix['date'],'home':home,'away':away,
            'home_score':fix['home_score'],'away_score':fix['away_score'],'status':'played','source':'fm_rich_stats',
            'identity_source':m.get('identity_source','recovered_inference'),'identity_validation':val}
        allp=[]
        for side,key,club,opp,venue in [('home','home_players',home,away,'H'),('away','away_players',away,home,'A')]:
            arr=[]
            for r in m[key]:
                eid=int(r['player_id']);canon=players_by_eid.get(eid)
                pos=canon['pos'] if canon else ('GK' if r.get('is_goalkeeper_match_role') else 'MID')
                name=canon['name'] if canon else r.get('player',f'FM Player {eid}')
                row=dict(r);row.update({'player_id':str(eid),'name':name,'club':club,'pos':pos,'opponent':opp,'venue':venue,'home':home,'away':away,
                    'score':f"{fix['home_score']}-{fix['away_score']}",'gameweek':fix['gameweek'],'match_id':mid,
                    'identity_source':m.get('identity_source','recovered_inference')})
                row.update(score_player(row,pos));arr.append(row);allp.append(row)
            mm[side+'_players']=arr
        award_bonus(allp);out.append(mm)
    return out
'''

def patch(py):
    py=replace_def(py,'_rich_pick_two_squads',NEW_PICK)
    py=replace_def(py,'_rich_extract_member',NEW_EXTRACT)
    py=replace_def(py,'join_rich_matches',NEW_JOIN)
    # Tag inferred recovery records so direct named candidates can win safely.
    py=py.replace("'source':'unlabelled_retained_match'", "'source':'unlabelled_retained_match','identity_source':'recovered_inference_v69'")
    py=py.replace("'source':'game_db_retained_match'", "'source':'game_db_retained_match','identity_source':'recovered_inference_v69'")
    # Require full player-detail coverage for each fully completed non-blank Gameweek.
    old="    rich_matches=join_rich_matches(rich_raw,fixtures,pbyeid) if rich_raw else []\n    history_identity_diag=aggregate_player_history(players,rich_matches)\n"
    new="""    rich_matches=join_rich_matches(rich_raw,fixtures,pbyeid) if rich_raw else []\n    _rich_fixture_ids={int(m.get('fixture_id') or 0) for m in rich_matches}\n    _coverage={}\n    for _gw in sorted({int(f.get('gameweek') or 0) for f in fixtures if int(f.get('gameweek') or 0)>0}):\n        _pf=[f for f in fixtures if int(f.get('gameweek') or 0)==_gw and f.get('status')=='played']\n        _coverage[str(_gw)]={'played_fixtures':len(_pf),'rich_fixtures':sum(1 for f in _pf if int(f.get('fixture_id') or 0) in _rich_fixture_ids),\n                            'missing_fixture_ids':[int(f.get('fixture_id') or 0) for f in _pf if int(f.get('fixture_id') or 0) not in _rich_fixture_ids]}\n    history_identity_diag=aggregate_player_history(players,rich_matches)\n"""
    if old not in py:raise RuntimeError('rich join/aggregate anchor missing')
    py=py.replace(old,new,1)
    marker="'history_identity_safety':history_identity_diag,"
    if marker not in py:raise RuntimeError('v68 history meta marker missing')
    py=py.replace(marker,marker+"'rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','rich_fixture_coverage':_coverage,",1)
    compile(py,'fm_importer_v69.py','exec')
    return py

def main():
    html=html_get();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 missing')
    py=base64.b64decode(m.group(1)).decode();py=patch(py)
    b64=base64.b64encode(py.encode()).decode();patched=html[:m.start(1)]+b64+html[m.end(1):]
    html_put(patched);assert html_get()==patched
    print('v69 rich match validation installed')

if __name__=='__main__':main()
