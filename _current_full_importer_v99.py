from __future__ import annotations
CURRENT_SQUAD_UID_PAIR_POLICY='duplicate-club-uid-team-header-v78'
CURRENT_SQUAD_SINGLE_MISSING_POLICY='23-of-24-strong-plus-current-person-proof-v77'
CURRENT_SQUAD_FOOTER_POLICY='positive-structure-first-consensus-only-legacy-v76'
FIXTURE_DB_HANDOFF_POLICY='loaded-game-db-bytes-v74'

import bisect
import collections
import datetime as dt
import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CHAMPIONSHIP_FIXTURE_COMP_ID = 206  # Legacy FM26 hint only; never trusted without identity validation.
SUPPORTED_LEAGUES = {
    'Premier League': {'code':'eng_prem','teams':20,'rounds':38,'fixtures':380,'per_round':10,
                       'long_names':('Premier League','English Premier Division')},
    'EFL Championship': {'code':'eng_champ','teams':24,'rounds':46,'fixtures':552,'per_round':12,
                         'long_names':('Sky Bet Championship','EFL Championship')},
}
POSITION_NAMES = ["GK","SW","DL","DC","DR","DM","ML","MC","MR","AML","AMC","AMR","ST","WBL","WBR"]
DEF_SLOTS = {1,2,3,4,13,14}
MID_SLOTS = {5,6,7,8,9,10,11}
FWD_SLOT = 12


def u16(b: bytes, o: int) -> int: return struct.unpack_from('<H', b, o)[0]
def u32(b: bytes, o: int) -> int: return struct.unpack_from('<I', b, o)[0]


def fm_date(stamp: int, year: int) -> str:
    doy = stamp & 0x1FF
    return (dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)).isoformat()


@dataclass
class Club:
    eid: int
    uid: int
    name: str
    short: str
    nation_id: int


@dataclass
class Person:
    eid: int
    uid: int
    offset: int
    name: str
    common_name: str | None
    first_name: str | None = None
    surname: str | None = None
    positions: list[int] | None = None
    current_ability: int | None = None
    potential_ability: int | None = None

    @property
    def display_name(self) -> str:
        # FM stores legal/full identity separately from the football-facing common name.
        # Prefer common/known-as + the structured football surname when available.
        c=(self.common_name or '').strip()
        sn=(self.surname or '').strip()
        if c:
            lc=c.casefold(); ls=sn.casefold()
            if not sn or lc==ls or ls in lc.split():
                return c
            # A multi-token common name is already an explicit display-style identity.
            if len(c.split())>1:
                return c
            return f'{c} {sn}'.strip()
        return self.name


def _season_start_for_date(date_text:str)->int:
    d=dt.date.fromisoformat(date_text)
    return d.year if d.month>=7 else d.year-1




def _normalize_gameweeks(rows:list[dict[str,Any]])->dict[str,Any]:
    """Convert FM nominal league rounds into FPL-style calendar Gameweeks.

    The number of Gameweeks is inferred from the selected league (38 or 46). Rescheduled
    league fixtures are assigned by their actual calendar date, creating genuine doubles
    and blanks without changing the underlying league fixture set.
    """
    by_raw=collections.defaultdict(list)
    for r in rows: by_raw[r['raw_gameweek']].append(r)

    profiles=[]
    for raw,rr in by_raw.items():
        ords=sorted(dt.date.fromisoformat(x['date']).toordinal() for x in rr)
        median=ords[len(ords)//2] if len(ords)%2 else (ords[len(ords)//2-1]+ords[len(ords)//2])/2
        expected=max(1,len(rr))
        core=[o for o in ords if abs(o-median)<=4]
        if len(core)<max(4,expected//2): core=ords
        profiles.append({'raw':raw,'median':median,'core_start':min(core),'core_end':max(core),'fixture_count':len(rr)})

    profiles.sort(key=lambda x:(x['median'],x['raw']))
    total_rounds=len(profiles)
    raw_order={p['raw']:i+1 for i,p in enumerate(profiles)}

    boundaries=[]
    for i,p in enumerate(profiles):
        start=int(p['core_start'])
        if boundaries and start<=boundaries[-1]:
            prev_med=profiles[i-1]['median']
            midpoint=int(math.floor((prev_med+p['median'])/2))+1
            start=max(boundaries[-1]+1,midpoint)
        boundaries.append(start)

    reassigned=[]
    for r in rows:
        day=dt.date.fromisoformat(r['date']).toordinal()
        cal=bisect.bisect_right(boundaries,day)
        gw=min(total_rounds,max(1,cal))
        nominal=raw_order[r['raw_gameweek']]
        r['round_gameweek']=nominal;r['gameweek']=gw;r['calendar_reassigned']=gw!=nominal
        if gw!=nominal:
            reassigned.append({'home_tid':r['home_tid'],'away_tid':r['away_tid'],'date':r['date'],
                               'raw_gameweek':r['raw_gameweek'],'nominal_gameweek':nominal,'fantasy_gameweek':gw})

    windows=[]
    for i,start in enumerate(boundaries):
        end=(boundaries[i+1]-1) if i+1<len(boundaries) else None
        windows.append({'gameweek':i+1,'start':dt.date.fromordinal(start).isoformat(),
                        'end':dt.date.fromordinal(end).isoformat() if end else None,'raw_round':profiles[i]['raw']})
    return {'raw_round_order':raw_order,'raw_round_relabels':{raw:new for raw,new in raw_order.items() if raw!=new},
            'calendar_windows':windows,'calendar_reassigned_count':len(reassigned),
            'calendar_reassigned_examples':reassigned[:24],'total_gameweeks':total_rounds}

def scan_fixture_groups(fix:bytes)->list[dict[str,Any]]:
    """Scan plausible fixture records and split them by competition and season.

    A candidate is considered a supported full league season when it matches either a
    20-team/38-round/380-fixture Premier League shape or a 24-team/46-round/552-fixture
    Championship shape. The competition id itself is not trusted because FM ids can move
    between databases and future seasons.
    """
    raw=[]
    for p in range(11,len(fix)-40):
        if fix[p+4:p+7] != b'\xff\x00\x00' or fix[p+11:p+13] != b'\xff\x00':
            continue
        comp=u32(fix,p-11); home,away=u32(fix,p),u32(fix,p+7)
        stamp,year=u16(fix,p+13),u16(fix,p+15); doy=stamp&0x1FF; gw0=fix[p+38]
        if not (1<=doy<=366 and 2024<=year<=2045 and 0<=gw0<=60):continue
        date=fm_date(stamp,year)
        raw.append({'fixture_offset':p,'competition_id':comp,'home_tid':home,'away_tid':away,
                    'date':date,'date_stamp':stamp,'year':year,'raw_gameweek':gw0+1,'gameweek':gw0+1,
                    'season_start':_season_start_for_date(date),'status':'future','home_score':None,'away_score':None,
                    'source':'fm_fix_man'})
    grouped=collections.defaultdict(list)
    for r in raw: grouped[(r['competition_id'],r['season_start'])].append(r)
    groups=[]
    shapes={(v['fixtures'],v['teams'],v['rounds'],v['per_round']):name for name,v in SUPPORTED_LEAGUES.items()}
    for (comp,season),rows in grouped.items():
        ded=[];seen=set()
        for r in sorted(rows,key=lambda x:x['fixture_offset']):
            k=(r['home_tid'],r['away_tid'],r['date'],r['raw_gameweek'])
            if k in seen:continue
            seen.add(k);ded.append(r)
        teams={x for r in ded for x in (r['home_tid'],r['away_tid'])}
        gws=collections.Counter(r['raw_gameweek'] for r in ded)
        league_name=None
        for (fixture_count,team_count,round_count,per_round),name in shapes.items():
            if (len(ded)==fixture_count and len(teams)==team_count and
                set(gws)==set(range(1,round_count+1)) and all(v==per_round for v in gws.values())):
                league_name=name;break
        groups.append({'competition_id':comp,'season_start':season,'rows':ded,'teams':teams,'gws':gws,
                       'exact':league_name is not None,'league_shape':league_name})
    return groups


def select_championship_fixtures(fix:bytes,clubs:dict[int,Club],expected_names:set[str]|None=None,
                                 expected_league:str|None=None,db:bytes|None=None)->tuple[list[dict[str,Any]],dict[str,Any]]:
    """Select the current supported domestic league and PROVE its fixture-team -> club mapping.

    v73: a 20/24-team calendar shape is not club identity evidence.  Every candidate fixture
    mapping must also decode a plausible CURRENT senior squad for every selected club from
    game_db.dat. Retained match history is never used to move/select current clubs.
    """
    groups=scan_fixture_groups(fix)
    exact_all=[g for g in groups if g['exact']]
    if not exact_all:
        near=sorted(groups,key=lambda g:(abs(len(g['teams'])-24),-g['season_start']))[:10]
        summary='; '.join(f"comp={g['competition_id']} season={g['season_start']} fixtures={len(g['rows'])} teams={len(g['teams'])} gws={len(g['gws'])} shape={g.get('league_shape')}" for g in near)
        raise RuntimeError('No supported full league season could be identified. Candidates: '+summary)

    requested=expected_league if expected_league in SUPPORTED_LEAGUES else None
    if requested:
        exact=[g for g in exact_all if g.get('league_shape')==requested]
        if not exact:
            raise RuntimeError(f'Manual league selection was {requested}, but no complete {requested} season exists in this save. The selection will not be overridden.')
        newest=max(g['season_start'] for g in exact)
        exact=[g for g in exact if g['season_start']==newest]
        selection_mode='user_preference_locked'
    else:
        newest=max(g['season_start'] for g in exact_all)
        exact=[g for g in exact_all if g['season_start']==newest]
        shapes={g.get('league_shape') for g in exact}
        if len(shapes)>1:
            summary=', '.join(sorted(str(x) for x in shapes))
            raise RuntimeError(f'Current season {newest}/{str(newest+1)[-2:]} contains both supported English leagues ({summary}). Historical retained-match identity is deliberately ignored because a promoted/relegated human club may have old division data. Choose the current league once; the choice will be locked for this import.')
        selection_mode='auto_latest_season'

    if db is None:
        raise RuntimeError('Current-season club identity validation requires game_db.dat; unsafe fixture-only mapping is disabled.')

    scored=[]
    candidate_debug=[]
    for g in exact:
        try:
            shifts=_fixture_to_club_shift_candidates(g['teams'],clubs)
        except Exception as e:
            candidate_debug.append({'competition_id':g['competition_id'],'season_start':g['season_start'],
                                    'league_shape':g.get('league_shape'),'error':str(e)})
            continue
        for sh in shifts:
            try:
                ev=_fixture_shift_current_squad_evidence(g['teams'],clubs,sh,db,expected_names if requested else None)
                ev.update({'competition_id':g['competition_id'],'season_start':g['season_start'],'league_shape':g.get('league_shape')})
                candidate_debug.append(ev)
                # The exact same squad-size invariant enforced at publish time is required BEFORE
                # a shift is eligible.  A nearby English club entity (the v72 +1-EID failure)
                # therefore cannot win merely because it is English.
                if ev['safe_squad_clubs'] != len(g['teams']):
                    continue
                overlap=ev['expected_name_overlap']
                legacy_hint=1 if (g.get('league_shape')=='EFL Championship' and g['competition_id']==CHAMPIONSHIP_FIXTURE_COMP_ID) else 0
                # Prefer fewer duplicated current-list memberships, then any direct expected-name
                # evidence, then the legacy competition hint only as a late deterministic tie-break.
                score=(ev['safe_squad_clubs'],-ev['duplicate_current_memberships'],overlap,legacy_hint,-abs(sh),-g['competition_id'])
                scored.append((score,g,sh,ev))
            except Exception as e:
                candidate_debug.append({'competition_id':g['competition_id'],'season_start':g['season_start'],
                                        'league_shape':g.get('league_shape'),'shift':sh,'error':str(e)})
    if not scored:
        summary='; '.join(
            f"comp={x.get('competition_id')} shift={x.get('shift')} safe={x.get('safe_squad_clubs','?')}/{x.get('team_count','?')} missing={','.join(x.get('unsafe_squad_names',[])[:4]) or '-'} v78={x.get('squad_resolution_evidence',{}).get('single_missing_completion_evidence') or x.get('single_missing_completion_evidence') or '-'}"
            for x in candidate_debug[:16]
        )
        raise RuntimeError('Supported fixture calendars were found, but no fixture-to-club mapping passed current first-team squad validation. '+summary)
    scored.sort(key=lambda x:x[0],reverse=True)
    score,g,shift,chosen_ev=scored[0]
    # If two mappings are equally proven through all identity evidence, do not guess.
    if len(scored)>1 and scored[1][0]==score and scored[1][2]!=shift:
        raise RuntimeError(f'Fixture-to-club identity remains ambiguous between shifts {shift} and {scored[1][2]}; import blocked rather than guessing.')
    rows=g['rows'];gw_info=_normalize_gameweeks(rows);spec=SUPPORTED_LEAGUES[g['league_shape']]
    info={'competition_id':g['competition_id'],'season_start':g['season_start'],'fixture_to_club_shift':shift,
          'candidate_groups':len(groups),'exact_candidate_groups':len(exact_all),
          'current_season_candidate_groups':len(exact),'current_season_candidates':candidate_debug[:48],
          'requested_league':requested,'selection_mode':selection_mode,
          'rich_name_overlap':chosen_ev['expected_name_overlap'],'competition':g['league_shape'],'competition_code':spec['code'],
          'team_count':spec['teams'],'total_gameweeks':spec['rounds'],'fixture_count':spec['fixtures'],
          'fixture_club_mapping_policy':'current-squad-validated-shift-v73',
          'selected_mapping_evidence':chosen_ev,
          'gameweek_relabels':gw_info['raw_round_relabels'],'calendar_gameweek_windows':gw_info['calendar_windows'],
          'calendar_reassigned_count':gw_info['calendar_reassigned_count'],
          'calendar_reassigned_examples':gw_info['calendar_reassigned_examples']}
    return rows,info

def scan_clubs(db: bytes) -> dict[int, Club]:
    # Scan only FFFFFFFF anchors, then validate the proven entity-head shape 22 bytes before name length.
    out: dict[int,Club] = {}
    for m in re.finditer(b'\xff\xff\xff\xff', db):
        ff=m.start(); len_at=ff+22
        if len_at < 39 or len_at+8 >= len(db): continue
        try:
            n1=u32(db,len_at)
            if not 3<=n1<=64: continue
            ns=len_at+4
            name=db[ns:ns+n1].decode('utf-8')
            sa=ns+n1; n2=u32(db,sa)
            if not 2<=n2<=32: continue
            short=db[sa+4:sa+4+n2].decode('utf-8')
            if not name or not short or any(ord(c)<32 for c in name+short): continue
            ff2=u32(db,len_at-22)
            if ff2 != 0xFFFFFFFF: continue
            eid=u32(db,len_at-39); uid=u32(db,len_at-35); uid2=u32(db,len_at-31)
            zero=db[len_at-27]
            nation1=u32(db,len_at-14); loc=u32(db,len_at-18); nation3=u32(db,len_at-26)
            if zero!=0 or eid in (0,0xFFFFFFFF) or uid in (0,0xFFFFFFFF) or uid!=uid2: continue
            if not (nation1==nation3 or nation1==loc or nation3==loc): continue
            if any(x==0 or x>10000 for x in (nation1,loc,nation3)): continue
            out[eid]=Club(eid,uid,name,short,nation1)
        except Exception:
            continue
    return out


def _fixture_to_club_shift_candidates(team_ids:set[int],clubs:dict[int,Club])->list[int]:
    """Return every constant shift that maps ALL fixture team ids to decoded English clubs."""
    english={eid for eid,c in clubs.items() if c.nation_id==139}
    counts=collections.Counter()
    for shift in range(-512,513):
        n=sum(1 for tid in team_ids if tid-shift in english)
        if n:counts[shift]=n
    if not counts:raise RuntimeError('Could not link fixture team ids to club entity ids')
    full=sorted(sh for sh,n in counts.items() if n==len(team_ids))
    if not full:
        best=max(counts.values())
        raise RuntimeError(f'Fixture→club identity mapping incomplete ({best}/{len(team_ids)})')
    return full


def derive_fixture_to_club_shift(team_ids:set[int],clubs:dict[int,Club],expected_names:set[str]|None=None)->int:
    """Compatibility helper. Production selection validates each full shift against current squads."""
    tied=_fixture_to_club_shift_candidates(team_ids,clubs)
    if expected_names:
        def score(sh):
            mapped={normalize_club_name(clubs[tid-sh].short or clubs[tid-sh].name) for tid in team_ids}
            return len(mapped & expected_names)
        tied.sort(key=lambda sh:(score(sh),-abs(sh)),reverse=True)
    return tied[0]


def _fixture_shift_current_squad_evidence(team_ids:set[int],clubs:dict[int,Club],shift:int,db:bytes,
                                           expected_names:set[str]|None=None)->dict[str,Any]:
    selected={tid-shift:clubs[tid-shift] for tid in team_ids if tid-shift in clubs}
    if len(selected)!=len(team_ids):
        raise RuntimeError(f'shift {shift} does not map every fixture team to a club')
    mapped={normalize_club_name(c.short or c.name) for c in selected.values()}
    squads,diag=scan_first_team_squads(db,selected,None)
    sizes={eid:len(squads.get(eid,[])) for eid in selected}
    # scan_first_team_squads already restricts >45 to an exact current-team header.
    # Therefore the mapping validator can safely recognise that proven extended roster.
    safe={eid:n for eid,n in sizes.items() if CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX}
    unsafe=[normalize_club_name(selected[eid].short or selected[eid].name) for eid,n in sizes.items() if not (CURRENT_SQUAD_MIN<=n<=CURRENT_SQUAD_STRICT_MAX)]
    memberships=collections.Counter()
    for vals in squads.values():
        for pid in set(vals):memberships[pid]+=1
    dup=sum(1 for n in memberships.values() if n>1)
    return {
        'shift':shift,
        'team_count':len(team_ids),
        'mapped_clubs':sorted(mapped),
        'safe_squad_clubs':len(safe),
        'unsafe_squad_names':sorted(unsafe),
        'squad_sizes':{normalize_club_name(selected[eid].short or selected[eid].name):n for eid,n in sorted(sizes.items())},
        'duplicate_current_memberships':dup,
        'expected_name_overlap':len(mapped & expected_names) if expected_names else 0,
        'squad_policy':diag.get('policy'),
        'squad_resolution_policy':diag.get('block_policy'),
        'squad_missing_club_eids':list(diag.get('missing_club_eids',[])),
        'squad_resolution_evidence':{'fallbacks':diag.get('fallbacks',[]),'resolved':diag.get('resolved_squad_blocks',[]),'ambiguous':diag.get('ambiguous_squad_blocks',[]),'rejected_options':diag.get('rejected_options',0),'overlap_unions':diag.get('overlap_union_squad_blocks',0),'single_missing_attempted':diag.get('single_missing_completion_attempted',False),'single_missing_accepted':diag.get('single_missing_completion_accepted',False),'single_missing_evidence':diag.get('single_missing_completion_evidence')},
        'mapping_proof':'all-fixture-teams-map-to-English-clubs + current-db-roster-proof-v79','current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY,
    }

CURRENT_SQUAD_MIN=12
CURRENT_SQUAD_STANDARD_MAX=45
CURRENT_SQUAD_STRICT_MAX=60
CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'


def read_squad_list_legacy(db: bytes, head: int, next_head: int|None=None) -> list[int]:
    """Original squad-list reader retained as a weak fallback for schema compatibility."""
    end=min(next_head or len(db), head+6000)
    at=head+26
    while at+6<end:
        p=db.find(b'\xff\xff\xff\xff',at,end)
        if p<0:return []
        cnt=u16(db,p+4)
        if 1<=cnt<=80:
            list_at=p+6; list_end=list_at+cnt*4
            if list_end+8<=end:
                vals=[u32(db,list_at+i*4) for i in range(cnt)]
                if all(0<v<3_000_000 for v in vals) and len(set(vals))==cnt:
                    cap=u32(db,list_end); vice=u32(db,list_end+4)
                    consistent=lambda v: v in (0,0xFFFFFFFF) or v in vals
                    asc=sum(1 for a,b in zip(vals[:7],vals[1:8]) if a<b)
                    if (asc>=min(6,max(0,len(vals)-1)) or cap in vals or vice in vals or (consistent(cap) and consistent(vice))):
                        return vals
        at=p+1
    return []


def read_squad_list(db: bytes, head: int, next_head: int|None=None) -> list[int]:
    """Prefer squad blocks with positive structural support.

    v76: a footer where captain and vice are both sentinel values (0/FFFFFFFF) is not,
    by itself, evidence that an arbitrary integer array is a current first-team squad.
    The original permissive decoder is retained separately and may only be used later
    when repeated current-DB blocks independently agree on exactly the same membership.
    """
    end=min(next_head or len(db), head+6000)
    at=head+26
    sentinels=(0,0xFFFFFFFF)
    while at+6<end:
        p=db.find(b'\xff\xff\xff\xff',at,end)
        if p<0:return []
        cnt=u16(db,p+4)
        if 1<=cnt<=80:
            list_at=p+6; list_end=list_at+cnt*4
            if list_end+8<=end:
                vals=[u32(db,list_at+i*4) for i in range(cnt)]
                if all(0<v<3_000_000 for v in vals) and len(set(vals))==cnt:
                    cap=u32(db,list_end); vice=u32(db,list_end+4)
                    consistent=lambda v: v in sentinels or v in vals
                    asc=sum(1 for a,b in zip(vals[:7],vals[1:8]) if a<b)
                    ordered=asc>=min(6,max(0,len(vals)-1))
                    linked=(cap in vals) or (vice in vals)
                    non_sentinel_footer=(cap not in sentinels) or (vice not in sentinels)
                    coherent_footer=non_sentinel_footer and consistent(cap) and consistent(vice)
                    if ordered or linked or coherent_footer:
                        return vals
        at=p+1
    return []

def _rich_members_by_club(rich:list[dict[str,Any]]|None, selected_clubs:dict[int,Club])->dict[int,set[int]]:
    out=collections.defaultdict(set)
    if not rich:return out
    byname={}
    for eid,c in selected_clubs.items():
        byname[normalize_club_name(c.name)]=eid
        byname[normalize_club_name(c.short)]=eid
    for m in rich:
        for side,key in (('home','home_players'),('away','away_players')):
            ceid=byname.get(normalize_club_name(m.get(side,'')))
            if ceid is None:continue
            for r in m.get(key,[]):
                try:out[ceid].add(int(r['player_id']))
                except Exception:pass
    return out


def selected_rich_team_aliases(selected_clubs:dict[int,Club])->dict[int,str]:
    """Build unambiguous match-header aliases only for clubs in the already-selected league.

    This is deliberately post-selection: it cannot influence which league/season is selected.
    It exists only to recover player history in saves whose retained match headers use a
    different team-id namespace from the original Championship regression save.
    """
    aliases=collections.defaultdict(set)
    for c in selected_clubs.values():
        name=normalize_club_name(c.short or c.name)
        for key in (c.uid+1,c.uid,c.eid,c.eid+1):
            if isinstance(key,int) and key>0: aliases[key].add(name)
    return {k:next(iter(v)) for k,v in aliases.items() if len(v)==1}


def _choose_current_squad_option_v75(db:bytes,eid:int,options:list[tuple[int,list[int],str]],diag:dict[str,Any]):
    """Resolve multiple CURRENT-DB squad blocks without using retained match history.

    Exact copies are consensus. Near-identical current snapshots may be unioned. Truly
    different blocks (e.g. senior vs development team) are resolved only when current
    person records provide a clear senior-quality separation; otherwise remain ambiguous.
    """
    priority={'strict':3,'paired_uid_v75':2,'relaxed_uid':1}
    valid=[]
    for p,vals,kind in options:
        # v79: exact current-team headers may legitimately include an academy-inclusive
        # current roster above 45.  Only the strongest exact EID+duplicated-UID structure
        # gets the extended ceiling; weaker compatibility fallbacks remain capped at 45.
        limit=CURRENT_SQUAD_STRICT_MAX if kind=='strict' else CURRENT_SQUAD_STANDARD_MAX
        if not (CURRENT_SQUAD_MIN<=len(vals)<=limit):
            diag['rejected_options']+=1;continue
        vals=list(dict.fromkeys(int(x) for x in vals if int(x)>0))
        if not (CURRENT_SQUAD_MIN<=len(vals)<=limit):
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
    union_limit=CURRENT_SQUAD_STRICT_MAX if best>=priority['strict'] else CURRENT_SQUAD_STANDARD_MAX
    if len(sets)>=2 and min_j>=0.72 and CURRENT_SQUAD_MIN<=len(union)<=union_limit:
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
            # v82: ability is useful reverse-engineering evidence, but it is not structural
            # proof that one conflicting CURRENT-DB block is the authoritative senior squad.
            # Keep the ranking for diagnostics and future schema learning; do not let CA
            # silently override a real current-database disagreement.
            diag.setdefault('ability_only_resolution_quarantined',0)
            diag['ability_only_resolution_quarantined']+=1
            diag.setdefault('ability_profile_evidence',[]).append({
                'club_eid':eid,'method':'current_person_ability_profile_evidence_v82',
                'candidate_offset':one['offset'],'players':len(one['vals']),
                'resolved_people':one['resolved'],'top16avg':round(one['top16avg'],1),
                'median_ca':round(one['median_ca'],1),
                'runner_up_top16avg':round(two['top16avg'],1) if two else None,
                'authoritative':False
            })

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
                 'policy':'strict_current_db_membership_only_v68','block_policy':'v82-current-db-consensus-only-ability-non-authoritative',
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

    # v77: near-complete current-DB mapping completion.
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
        # A duplicated club-UID header is stronger than generic legacy arrays because its
        # location is learned from the same current-team structure used by the 23 proven clubs.
        uid_proven=[x for x in proven if x.get('kind')=='uid_pair_header_v78']
        basis=uid_proven if uid_proven else proven
        groups=collections.defaultdict(list)
        for x in basis:groups[tuple(sorted(set(x['vals'])))].append(x)
        if len(groups)==1 and basis:
            chosen=basis[0]['vals'];method='single_missing_uid_pair_current_db_completion_v78' if uid_proven else 'single_missing_current_db_completion_v77'
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

HEADER_PAT=re.compile(rb'.{3}[\x00-\x4c][\x00-\xfa]\x00\x00\x00', re.S)

def _read_string_entry(db:bytes,at:int):
    if at+8>len(db): return None
    iid=u32(db,at); ln=u32(db,at+4)
    if iid>5_000_000 or ln>250 or at+8+ln>len(db): return None
    try:s=db[at+8:at+8+ln].decode('utf-8')
    except UnicodeDecodeError:return None
    if any(ord(c)<32 for c in s):return None
    return iid,s,at+8+ln


def _chain_len(db:bytes,at:int,n:int=64)->int:
    p=at
    for i in range(n):
        e=_read_string_entry(db,p)
        if not e:return i
        p=e[2]
    return n


def find_name_pool_index(db:bytes):
    # Keep only compact ID-membership bytearrays, not ~1M Python strings.
    # Target player names are resolved in a second tiny pass after EID binding.
    pos=int(len(db)*0.25);search_end=int(len(db)*0.72)
    pools=[];bounds=[];end_offset=0
    while len(pools)<3:
        found=None
        for m in HEADER_PAT.finditer(db,pos,search_end):
            if _chain_len(db,m.start(),64)>=64:
                found=m.start();break
        if found is None:raise RuntimeError('FM name string table not found')
        q=found;membership=bytearray();count=0
        while True:
            e=_read_string_entry(db,q)
            if not e:break
            iid,_text,q=e;count+=1
            if iid>=len(membership):membership.extend(b'\x00'*(iid+1-len(membership)))
            membership[iid]=1
        if count>=10_000:
            pools.append(membership);bounds.append((found,q));end_offset=q
        pos=q+1
    return pools[0],pools[1],pools[2],bounds,end_offset


def _pool_has(pool:bytearray,iid:int)->bool:
    return 0<=iid<len(pool) and bool(pool[iid])


PERSON_PREFIX_RE=re.compile(rb'(?=(.{4}\x00.{4}\x00.{4}\x00))', re.S)

def scan_person_offsets(db:bytes,start:int,forenames:bytearray,surnames:bytearray):
    offsets=[]
    for m in PERSON_PREFIX_RE.finditer(db,start):
        at=m.start();first=u32(db,at);sur=u32(db,at+5)
        if not _pool_has(forenames,first) or not _pool_has(surnames,sur):continue
        body=at+15
        if body+8>len(db):continue
        ln=u32(db,body)
        if ln==0:
            body+=4
        elif 2<=ln<=64 and body+4+ln+4<=len(db) and u16(db,body+2)==0:
            raw=db[body+4:body+4+ln]
            try:text=raw.decode('utf-8')
            except UnicodeDecodeError:continue
            if any(ord(c)<32 for c in text):continue
            body+=4+ln
        else:continue
        year=u16(db,body+2);doy=u16(db,body)
        if 1920<=year<=2030 and 1<=doy<=366:offsets.append(at)
    return offsets


IDENTITY_RE=re.compile(rb'\x00\x00\x00(?P<eid>.{4})(?P<uid>.{4})(?P=uid)', re.S)

def identity_chain(db:bytes,start:int):
    cand=[]
    for m in IDENTITY_RE.finditer(db,start):
        at=m.start()+3;eid=u32(db,at);uid=u32(db,at+4)
        if not (0<eid<3_000_000 and uid not in (0,0xFFFFFFFF)):continue
        if eid%256==0 and uid%256==0 and at+13<=len(db):
            if u32(db,at+1)==eid//256 and u32(db,at+5)==uid//256 and u32(db,at+9)==uid//256:continue
        cand.append((at,eid,uid))
    tails=[];tails_idx=[];prev=[-1]*len(cand)
    for i,(_,eid,_) in enumerate(cand):
        k=bisect.bisect_left(tails,eid);prev[i]=tails_idx[k-1] if k else -1
        if k==len(tails):tails.append(eid);tails_idx.append(i)
        elif eid<tails[k]:tails[k]=eid;tails_idx[k]=i
    chain=[];cur=tails_idx[-1] if tails_idx else -1
    while cur>=0:chain.append(cand[cur]);cur=prev[cur]
    chain.reverse();return chain


ABILITY_RE=re.compile(rb'(?=([\x01-\x14]{15}[\x01-\x64]{54}))', re.S)

def scan_target_abilities(db:bytes,person_offsets:list[int],target_offsets:set[int]):
    best={}
    for m in ABILITY_RE.finditer(db):
        pos_start=m.start();attr_start=pos_start+15
        if attr_start<39:continue
        ca=db[attr_start-39];pa=db[attr_start-37]
        if ca==0 or ca>200 or pa>200 or pa<ca:continue
        idx=bisect.bisect_right(person_offsets,attr_start)
        if idx>=len(person_offsets):continue
        po=person_offsets[idx]
        if po not in target_offsets:continue
        dist=po-attr_start
        if dist>50_000:continue
        prev=best.get(po)
        if prev is None or dist<prev[0]:best[po]=(dist,list(db[pos_start:attr_start]),ca,pa)
    return {po:(positions,ca,pa) for po,(_dist,positions,ca,pa) in best.items()}


def _prefix_ids(db:bytes,at:int):
    first=u32(db,at);sur=u32(db,at+5);com=u32(db,at+10);body=at+15;ln=u32(db,body)
    inline=None
    if ln==0:body+=4
    else:
        try:inline=db[body+4:body+4+ln].decode('utf-8')
        except UnicodeDecodeError:inline=None
        body+=4+ln
    return first,sur,com,inline


def resolve_pool_ids(db:bytes,bound:tuple[int,int],wanted:set[int])->dict[int,str]:
    if not wanted:return {}
    out={};q=bound[0];end=bound[1]
    while q<end and len(out)<len(wanted):
        e=_read_string_entry(db,q)
        if not e:break
        iid,text,q=e
        if iid in wanted:out[iid]=text
    return out


def bind_target_people(db:bytes,target_eids:set[int]):
    fore_index,sur_index,_common_index,bounds,table_end=find_name_pool_index(db)
    # Full person offset spine is compact (~75k integers) and is needed to stop an
    # ability block belonging to a neighbouring non-target person being misbound.
    person_offsets=scan_person_offsets(db,table_end,fore_index,sur_index)
    chain=identity_chain(db,table_end)
    targets={eid:(iat,uid) for iat,eid,uid in chain if eid in target_eids}
    target_prefix={}
    for eid,(iat,_uid) in targets.items():
        idx=bisect.bisect_right(person_offsets,iat)-1
        if idx<0:continue
        pat=person_offsets[idx]
        if iat-pat<=650:target_prefix[eid]=pat
    # Resolve only the few hundred string IDs the Championship squad actually uses.
    first_ids=set();sur_ids=set();common_ids=set();details={}
    for eid,pat in target_prefix.items():
        first,sur,com,inline=_prefix_ids(db,pat);details[eid]=(first,sur,com,inline)
        first_ids.add(first);sur_ids.add(sur)
        if com!=0xFFFFFFFF:common_ids.add(com)
    fore=resolve_pool_ids(db,bounds[0],first_ids);sur=resolve_pool_ids(db,bounds[1],sur_ids);common=resolve_pool_ids(db,bounds[2],common_ids)
    ability=scan_target_abilities(db,person_offsets,set(target_prefix.values()))
    out={}
    for eid,pat in target_prefix.items():
        iat,uid=targets[eid];first,surname,com,inline=details[eid]
        if first not in fore or surname not in sur:continue
        first_text=fore[first]; surname_text=sur[surname]
        name=inline or f'{first_text} {surname_text}'
        cname=None if com==0xFFFFFFFF else common.get(com)
        positions=None;ca=pa=None
        if pat in ability:positions,ca,pa=ability[pat]
        person_obj=Person(eid,uid,pat,name,cname,first_text,surname_text,positions,ca,pa)
        person_obj.first_name=fore.get(first)
        person_obj.surname_name=sur.get(surname)
        person_obj.common_name_id=None if com==0xFFFFFFFF else com
        person_obj.first_name_id=first
        person_obj.surname_name_id=surname
        out[eid]=person_obj
    return out

def fantasy_position(positions:list[int]|None)->str:
    if not positions:return 'MID'
    gk=positions[0]
    d=max(positions[i] for i in DEF_SLOTS)
    m=max(positions[i] for i in MID_SLOTS)
    f=positions[FWD_SLOT]
    overall=max(gk,d,m,f)
    if gk==overall and gk>=15:return 'GK'
    # Keep a genuine natural midfield role over an equally-rated ST (e.g. Bowen).
    # Exact match-by-match position usage is not guessed until its FM marker is decoded.
    if m==overall and m>=15:return 'MID'
    if d==overall and d>=15:return 'DEF'
    if f==overall and f>=15:return 'FWD'
    if gk==overall:return 'GK'
    if m==overall:return 'MID'
    if d==overall:return 'DEF'
    return 'FWD'

def price_from_ca(pos:str,ca:int|None)->float:
    # Provisional only. The final launch price is assigned by reprice_players after role/depth/history are known.
    ca=ca or 100
    base={'GK':4.0,'DEF':4.0,'MID':4.5,'FWD':4.5}[pos]
    extra=max(0.0,(ca-110)/25.0)
    return round(max(base,min(10.0,base+extra))*2)/2


def _clamp(x:float,a:float=0.0,b:float=1.0)->float:return max(a,min(b,x))


def _fm_struct_date(v:int):
    try:
        year=int(v)>>16; doy=int(v)&0x1FF
        if year<1900 or year>2200 or doy<1 or doy>366:return None
        return dt.date(year,1,1)+dt.timedelta(days=doy-1)
    except Exception:return None


def _structural_availability_from_fs(players:list[dict[str,Any]],fixtures:list[dict[str,Any]]|None=None)->dict[str,Any]:
    """Read active availability from FM's dedicated manager members.

    This deliberately binds records by player EID. It does not infer an injury from missed
    matches, names, cards or nearby bytes. Unknown structure remains unknown.
    """
    fixtures=fixtures or []
    byid={int(p.get('pid') or p.get('id') or 0):p for p in players}
    out={'decoder':'structural-v2-fixture-floor','save_date':None,'injury_records':0,'injured_players':0,
         'suspension_records':0,'suspended_players':0,'injury_source':'injury_manager.dat',
         'suspension_source':'discipline.dat'}
    save_date=None
    # Dates inside injury_manager.dat describe injury windows, not necessarily the current
    # save date. The latest played league fixture is a hard lower bound for the save timeline.
    # Never allow an older injury-table date to move the availability clock backwards.
    fixture_dates=[]
    for f in fixtures:
        if f.get('status')!='played' or not f.get('date'):continue
        try:fixture_dates.append(dt.date.fromisoformat(str(f['date'])[:10]))
        except Exception:pass
    fixture_floor=max(fixture_dates) if fixture_dates else None

    ip=Path('/tmp/injury_manager.dat')
    if ip.exists():
        try:
            b=ip.read_bytes();ip.unlink(missing_ok=True)
            c1=u32(b,12);s1=16;e1=s1+c1*14
            if 0<c1<2_000_000 and e1+4<=len(b):
                c2=u32(b,e1);s2=e1+4;e2=s2+c2*14
                if 0<=c2<2_000_000 and e2+4<=len(b):
                    c3=u32(b,e2);s3=e2+4;e3=s3+c3*13
                    if 0<=c3<2_000_000 and e3+4<=len(b):
                        c4=u32(b,e3);s4=e3+4;e4=s4+c4*15
                        if 0<=c4<5_000_000 and e4<=len(b):
                            past=[];future=[]
                            for i in range(c4):
                                d=_fm_struct_date(u32(b,s4+i*15+1))
                                if d:past.append(d)
                            for i in range(c1):
                                d=_fm_struct_date(u32(b,s1+i*14+1))
                                if d:future.append(d)
                            if past:save_date=max(past)
                            if save_date is None and future:save_date=min(future)
                            if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor
                            seen=set();recs=0
                            for i in range(c2):
                                o=s2+i*14
                                earliest=_fm_struct_date(u32(b,o+1));full=_fm_struct_date(u32(b,o+5));eid=u32(b,o+9)
                                if not full or not save_date or full<=save_date:continue
                                p=byid.get(int(eid))
                                if not p:continue
                                days=max(0,(full-save_date).days)
                                p['injury_status']='injured';p['injured']=True
                                p['injury_type']=p.get('injury_type') or 'Injury'
                                p['expected_return_date']=full.isoformat();p['injury_return_date']=full.isoformat();p['injured_until']=full.isoformat()
                                p['injury_days_remaining']=days
                                p['injury_evidence']={'source':'injury_manager.dat/current-window-v1','earliest_return':earliest.isoformat() if earliest else None,'expected_return':full.isoformat(),'days_remaining':days}
                                seen.add(int(eid));recs+=1
                            out['injury_records']=recs;out['injured_players']=len(seen)
        except Exception as e:out['injury_error']=str(e)[:220]

    if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor
    out['save_date']=save_date.isoformat() if save_date else None

    dp=Path('/tmp/discipline.dat')
    if dp.exists():
        try:
            b=dp.read_bytes();dp.unlink(missing_ok=True);count=u32(b,12) if len(b)>=16 else 0
            # FM26 active discipline rows have a stable entity prefix but a 59/60-byte variant,
            # so locate starts structurally rather than stepping a guessed row size.
            starts=[];pos=16
            while pos+20<=len(b) and len(starts)<count:
                found=-1
                for q in range(pos,min(len(b)-20,pos+96)):
                    if b[q]==0 and q+13<len(b) and b[q+7:q+13]==b'\x02\x00\xff\xff\x06\x01':found=q;break
                if found<0:break
                starts.append(found);pos=found+1
            seen=set();recs=0
            for s in starts:
                eid=u32(b,s+1);expiry=_fm_struct_date(u32(b,s+14));p=byid.get(int(eid))
                if not p or not expiry or (save_date and expiry<=save_date):continue
                # A row in discipline.dat is itself evidence of an active FM ban.
                # Count unplayed league fixtures through the expiry date where possible,
                # including a same-day fixture when the save was taken before kick-off.
                games=1
                if save_date and p.get('club'):
                    upcoming=set()
                    for f in fixtures:
                        try:fd=dt.date.fromisoformat(str(f.get('date') or '')[:10])
                        except Exception:continue
                        if fd<save_date or fd>expiry:continue
                        if f.get('status')=='played':continue
                        if p.get('club') in (f.get('home'),f.get('away')):upcoming.add(fd)
                    if upcoming:games=max(1,len(upcoming))
                p['suspension_status']='suspended';p['suspended']=True;p['banned_until']=expiry.isoformat()
                p['suspension_games_remaining']=games;p['suspension_remaining']=games;p['ban_games_remaining']=games
                p['suspension_detail']='Active FM suspension'
                p['suspension_evidence_structural']={'source':'discipline.dat/active-ban-v1','expiry':expiry.isoformat(),'games_remaining':games}
                seen.add(int(eid));recs+=1
            out['suspension_records']=recs;out['suspended_players']=len(seen)
        except Exception as e:out['suspension_error']=str(e)[:220]
    return out

def _role_profile(p:dict[str,Any])->tuple[str,float]:
    ps=p.get('positions') or {}
    v=lambda k:float(ps.get(k,0) or 0)
    pos=p.get('pos')
    if pos=='GK':return 'Goalkeeper',0.0
    if pos=='DEF':
        wing=max(v('DL'),v('DR'),v('WBL'),v('WBR'))/20.0
        midfield_wide=max(v('ML'),v('MR'),v('AML'),v('AMR'))/20.0
        cb=v('DC')/20.0
        attack=_clamp(0.08+0.38*wing+0.20*midfield_wide)
        label='Wide DEF/MID hybrid' if midfield_wide>=0.75 else ('Attacking full-back / wing-back' if wing>=0.75 and wing>=cb else 'Centre-back / defensive defender')
        return label,attack
    if pos=='FWD':return 'Forward',0.98
    attacking=max(v('AML'),v('AMC'),v('AMR'),v('ST'))/20.0
    wide=max(v('ML'),v('MR'))/20.0
    central=v('MC')/20.0; defensive=v('DM')/20.0
    attack=_clamp(max(attacking,0.72*wide,0.40*central))
    if defensive>=0.75 and attacking<0.60 and wide<0.70:
        attack=min(attack,0.28);return 'Defensive midfielder',attack
    if attacking>=0.75:return 'Attacking midfielder / winger',attack
    if wide>=0.70:return 'Wide midfielder',attack
    return 'Central midfielder',max(0.30,attack)



def reprice_players(players:list[dict[str,Any]], fixtures:list[dict[str,Any]]|None=None)->None:
    """FPL-shaped v6.5 role-projection launch pricing.

    Launch prices are set once at Season / Database Import.  Later Gameweek imports do
    not re-run this model as the market price; the browser applies small, sustained-form
    changes from the launch value.  This model therefore focuses on the player's value
    *at the import date*: quality, role, actual availability, depth and team strength.
    """
    if not players:return
    fixtures=fixtures or []
    bypos=collections.defaultdict(list)
    for p in players:bypos[p['pos']].append(p)
    pct={}
    for pos,arr in bypos.items():
        vals=sorted(float(p.get('ca') or 100) for p in arr)
        for p in arr:
            ca=float(p.get('ca') or 100);rank=bisect.bisect_right(vals,ca)-1;rel=rank/max(1,len(vals)-1)
            absolute=_clamp((ca-100.0)/80.0)
            pct[p['id']]=0.40*rel+0.60*absolute

    club_quality_raw={}
    for club in {p['club'] for p in players}:
        vals=sorted((float(p.get('ca') or 90) for p in players if p['club']==club),reverse=True)[:16]
        club_quality_raw[club]=sum(vals)/max(1,len(vals))
    qvals=sorted(club_quality_raw.values())
    club_quality={c:(bisect.bisect_right(qvals,v)-1)/max(1,len(qvals)-1) for c,v in club_quality_raw.items()}

    perf=collections.defaultdict(lambda:{'p':0,'pts':0,'gd':0,'dates':[]})
    for f in fixtures:
        if f.get('status')!='played':continue
        h,a=f.get('home'),f.get('away');hs=int(f.get('home_score') or 0);as_=int(f.get('away_score') or 0);date=f.get('date')
        if not h or not a:continue
        for c in (h,a):
            perf[c]['p']+=1
            if date:perf[c]['dates'].append(date)
        perf[h]['gd']+=hs-as_;perf[a]['gd']+=as_-hs
        if hs>as_:perf[h]['pts']+=3
        elif hs<as_:perf[a]['pts']+=3
        else:perf[h]['pts']+=1;perf[a]['pts']+=1

    club_strength={}
    for c in club_quality:
        d0=perf[c]
        if d0['p']>=3:
            ppg=d0['pts']/(3*d0['p']);gdpg=d0['gd']/d0['p'];live=_clamp(0.74*ppg+0.26*((gdpg+2.0)/4.0))
            live_weight=0.64 if d0['p']>=5 else 0.48
            club_strength[c]=(1-live_weight)*club_quality[c]+live_weight*live
        else:club_strength[c]=club_quality[c]

    club_matches={c:int(perf[c]['p']) for c in club_quality}
    # Some FM saves expose league results but no retained player-match detail. In that case
    # '0 minutes' means unknown coverage, not a genuine unused reserve. Never collapse an
    # entire league to basement prices because match-detail coverage is absent.
    club_usage_coverage={c:any(float(p.get('minutes') or 0)>0 or bool(p.get('history')) for p in players if p.get('club')==c) for c in club_quality}
    groups=collections.defaultdict(list)
    for p in players:groups[(p['club'],p['pos'])].append(p)
    depth={};group_active={};usage_rank={}
    for (club,pos),arr in groups.items():
        ability_order=sorted(arr,key=lambda p:(float(p.get('ca') or 0),float(p.get('pa') or 0)),reverse=True)
        used_order=sorted(arr,key=lambda p:(float(p.get('minutes') or 0),float(p.get('starts') or 0),float(p.get('ca') or 0)),reverse=True)
        group_active[(club,pos)]=used_order[0] if used_order else None
        usage_rank.update({p['id']:i for i,p in enumerate(used_order)})
        for i,p in enumerate(ability_order):
            if pos=='GK':d=[1.0,0.35,0.07][min(i,2)] if i<3 else 0.03
            elif pos=='FWD':d=max(0.18,1.0-0.24*i)
            elif pos=='DEF':d=max(0.28,1.0-0.12*i)
            else:d=max(0.25,1.0-0.12*i)
            depth[p['id']]=d

    raw_scores={}
    for p in players:
        q=_clamp(pct.get(p['id'],0.35));role,attack=_role_profile(p);club=p['club'];games=club_matches.get(club,0);d=depth.get(p['id'],0.5)
        mins=float(p.get('minutes',0) or 0);starts=float(p.get('starts',0) or 0);hist=p.get('history') or []
        # A recent signing should be judged on fixtures he could actually have played.
        first_dates=sorted(str(h.get('date')) for h in hist if h.get('date') and float(h.get('minutes') or 0)>0)
        first_play=first_dates[0] if first_dates else None
        club_dates=sorted(perf[club]['dates'])
        available_games=games;late_arrival=False
        if first_play and club_dates and first_play>club_dates[0]:
            after=sum(1 for x in club_dates if x>=first_play)
            # Only use the late-arrival window when the player has clearly participated
            # in it; this stops pre-transfer league matches making a new signing look unused.
            if after and len(first_dates)>=min(1,after):
                available_games=max(1,after);late_arrival=(available_games<games)
        share=_clamp(mins/(90.0*available_games)) if available_games else 0.0
        start_share=_clamp(starts/available_games) if available_games else 0.0
        active=group_active.get((club,p['pos']));ca=float(p.get('ca') or 100);active_ca=float(active.get('ca') or 100) if active else ca
        _status_text=' '.join(str(p.get(k) or '').lower() for k in ('injury_status','suspension_status','status'))
        current_unavailable=bool(p.get('injured') or p.get('suspended') or 'injur' in _status_text or 'suspend' in _status_text or p.get('injury_return_date') or p.get('injury_evidence'))
        # Missing games are excused only for a ZERO-MINUTE player who has real senior-role
        # evidence. This prevents a low-CA injured reserve being treated as a nailed starter.
        established_absence=bool(current_unavailable and mins<=0 and (q>=0.55 or d>=0.55 or ca>=130))
        absence_excused=established_absence
        expected_exception=established_absence
        if available_games>=1 and club_usage_coverage.get(club,False):
            actual_role=_clamp(0.66*share+0.34*start_share)
            nailed=_clamp(0.86*actual_role+0.14*d)
            if expected_exception:nailed=max(0.68,d*0.80)
        else:nailed=d
        team=_clamp(club_strength.get(club,0.5));pos=p['pos']

        # Add real attacking output to the positional-role estimate without letting a tiny
        # sample dominate.  This separates an attacking wing-back/creator from a CB/DM.
        ga=float(p.get('goals',0) or 0)+float(p.get('assists',0) or 0)
        ga90=(ga*90.0/mins) if mins>=90 else 0.0
        output_weight=_clamp(mins/720.0,0.0,0.42)
        observed_attack=_clamp(ga90/0.62)
        attack=_clamp((1-output_weight)*attack+output_weight*observed_attack)

        if games>=2 and mins==0 and not expected_exception and club_usage_coverage.get(club,False):
            raw=min(4.5,3.5+0.42*q+0.20*d);availability='No minutes · basement price'
        else:
            availability=('Recent arrival · judged since first appearance' if late_arrival else
                          ('Expected role exception' if expected_exception else ('Observed role' if games>=2 and club_usage_coverage.get(club,False) else ('Squad-role projection · player match detail unavailable' if games>=2 else 'Pre-season projection'))))
            if pos=='GK':
                raw=3.70+0.30*q+0.78*nailed+0.82*team;raw=min(5.5,raw)
            elif pos=='DEF':
                # Team quality matters, but attacking threat is required for true premium territory.
                raw=3.60+0.48*q+0.92*nailed+0.78*attack+1.42*team+0.18*(q**4)
            elif pos=='MID' and attack<0.34:
                raw=4.10+0.48*q+1.00*nailed+0.26*attack+0.72*team+0.12*(q**3);raw=min(6.8,raw)
            elif pos=='MID':
                raw=4.10+0.72*q+1.18*nailed+1.70*attack+0.82*team+4.15*(q**4)*(0.30+0.70*nailed)*(0.40+0.60*attack)
                if q>=0.94 and nailed>=0.82 and attack>=0.72 and team>=0.65:raw+=0.8
                raw=min(15.0,raw)
            else:
                raw=4.10+0.76*q+1.28*nailed+1.22*attack+0.92*team+3.85*(q**4)*(0.24+0.76*nailed)
                if q>=0.95 and nailed>=0.82 and team>=0.58:raw+=0.6
                raw=min(14.5,raw)

        # Usage beats reputation once there is evidence, but use AVAILABLE games rather
        # than all club games so a newly-signed starter is not labelled a backup.
        if available_games>=3 and club_usage_coverage.get(club,False) and not expected_exception:
            if share<0.15:
                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos]);availability='Rarely used backup'
            elif share<0.35:
                raw=min(raw,{'GK':4.5,'DEF':5.0,'MID':5.2,'FWD':5.5}[pos]);availability='Backup / rotation'
            elif share<0.55:
                raw-=0.35;availability='Rotation / partial starter'

        # League position/performance should materially separate equivalent players.
        if games>=3:
            if pos=='FWD':
                if team<0.28:raw=min(raw,6.0)
                elif team<0.45:raw=min(raw,6.5)
                elif team<0.58:raw=min(raw,7.0)
            elif pos=='DEF':
                if team<0.28:raw=min(raw,4.7)
                elif team<0.42:raw=min(raw,5.2)
            elif pos=='MID' and attack<0.45 and team<0.45:raw=min(raw,5.5)

        raw_scores[p['id']]=raw
        p['price_context']={'quality':round(q,3),'nailedness':round(nailed,3),'minutes_share':round(share,3),
                            'start_share':round(start_share,3),'usage_rank':usage_rank.get(p['id'],0)+1,'role':role,
                            'attack_profile':round(attack,3),'depth_score':round(d,3),'team_strength':round(team,3),
                            'observed_matches':games,'available_matches':available_games,'late_arrival':late_arrival,
                            'first_appearance_date':first_play,'availability_signal':availability,
                            'zero_minute_exception':expected_exception,'ga_per90':round(ga90,3)}

    # v6.1: the raw FM-derived model decides ordering; positional rank then controls
    # the shape of the market. Premium prices are deliberately scarce and the middle/
    # value tiers step down rather than bunching at one high cap.
    ranked={pos:sorted((p for p in players if p['pos']==pos),key=lambda p:raw_scores[p['id']],reverse=True) for pos in ('GK','DEF','MID','FWD')}
    for pos,arr in ranked.items():
        for i,p in enumerate(arr):
            raw=raw_scores[p['id']];c=p['price_context'];att=float(c['attack_profile']);team=float(c['team_strength']);nailed=float(c['nailedness']);q=float(c['quality'])
            c['position_price_rank']=i+1
            if p.get('minutes',0)==0 and c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and not c['zero_minute_exception']:
                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos])
            elif p.get('minutes',0)==0 and c['zero_minute_exception']:
                _floor={'GK':4.5,'DEF':5.0,'MID':5.5,'FWD':6.0}[pos]
                _cap={'GK':5.0,'DEF':5.5,'MID':7.0,'FWD':7.5}[pos]
                raw=max(_floor,min(raw,_cap))
            elif pos=='GK':
                # Two genuine premium keepers, a small £5.0m tier, then normal £4.5m territory.
                cap=5.5 if i<2 else 5.0 if i<8 else 4.5
                raw=min(raw,cap)
            elif pos=='DEF':
                # £6.0m+ is premium. After the premium group, force distinct £5.5/£5.0/£4.5
                # ceilings so a strong league cannot turn most starting defenders expensive.
                if att<0.42:
                    if i<3 and team>=0.78 and nailed>=0.84:cap=6.0
                    elif i<18:cap=5.5
                    elif i<60:cap=5.0
                    else:cap=4.5
                    raw=min(raw,cap)
                elif i==0 and team>=0.70 and att>=0.58:
                    raw=min(7.5,raw+0.35)
                elif i<3 and team>=0.58:
                    raw=min(raw,6.5)
                elif i<6:
                    raw=min(raw,6.0)
                elif i<18:
                    raw=min(raw,5.5)
                elif i<60:
                    raw=min(raw,5.0)
                else:
                    raw=min(raw,4.5)
            elif pos=='MID':
                if att<0.34:
                    # Defensive midfielders are priced for fantasy role, not reputation.
                    if i<8 and q>=0.88 and team>=0.62 and nailed>=0.80:cap=6.0
                    elif i<45:cap=5.5
                    else:cap=5.0
                    raw=min(raw,cap)
                else:
                    cap=(15.0 if i<2 else 12.5 if i<5 else 10.5 if i<10 else 9.0 if i<20
                         else 8.0 if i<40 else 7.0 if i<80 else 6.5 if i<140 else 6.0)
                    raw=min(raw,cap)
            else: # FWD
                cap=(14.0 if i<2 else 11.5 if i<5 else 9.5 if i<10 else 8.0 if i<20
                     else 7.5 if i<40 else 7.0 if i<80 else 6.5)
                raw=min(raw,cap)
            obs=max(0,int(c.get('observed_matches') or 0))
            arrival=None
            for _k in ('club_join_date','joined_date','date_joined','transfer_date','arrival_date','signed_date'):
                _v=p.get(_k)
                if not _v:continue
                try:arrival=dt.date.fromisoformat(str(_v)[:10]);break
                except Exception:pass
            if arrival and p.get('club'):
                eligible=set()
                for _f in fixtures:
                    if _f.get('status')!='played' or p.get('club') not in (_f.get('home'),_f.get('away')):continue
                    try:_fd=dt.date.fromisoformat(str(_f.get('date') or '')[:10])
                    except Exception:continue
                    if _fd>=arrival:eligible.add(_fd)
                obs=len(eligible)
                c['current_club_observed_matches']=obs
                c['arrival_date']=arrival.isoformat()
                c['new_arrival']=obs<2
            else:
                c['new_arrival']=False
            mins=max(0.0,float(p.get('minutes') or 0))
            minute_share=min(1.0,mins/max(1.0,obs*90.0)) if obs else 0.0
            _status_text=' '.join(str(p.get(k) or '').lower() for k in ('injury_status','suspension_status','status'))
            current_unavailable=bool(p.get('injured') or p.get('suspended') or 'injur' in _status_text or 'suspend' in _status_text or p.get('injury_return_date') or p.get('injury_evidence'))
            q0=float(c.get('quality') or 0);d0=float(c.get('depth_score') or 0);ca0=float(p.get('ca') or 0)
            absence_excused=bool(current_unavailable and mins<=0 and (q0>=0.55 or d0>=0.55 or ca0>=130))
            c['current_unavailable']=current_unavailable
            c['established_absence']=absence_excused
            c['observed_minute_share']=round(minute_share,3)
            if obs>=2 and not absence_excused:
                if minute_share<0.20:
                    role='backup';role_floor={'GK':4.0,'DEF':4.0,'MID':4.5,'FWD':4.5}[pos];role_cap={'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos]
                elif minute_share<0.45:
                    role='rotation';role_floor={'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos];role_cap={'GK':4.5,'DEF':4.5,'MID':5.0,'FWD':6.0}[pos]
                elif minute_share<0.70:
                    role='squad';role_floor={'GK':4.5,'DEF':4.5,'MID':5.0,'FWD':5.5}[pos];role_cap={'GK':5.0,'DEF':5.0,'MID':6.0,'FWD':7.0}[pos]
                else:
                    role='starter';role_floor={'GK':4.5,'DEF':5.0,'MID':5.5,'FWD':6.0}[pos];role_cap={'GK':6.0,'DEF':8.0,'MID':15.0,'FWD':14.0}[pos]
                raw=max(role_floor,min(raw,role_cap))
                c['usage_role']=role;c['usage_role_floor']=role_floor;c['usage_role_cap']=role_cap
            elif c.get('new_arrival'):
                c['usage_role']='new_arrival_unproven'
            elif absence_excused:
                c['usage_role']='absence_excused'
            else:
                c['usage_role']='unproven'
            raw_scores[p['id']]=raw
            c['distribution_cap']=round(raw,2)

    for p in players:
        c=p['price_context'];basement=(c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and float(p.get('minutes',0) or 0)==0 and not c['zero_minute_exception'])
        base=3.5 if basement else {'GK':4.0,'DEF':4.0,'MID':4.5,'FWD':4.5}[p['pos']]
        price=round(max(base,raw_scores[p['id']])*2)/2
        if basement:price=min(4.5,price)
        p['price']=price;c['price']=price
        c['summary']=(f"{c['role']} · available-minute share {round(c['minutes_share']*100)}% · starts {round(c['start_share']*100)}% · "
                      f"attack {round(c['attack_profile']*100)}/100 · team strength {round(c['team_strength']*100)}/100 · "
                      f"quality {round(c['quality']*100)}/100 · {c['availability_signal']}")


    # v6.5 final launch-price guardrails. Earlier stages build the market shape, but these
    # two cases must never be flattened into ordinary zero-minute backups:
    #   1) established senior players currently unavailable through injury/suspension;
    #   2) strong recent arrivals with too little eligible-club evidence to judge by minutes.
    # This is generic evidence-based logic: no player names or club-specific exceptions.
    _starter_price={}
    for _p in players:
        _c=_p.get('price_context') or {}
        _key=(_p.get('club'),_p.get('pos'))
        if (float(_p.get('minutes') or 0)>=120 and int(_p.get('starts') or 0)>=2) or _c.get('usage_role')=='starter':
            _starter_price[_key]=max(float(_starter_price.get(_key,0) or 0),float(_p.get('price') or 0))

    for _p in players:
        _c=_p.get('price_context') or {};_pos=_p.get('pos')
        if _pos not in ('GK','DEF','MID','FWD'):continue
        _price=float(_p.get('price') or 0);_q=float(_c.get('quality') or 0);_d=float(_c.get('depth_score') or 0);_ca=float(_p.get('ca') or 0)
        _mins=float(_p.get('minutes') or 0);_apps=int(_p.get('apps') or 0)
        _st=' '.join(str(_p.get(k) or '').lower() for k in ('injury_status','suspension_status','status'))
        _unavailable=bool(_p.get('injured') or _p.get('suspended') or 'injur' in _st or 'suspend' in _st or _p.get('return_date') or _p.get('injury_return_date') or _p.get('injury_evidence'))

        # An unavailable established senior option keeps a sensible FPL-like launch floor.
        # Ability/depth only proves they belong in the senior pricing band; it does not make
        # an absent player premium by itself.
        if _mins<=0 and _unavailable and (_q>=0.55 or _d>=0.55 or _ca>=130):
            _floor={'GK':4.5,'DEF':5.0,'MID':5.5,'FWD':6.0}[_pos]
            if _q>=0.80 and _d>=0.70:_floor+=0.5
            _price=max(_price,_floor)
            _c['usage_role']='established_absence'
            _c['availability_signal']='Established senior role · currently unavailable'
            _c['pricing_guardrail']='v65_established_absence'

        # A genuine recent arrival cannot be labelled a £4.5/£5.0 backup from one cameo.
        # Project from quality + depth until there are at least two eligible current-club
        # matches. Keep the projection below a proven starter in the same club/position.
        _avail=int(_c.get('available_matches') or 0);_late=bool(_c.get('late_arrival'))
        if _late and _avail<=1 and _apps<=1 and _q>=0.60 and _d>=0.45:
            if _pos=='GK':_proj=4.0+0.60*_q+0.40*_d
            elif _pos=='DEF':_proj=4.5+0.80*_q+0.50*_d
            elif _pos=='MID':_proj=5.0+1.30*_q+0.60*_d
            else:_proj=5.5+1.40*_q+0.70*_d
            _ahead=float(_starter_price.get((_p.get('club'),_pos),0) or 0)
            if _ahead>0:_proj=min(_proj,max({'GK':4.5,'DEF':5.0,'MID':5.5,'FWD':6.0}[_pos],_ahead-0.5))
            _proj=round(_proj*2)/2
            _price=max(_price,_proj)
            _c['usage_role']='new_arrival_projected'
            _c['availability_signal']='Recent arrival · projected from quality and squad role'
            _c['pricing_guardrail']='v65_new_arrival_projection'
            _c['projected_arrival_price']=_proj

        _p['price']=round(_price*2)/2;_c['price']=_p['price']
        _c['summary']=(f"{_c.get('role','Player')} · available-minute share {round(float(_c.get('minutes_share') or 0)*100)}% · "
                       f"starts {round(float(_c.get('start_share') or 0)*100)}% · attack {round(float(_c.get('attack_profile') or 0)*100)}/100 · "
                       f"team strength {round(float(_c.get('team_strength') or 0)*100)}/100 · quality {round(_q*100)}/100 · {_c.get('availability_signal','')}")

def scan_completed_results(db:bytes,fixtures:list[dict[str,Any]]):
    keys={(r['home_tid'],r['away_tid'],r['date']):r for r in fixtures}
    teams=sorted({x for r in fixtures for x in (r['home_tid'],r['away_tid'])})
    pat=re.compile(b'|'.join(re.escape(struct.pack('<I',x)) for x in teams))
    found={}
    for m in pat.finditer(db):
        p=m.start()
        if p+86>len(db):continue
        home=u32(db,p); away=u32(db,p+4)
        if away not in teams:continue
        stamp=u16(db,p+8);year=u16(db,p+10);doy=stamp&0x1ff
        if not (1<=doy<=366 and 2024<=year<=2045):continue
        date=fm_date(stamp,year)
        key=(home,away,date)
        if key not in keys:continue
        hs,as_=db[p+84],db[p+85]
        if hs>30 or as_>30:continue
        found[key]=(hs,as_,p)
    # one result per completed fixture; 50 in current regression save
    for key,(hs,as_,p) in found.items():
        f=keys[key];f['status']='played';f['home_score']=hs;f['away_score']=as_;f['result_offset']=p
    return found


def _rich_read_lp_utf8(buf:bytes,pos:int,max_len:int=80):
    if pos+4>len(buf): return None,pos
    n=u32(buf,pos)
    if n>max_len or pos+4+n>len(buf): return None,pos
    raw=buf[pos+4:pos+4+n]
    try:s=raw.decode('utf-8')
    except UnicodeDecodeError:return None,pos
    if any(ord(c)<32 for c in s):return None,pos
    return s,pos+4+n


def _rich_stat_record_at(buf:bytes,p:int):
    if p+214>len(buf) or buf[p]!=2:return None
    c=buf[p:p+214];rating=u16(c,136)
    if not (1<=c[5]<=99 and c[7]==2 and c[20]<=12 and c[21]<=20 and c[50]<=30 and c[51]<=30 and c[52]<=30 and c[56]<=12 and c[63]<=5 and c[64]<=2 and c[67]<=130 and c[71]<=130 and 400<=rating<=1000):
        return None
    out={
        'player_id':u32(c,1),'shirt':c[5],'goals':c[20],
        'goalkeeper_goals_conceded_from_sot':c[21],'penalties_taken':c[22],
        'penalties_scored':c[23],'own_goals':c[24],
        'shots_on_target':c[42],'shots_blocked':c[43],
        'save_component_1':c[50],'save_component_2':c[51],'save_component_3':c[52],
        'save_component_legacy_1':c[50],'save_component_legacy_2':c[51],'save_component_legacy_3':c[52],
        'blocks':c[55],'assists':c[56],
        'yellow_cards':c[63],'red_cards':c[64],'sub_off':c[67],'sub_on':c[71],
        'sent_off_minute':c[74],'match_position_marker':c[77],
        'passes_attempted':c[86],'passes_completed':c[87],
        'tackles_attempted':c[92],'tackles_won':c[93],'key_tackles_candidate':c[94],
        'headers_attempted':c[95],'headers_won':c[96],
        'interceptions_candidate':c[97],'clearances_candidate':c[98],
        'team_goals_while_on_pitch':c[145],'team_goals_conceded_while_on_pitch':c[146],
        'possession_won_candidate':c[151],'possession_lost_candidate':c[152],
        'shots_on_target_faced':c[157],
        'rating_raw':rating,'rating':round(rating/100,1),'offset':p,
    }
    out['saves']=max(0,out['shots_on_target_faced']-out['goalkeeper_goals_conceded_from_sot'])
    out['penalties_missed']=max(0,out['penalties_taken']-out['penalties_scored'])
    out['is_goalkeeper_match_role']=out['match_position_marker']==4
    out['goals_conceded']=out['team_goals_conceded_while_on_pitch']
    out['cbit_candidate']=out['blocks']+out['tackles_won']+out['interceptions_candidate']+out['clearances_candidate']
    out['mapping_confidence']={
        'blocks':'exact-mirror','tackles_won':'strong-pair-and-ui-check',
        'interceptions_candidate':'working-high','clearances_candidate':'working-high',
        'possession_won_candidate':'working-high',
    }
    return out


def _rich_scan_stats(buf:bytes,start:int,end:int):
    out=[];p=start
    while p<end-214:
        if buf[p]==2:
            r=_rich_stat_record_at(buf,p)
            if r:
                out.append(r);p+=140;continue
        p+=1
    return out


def _rich_pick_two_squads(stats:list[dict[str,Any]]):
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

def _rich_decorate(rows:list[dict[str,Any]]):
    result=[]
    for idx,r0 in enumerate(rows):
        r=dict(r0);starter=idx<11
        if starter:
            r['appearance']='Started'
            if r['sub_off']:
                r['minutes']=r['sub_off'];r['appearance']+=f", off {r['sub_off']}'"
            elif r['red_cards'] and r['sent_off_minute']:
                r['minutes']=r['sent_off_minute'];r['appearance']+=f", sent off {r['sent_off_minute']}'"
            else:r['minutes']=90
        else:
            if r['sub_on']:
                r['appearance']=f"On {r['sub_on']}'";r['minutes']=max(0,90-r['sub_on'])
            else:
                r['appearance']='Unused';r['minutes']=0;r['rating']=None
        result.append(r)
    return result



def _rich_header(buf:bytes,comp_pos:int,rich_team_names:dict[int,str],competition_text:bytes):
    p=comp_pos+len(competition_text)
    short,p2=_rich_read_lp_utf8(buf,p,80)
    # FM stores a second competition label immediately after the long label. Accept the
    # label generically; team identity and league fixture matching provide the validation.
    if not short:return None
    stadium=None;stadium_end=None
    for q in range(p2,min(p2+120,len(buf)-8)):
        text,nxt=_rich_read_lp_utf8(buf,q,80)
        if text and len(text)>=3 and nxt+12<len(buf) and buf[nxt:nxt+2]==b'\x03\x02':
            stadium=text;stadium_end=nxt;break
    if not stadium:return None
    q=stadium_end
    if buf[q:q+2]!=b'\x03\x02' or buf[q+6]!=2:return None
    home_tid=u32(buf,q+7)
    marker=buf.find(b'\x00\x03\x02',q+11,q+70)
    if marker<0 or buf[marker+7]!=2:return None
    away_tid=u32(buf,marker+8)
    home=rich_team_names.get(home_tid);away=rich_team_names.get(away_tid)
    if not home or not away:return None
    return {'stadium':stadium,'home':home,'away':away,'home_tid':home_tid,'away_tid':away_tid,'competition_short':short}


def _rich_extract_member(buf:bytes,rich_team_names:dict[int,str],source_member:str):
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

def rich_extract_named(save_path:Path,all_clubs:dict[int,Club])->list[dict[str,Any]]:
    # Rich match copies live across labelled save members (news, play-fixture manager,
    # and transient APM/SCM snapshots). Scan members one-at-a-time so the importer
    # never needs the legacy ~500 MB whole-save decompression.
    rich_team_names={c.uid+1:normalize_club_name(c.short or c.name) for c in all_clubs.values()}
    _save,items=read_manifest(save_path)
    raw=[]
    for member in items:
        if member.plain_len<=0 or member.plain_len>30_000_000:continue
        buf=extract_member(save_path,member)
        if b'Sky Bet Championship' not in buf:continue
        raw.extend(_rich_extract_member(buf,rich_team_names,member.name))
    ded=[];seen=set()
    for m in raw:
        key=(m['home'],m['away'],m['home_score'],m['away_score'],
             tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))
        if key in seen:continue
        seen.add(key);ded.append(m)
    return ded

def normalize_club_name(name:str)->str:
    repl={'West Ham United':'West Ham Utd','Queens Park Rangers':'QPR','Sheffield United':'Sheffield Utd','West Bromwich Albion':'West Brom'}
    return repl.get(name,name)


def score_player(row:dict[str,Any],pos:str)->dict[str,Any]:
    mins=row.get('minutes',0) or 0
    app=2 if mins>=60 else 1 if mins>0 else 0
    goals=row.get('goals',0) or 0; assists=row.get('assists',0) or 0
    goal_pts=goals*({'GK':10,'DEF':6,'MID':5,'FWD':4}[pos])
    assist_pts=assists*3
    gc=row.get('team_goals_conceded_while_on_pitch',row.get('goals_conceded',0)) or 0
    cs=0
    if mins>=60 and gc==0: cs={'GK':4,'DEF':4,'MID':1,'FWD':0}[pos]
    saves=row.get('saves',0) or 0
    save_pts=(saves//3) if pos=='GK' else 0
    gc_pts=-(gc//2) if pos in ('GK','DEF') and mins>0 else 0
    reds=(row.get('red_cards',0) or 0); yellows=(row.get('yellow_cards',0) or 0); card_pts=(-3*reds) if reds else (-yellows)
    pen_pts=-2*(row.get('penalties_missed',0) or 0)
    og_pts=-2*(row.get('own_goals',0) or 0)
    cbit=(row.get('blocks',0) or 0)+(row.get('tackles_won',0) or 0)+(row.get('interceptions_candidate',0) or 0)+(row.get('clearances_candidate',0) or 0)
    recovery=row.get('possession_won_candidate',0) or 0
    def_actions=cbit if pos=='DEF' else cbit+recovery
    threshold=10 if pos=='DEF' else 12
    def_pts=2 if pos!='GK' and def_actions>=threshold else 0
    base=app+goal_pts+assist_pts+cs+save_pts+gc_pts+card_pts+pen_pts+og_pts+def_pts
    # Transparent FM-derived BPS proxy: rank only; not claimed as official FPL BPS.
    rating=float(row.get('rating') or 0)
    proxy=round(rating*10 + goals*18 + assists*9 + cs*4 + saves*2 + def_actions*0.5 + base,1) if mins else 0.0
    return {'appearance_pts':app,'goal_pts':goal_pts,'assist_pts':assist_pts,'clean_sheet_pts':cs,'save_pts':save_pts,'gc_pts':gc_pts,'card_pts':card_pts+pen_pts+og_pts,'defcon_actions':def_actions,'defcon_pts':def_pts,'base_points':base,'bps_proxy':proxy}


def award_bonus(players:list[dict[str,Any]]):
    active=[p for p in players if p.get('minutes',0)>0]
    active.sort(key=lambda x:(x['bps_proxy'],x.get('rating') or 0,x.get('goals',0),x.get('assists',0)),reverse=True)
    # Simple 3/2/1 proxy ranking. Ties intentionally resolve deterministically rather than emulating official BPS tie rules.
    for p in players:p['bonus']=0
    for pts,p in zip((3,2,1),active[:3]):p['bonus']=pts
    for p in players:p['fpl_points']=p['base_points']+p['bonus']



def _position_strengths(p:dict[str,Any]):
    ps=p.get('positions') or {};v=lambda k:float(ps.get(k,0) or 0)
    return {'GK':v('GK'),'DEF':max(v('SW'),v('DL'),v('DC'),v('DR'),v('WBL'),v('WBR')),
            'MID':max(v('DM'),v('ML'),v('MC'),v('MR'),v('AML'),v('AMC'),v('AMR')),'FWD':v('ST')}

def infer_hybrid_positions_from_match_markers(rich:list[dict[str,Any]],players_by_eid:dict[int,dict[str,Any]]):
    """Self-calibrate FM's retained match-position marker from unambiguous players.

    Marker 4 is already proven as goalkeeper. Other marker meanings can vary across
    retained objects, so never hard-code them: learn a marker->FPL band mapping only
    when the save itself gives a strong, repeated correlation. Then use that mapping
    solely to resolve genuine DEF/MID hybrids; ordinary positions are left untouched.
    """
    marker_counts=collections.defaultdict(collections.Counter)
    for m in rich:
        for key in ('home_players','away_players'):
            for r in m.get(key,[]):
                p=players_by_eid.get(int(r.get('player_id') or 0));marker=int(r.get('match_position_marker') or 0)
                if not p or not marker or marker==4 or float(r.get('minutes') or 0)<=0:continue
                strengths=_position_strengths(p);order=sorted(strengths.items(),key=lambda x:x[1],reverse=True)
                if order[0][1]<15 or order[0][1]-order[1][1]<3:continue
                marker_counts[marker][order[0][0]]+=1
    marker_roles={4:'GK'}
    for marker,c in marker_counts.items():
        total=sum(c.values())
        if total<8:continue
        role,n=c.most_common(1)[0]
        if n/total>=0.80:marker_roles[marker]=role
    usage=collections.defaultdict(collections.Counter)
    for m in rich:
        for key in ('home_players','away_players'):
            for r in m.get(key,[]):
                if float(r.get('minutes') or 0)<=0:continue
                role=marker_roles.get(int(r.get('match_position_marker') or 0))
                if role:usage[int(r.get('player_id') or 0)][role]+=1
    changed=[]
    for eid,c in usage.items():
        p=players_by_eid.get(eid)
        if not p:continue
        st=_position_strengths(p)
        # Only override genuine DEF/MID hybrids. A lineup slot is not strong enough
        # evidence to turn an otherwise unambiguous defender/midfielder/forward into
        # another FPL band. Both FM bands must be materially playable.
        if p.get('pos') not in ('DEF','MID') or min(st['DEF'],st['MID'])<14:continue
        dm=c['DEF']+c['MID']
        if dm<2:continue
        if c['MID']/dm>=0.80 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage_v64_marker';changed.append(eid)
        elif c['DEF']/dm>=0.80 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage_v64_marker';changed.append(eid)

    # FM's match-position marker is 0 for most outfield rows in some saves. The retained
    # player blocks still preserve tactical XI order: slot 1 is GK, 2-5 defence, 6-10
    # midfield/attack, 11 striker in the overwhelming majority of decoded matches. Learn
    # those slot roles from unambiguous players in THIS save, then apply only to genuine
    # DEF/MID hybrids with at least two starts in a strongly calibrated slot.
    slot_counts=collections.defaultdict(collections.Counter)
    for mm in rich:
        for key in ('home_players','away_players'):
            for idx,r in enumerate(mm.get(key,[])[:11],1):
                if float(r.get('minutes') or 0)<=0:continue
                p=players_by_eid.get(int(r.get('player_id') or 0))
                if not p:continue
                st=_position_strengths(p);order=sorted(st.items(),key=lambda x:x[1],reverse=True)
                if order[0][1]<15 or order[0][1]-order[1][1]<3:continue
                slot_counts[idx][order[0][0]]+=1
    slot_roles={}
    for idx,cnt in slot_counts.items():
        total=sum(cnt.values())
        if total<10:continue
        role,n=cnt.most_common(1)[0]
        if n/total>=0.75:slot_roles[idx]=role
    slot_usage=collections.defaultdict(collections.Counter)
    for mm in rich:
        for key in ('home_players','away_players'):
            for idx,r in enumerate(mm.get(key,[])[:11],1):
                role=slot_roles.get(idx)
                if role:slot_usage[int(r.get('player_id') or 0)][role]+=1
    for eid,c in slot_usage.items():
        p=players_by_eid.get(eid)
        if not p:continue
        st=_position_strengths(p)
        # Only override genuine DEF/MID hybrids. A lineup slot is not strong enough
        # evidence to turn an otherwise unambiguous defender/midfielder/forward into
        # another FPL band. Both FM bands must be materially playable.
        if p.get('pos') not in ('DEF','MID') or min(st['DEF'],st['MID'])<14:continue
        dm=c['DEF']+c['MID']
        if dm<2:continue
        if c['MID']/dm>=0.75 and p.get('pos')!='MID':
            p['pos']='MID';p['position_source']='observed_midfield_usage_v64_lineup_slot';p['observed_lineup_role_counts']=dict(c);changed.append(eid)
        elif c['DEF']/dm>=0.75 and p.get('pos')!='DEF':
            p['pos']='DEF';p['position_source']='observed_defensive_usage_v64_lineup_slot';p['observed_lineup_role_counts']=dict(c);changed.append(eid)
    return {'marker_roles':marker_roles,'slot_roles':slot_roles,'hybrid_players_reclassified':sorted(set(changed))}

def join_rich_matches(rich:list[dict[str,Any]],fixtures:list[dict[str,Any]],players_by_eid:dict[int,dict[str,Any]]):
    # Current fantasy positions and clubs come from current person/squad records only.
    by_pair=collections.defaultdict(list)
    for f in fixtures:
        if f['status']=='played':by_pair[(f['home'],f['away'])].append(f)

    def current_club(pid):
        p=players_by_eid.get(int(pid or 0))
        return normalize_club_name(p.get('club','')) if p else ''

    def validate_sides(home_rows,away_rows,home,away,fix,grounded=False):
        if not (11<=len(home_rows)<=25 and 11<=len(away_rows)<=25):return None
        hi=[int(r.get('player_id') or 0) for r in home_rows];ai=[int(r.get('player_id') or 0) for r in away_rows]
        if any(x<=0 for x in hi+ai):return None
        if len(set(hi))!=len(hi) or len(set(ai))!=len(ai) or set(hi)&set(ai):return None
        calc_h=sum(int(r.get('goals',0) or 0) for r in home_rows)+sum(int(r.get('own_goals',0) or 0) for r in away_rows)
        calc_a=sum(int(r.get('goals',0) or 0) for r in away_rows)+sum(int(r.get('own_goals',0) or 0) for r in home_rows)
        if calc_h!=int(fix.get('home_score') or 0) or calc_a!=int(fix.get('away_score') or 0):return None
        hh=sum(1 for pid in hi if current_club(pid)==home);ho=sum(1 for pid in hi if current_club(pid) not in ('',home))
        ah=sum(1 for pid in ai if current_club(pid)==away);ao=sum(1 for pid in ai if current_club(pid) not in ('',away))
        # A match recovered by recover_unlabelled_rich_members can already be bound to one
        # authoritative fixture (exact clubs, score and fixture id) before this join. Do not
        # reject that historical match merely because transfers/loans mean fewer than six of
        # its players still belong to the same CURRENT club. Ungrounded candidates retain the
        # strict current-cohort proof.
        if not grounded:
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
        grounded_id=int(m.get('grounded_fixture_id') or 0);source=str(m.get('source') or m.get('identity_source') or '')
        grounded=bool(grounded_id and grounded_id==int(fix.get('fixture_id') or 0) and source.startswith('unlabelled_retained_'))
        if grounded_id and not grounded:continue
        val=validate_sides(home_rows,away_rows,home,away,fix,grounded)
        if not val:continue
        source=str(m.get('source') or m.get('identity_source') or 'recovered_inference')
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

def build_players(squads:dict[int,list[int]], selected_clubs:dict[int,Club], people:dict[int,Person], rich:list[dict[str,Any]]|None=None):
    memberships=collections.defaultdict(list)
    for ceid,eids in squads.items():
        for eid in eids: memberships[eid].append(ceid)
    # Resolve duplicate list membership from actual current-season rich match participation when available.
    # v68: retained match history is never authoritative for CURRENT club membership.
    out=[]; unresolved=[]; ambiguous=[]
    for eid,clubs in sorted(memberships.items()):
        person=people.get(eid)
        if not person:
            unresolved.append(eid);continue
        clubs=sorted(set(clubs))
        if len(clubs)!=1:
            # v72: preserve the decoded person and every current-DB club candidate, but
            # never guess current membership from retained/history evidence.  The player
            # is quarantined from the selectable fantasy DB until a future current-DB
            # decoder can resolve the ambiguity.
            ambiguous.append({
                'player_eid':eid,
                'club_eids':clubs,
                'reason':'multiple_current_squad_records',
                'quarantined_from_fantasy_selection':True,
                'candidate_clubs':[{'club_eid':ce,'name':selected_clubs[ce].name,'short':selected_clubs[ce].short} for ce in clubs if ce in selected_clubs],
                'person_evidence':{
                    'legal_name':person.name,
                    'display_name':getattr(person,'display_name',None),
                    'common_name':person.common_name,
                    'first_name':getattr(person,'first_name',None),
                    'surname_name':getattr(person,'surname_name',None),
                    'first_name_id':getattr(person,'first_name_id',None),
                    'surname_name_id':getattr(person,'surname_name_id',None),
                    'common_name_id':getattr(person,'common_name_id',None),
                    'positions':list(person.positions or []),
                    'current_ability':person.current_ability,
                    'potential_ability':person.potential_ability,
                },
            })
            continue
        ceid=clubs[0]
        c=selected_clubs[ceid]
        pos=fantasy_position(person.positions)
        out.append({'id':str(eid),'pid':str(eid),'name':person.display_name,'display_name':person.display_name,'public_name':person.display_name,'legal_name':person.name,'first_name':getattr(person,'first_name',None),'surname_name':getattr(person,'surname_name',None),'common_name':person.common_name,'first_name_id':getattr(person,'first_name_id',None),'surname_name_id':getattr(person,'surname_name_id',None),'common_name_id':getattr(person,'common_name_id',None),'identity_components_preserved':True,'name_component_evidence':{'legal_full':person.name,'first':getattr(person,'first_name',None),'surname_family':getattr(person,'surname_name',None),'common_known_as':person.common_name,'first_pool_id':getattr(person,'first_name_id',None),'surname_pool_id':getattr(person,'surname_name_id',None),'common_pool_id':getattr(person,'common_name_id',None),'nickname':None,'shirt_name':None,'preferred_short_name':None,'schema':'person_string_pools_v1'},'name_resolution_evidence':{'resolved_display':getattr(person,'display_name',None),'display_equals_legal':bool(getattr(person,'display_name',None) and getattr(person,'display_name',None)==person.name),'display_equals_common':bool(getattr(person,'display_name',None) and person.common_name and getattr(person,'display_name',None)==person.common_name),'display_contains_common':bool(getattr(person,'display_name',None) and person.common_name and person.common_name.casefold() in getattr(person,'display_name',None).casefold()),'display_contains_surname':bool(getattr(person,'display_name',None) and getattr(person,'surname_name',None) and getattr(person,'surname_name',None).casefold() in getattr(person,'display_name',None).casefold()),'source':'preserved_components_plus_current_resolver'},'preferred_name':person.common_name,'first_name':person.first_name,'surname':person.surname,'football_surname':person.surname,'legal_full_name':person.name,'club':normalize_club_name(c.short or c.name),'club_full':c.name,'club_eid':ceid,'pos':pos,'positions':{POSITION_NAMES[i]:v for i,v in enumerate(person.positions or [])},'ca':person.current_ability,'pa':person.potential_ability,'price':price_from_ca(pos,person.current_ability),'apps':0,'minutes':0,'goals':0,'assists':0,'yc':0,'rc':0,'saves':0,'gc':0,'starts':0,'avg_rating':0.0,'fantasy_points':0,'points':0,'form_points':0.0,'form':0.0,'history':[],'weekly_points':{},'visible':True,'available':True,'unresolved':False})
    return out,unresolved,ambiguous


def aggregate_player_history(players:list[dict[str,Any]],matches:list[dict[str,Any]]):
    byid={int(p['pid']):p for p in players}
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
    for m in matches:
        for key in ('home_players','away_players'):
            for r in m[key]:
                pid=int(r.get('player_id') or 0)
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
                h={k:r.get(k) for k in ['match_id','opponent','venue','score','home','away','minutes','goals','assists','yellow_cards','red_cards','rating','goals_conceded','saves','appearance_pts','goal_pts','assist_pts','clean_sheet_pts','save_pts','gc_pts','card_pts','defcon_actions','defcon_pts','bonus','bps_proxy','fpl_points','gameweek','own_goals','penalties_missed','match_position_marker','identity_source']};h['date']=m.get('date')
                h['yc']=h.pop('yellow_cards') or 0;h['rc']=h.pop('red_cards') or 0;h['gc']=h.pop('goals_conceded') or 0
                p['history'].append(h)
                mins=r.get('minutes',0) or 0
                p['apps']+=1 if mins>0 else 0;p['minutes']+=mins;p['goals']+=r.get('goals',0) or 0;p['assists']+=r.get('assists',0) or 0;p['yc']+=r.get('yellow_cards',0) or 0;p['rc']+=r.get('red_cards',0) or 0;p['saves']+=r.get('saves',0) or 0;p['gc']+=r.get('team_goals_conceded_while_on_pitch',0) or 0;p['starts']+=1 if str(r.get('appearance','')).startswith('Started') else 0
                p['fantasy_points']+=r.get('fpl_points',0) or 0;p['weekly_points'][str(r['gameweek'])]=p['weekly_points'].get(str(r['gameweek']),0)+(r.get('fpl_points',0) or 0)
    for p in players:
        ratings=[h['rating'] for h in p['history'] if h.get('rating')]
        p['avg_rating']=round(sum(ratings)/len(ratings),2) if ratings else 0.0
        recent=sorted(p['history'],key=lambda h:h['gameweek'])[-4:]
        p['form_points']=round(sum(h.get('fpl_points',0) for h in recent)/len(recent),1) if recent else 0.0
        p['points']=p['fantasy_points'];p['form']=p['form_points']
        card_rows=[h for h in p['history'] if int(h.get('yc',0) or 0)>0 or int(h.get('rc',0) or 0)>0]
        card_rows.sort(key=lambda h:(str(h.get('date') or ''),int(h.get('gameweek') or 0)))
        _hist_rows=list(p.get('history') or [])
        _hist_gws=sorted({int(h.get('gameweek') or 0) for h in _hist_rows if int(h.get('gameweek') or 0)>0})
        _hist_dates=sorted({str(h.get('date')) for h in _hist_rows if h.get('date')})
        p['retained_history_evidence']={
            'decoded_rows':len(_hist_rows),
            'decoded_gameweeks':_hist_gws,
            'first_decoded_date':(_hist_dates[0] if _hist_dates else None),
            'last_decoded_date':(_hist_dates[-1] if _hist_dates else None),
            'history_is_partial_or_unknown':True,
            'zero_stats_are_observed_only_within_decoded_rows':True,
            'source':'decoded_rich_history'
        }
        p['discipline_evidence']={
            'yellow_cards':int(p.get('yc',0) or 0),'red_cards':int(p.get('rc',0) or 0),
            'history_rows':len(p.get('history') or []),
            'last_card_date':(card_rows[-1].get('date') if card_rows else None),
            'last_card_gameweek':(card_rows[-1].get('gameweek') if card_rows else None),
            'source':'decoded_rich_history'
        }
    return history_identity_diag

def gameweek_schedule_meta(fixtures:list[dict[str,Any]], total_gameweeks:int|None=None)->dict[str,Any]:
    max_gw=int(total_gameweeks or max((int(f.get('round_gameweek') or f.get('gameweek') or 0) for f in fixtures),default=46))
    total=collections.Counter(int(f['gameweek']) for f in fixtures)
    played=collections.Counter(int(f['gameweek']) for f in fixtures if f['status']=='played')
    fully=[gw for gw in range(1,max_gw+1) if total[gw]>0 and played[gw]==total[gw]]
    contiguous=0;fullset=set(fully)
    for gw in range(1,max_gw+1):
        if gw in fullset:contiguous=gw
        else:break
    latest_result=max((int(f['gameweek']) for f in fixtures if f['status']=='played'),default=0)
    club_names=sorted({x for f in fixtures for x in (f.get('home'),f.get('away')) if x})
    doubles={};blanks={}
    for gw in range(1,max_gw+1):
        apps=collections.Counter()
        for f in fixtures:
            if int(f['gameweek'])!=gw:continue
            if f.get('home'):apps[f['home']]+=1
            if f.get('away'):apps[f['away']]+=1
        dg=sorted(c for c,n in apps.items() if n>1);bg=sorted(c for c in club_names if apps[c]==0)
        if dg:doubles[str(gw)]=dg
        if bg:blanks[str(gw)]=bg
    return {'fixture_counts':{str(gw):total[gw] for gw in range(1,max_gw+1)},
            'played_counts':{str(gw):played[gw] for gw in range(1,max_gw+1)},
            'fully_completed':fully,'completed_contiguous':contiguous,'latest_result':latest_result,
            'double_gameweek_clubs':doubles,'blank_gameweek_clubs':blanks,'total_gameweeks':max_gw}

def build_table(fixtures:list[dict[str,Any]]) -> list[dict[str,Any]]:
    clubs=sorted({x for f in fixtures for x in (f['home'],f['away'])})
    st={c:{'club':c,'P':0,'W':0,'D':0,'L':0,'GF':0,'GA':0,'adjustment':(-4 if c=='Southampton' else 0)} for c in clubs}
    for f in fixtures:
        if f['status']!='played':continue
        h,a=f['home'],f['away'];hg,ag=int(f['home_score']),int(f['away_score'])
        sh,sa=st[h],st[a]
        for x in (sh,sa):x['P']+=1
        sh['GF']+=hg;sh['GA']+=ag;sa['GF']+=ag;sa['GA']+=hg
        if hg>ag:sh['W']+=1;sa['L']+=1
        elif ag>hg:sa['W']+=1;sh['L']+=1
        else:sh['D']+=1;sa['D']+=1
    rows=[]
    for x in st.values():
        x['GD']=x['GF']-x['GA'];x['Pts']=x['W']*3+x['D']+x['adjustment'];rows.append(x)
    rows.sort(key=lambda x:(x['Pts'],x['GD'],x['GF']),reverse=True)
    for i,x in enumerate(rows,1):x['position']=i
    return rows


def build_star_teams(players:list[dict[str,Any]],latest_gw:int)->dict[str,dict[str,Any]]:
    out={}
    formations=[]
    for d in range(3,6):
        for m in range(2,6):
            f=10-d-m
            if 1<=f<=3:formations.append((d,m,f))
    for gw in range(1,max(1,latest_gw)+1):
        bypos={pos:sorted((p for p in players if p.get('pos')==pos),key=lambda p:(int(p.get('weekly_points',{}).get(str(gw),0)),p.get('fantasy_points',0)),reverse=True) for pos in ('GK','DEF','MID','FWD')}
        best=None
        for d,m,f in formations:
            picks=bypos['GK'][:1]+bypos['DEF'][:d]+bypos['MID'][:m]+bypos['FWD'][:f]
            if len(picks)!=11 or len({p['id'] for p in picks})!=11:continue
            pts=sum(int(p.get('weekly_points',{}).get(str(gw),0)) for p in picks)
            if best is None or pts>best[0]:best=(pts,[p['id'] for p in picks],{'GK':1,'DEF':d,'MID':m,'FWD':f})
        if best:out[str(gw)]={'points':best[0],'ids':best[1],'formation':best[2]}
    return out

def _build_payload(save_path:Path,fingerprint:str,db,fix:bytes,include_rich:bool=True)->dict[str,Any]:
    all_clubs=scan_clubs(db)
    rich_raw=rich_extract_named(save_path,all_clubs) if include_rich else []
    comp_counts=collections.Counter(m.get('competition') for m in rich_raw if m.get('competition'))
    requested_league=preferred_league if preferred_league in SUPPORTED_LEAGUES else None
    preselect_rich=[m for m in rich_raw if (not requested_league or m.get('competition')==requested_league)]
    expected_names={normalize_club_name(m[k]) for m in preselect_rich for k in ('home','away')} if (requested_league and preselect_rich) else None
    fixtures,fixture_info=select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)
    expected_league=fixture_info['competition']
    rich_raw=[m for m in rich_raw if m.get('competition')==expected_league]
    team_ids={x for f in fixtures for x in (f['home_tid'],f['away_tid'])}
    shift=fixture_info['fixture_to_club_shift']
    selected={tid-shift:all_clubs[tid-shift] for tid in team_ids}
    # Second retained-match pass, AFTER league selection. This cannot change the chosen
    # competition or club set; it only attempts to recover richer player history for the
    # selected clubs (notably some Premier League saves).
    selected_aliases=selected_rich_team_aliases(selected)
    selected_names={normalize_club_name(c.short or c.name) for c in selected.values()}
    post_raw=[]
    for i,name in enumerate(rich_names):
        p=Path(f'/tmp/rich_{i}.bin')
        if not p.exists(): continue
        buf=p.read_bytes()
        for m in _rich_extract_member(buf,selected_aliases,name):
            if m.get('competition')!=fixture_info['competition']: continue
            if normalize_club_name(m.get('home','')) not in selected_names or normalize_club_name(m.get('away','')) not in selected_names: continue
            post_raw.append(m)
        p.unlink(missing_ok=True)
    post_recovered=0
    if post_raw:
        combined=[];seen_post=set()
        for m in list(rich_raw)+post_raw:
            key=(m.get('competition'),m.get('home'),m.get('away'),m.get('home_score'),m.get('away_score'),
                 tuple(x.get('player_id') for x in m.get('home_players',[])),tuple(x.get('player_id') for x in m.get('away_players',[])))
            if key in seen_post: continue
            seen_post.add(key);combined.append(m)
        post_recovered=max(0,len(combined)-len(rich_raw));rich_raw=combined
    fixture_name={tid:normalize_club_name(selected[tid-shift].short or selected[tid-shift].name) for tid in team_ids}
    # v87: schedule dates/Gameweeks can change after postponements. The selected league
    # has already passed the exact full double-round-robin shape check, so ordered team
    # pairs are immutable season identities and must own the public fixture_id.
    pair_keys=[(int(f['home_tid']),int(f['away_tid'])) for f in fixtures]
    if len(set(pair_keys))!=len(fixtures):
        raise RuntimeError('Current league fixture identity is not unique by ordered team pair; refusing mutable schedule-based IDs')
    for i,f in enumerate(sorted(fixtures,key=lambda x:(int(x['home_tid']),int(x['away_tid']))),1):
        f['fixture_id']=i
        f['stable_fixture_key']=f"{fixture_info['season_start']}:{int(f['home_tid'])}>{int(f['away_tid'])}"
        f['home']=fixture_name[f['home_tid']];f['away']=fixture_name[f['away_tid']]
    results=scan_completed_results(db,fixtures)
    # First recover senior squads independently. If separate retained match-detail files are
    # missing, use grounded completed-result anchors inside game_db.dat to recover old player rows.
    squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)
    bad_squads={eid:len(vals) for eid,vals in squads.items() if not (12<=len(vals)<=45)}
    if squad_diag.get('missing_club_eids') or bad_squads:
        raise RuntimeError(f"Current first-team squad decode failed safely; missing={squad_diag.get('missing_club_eids',[])} invalid_sizes={bad_squads}. Import blocked rather than guessing from match history.")
    game_db_rich,game_db_rich_diag=recover_game_db_rich_matches(
        db,fixtures,selected,squads,shift,fixture_info['competition'])
    if game_db_rich:
        existing={(normalize_club_name(m.get('home','')),normalize_club_name(m.get('away','')),
                   int(m.get('home_score') or 0),int(m.get('away_score') or 0)) for m in rich_raw}
        for m in game_db_rich:
            k=(normalize_club_name(m.get('home','')),normalize_club_name(m.get('away','')),
               int(m.get('home_score') or 0),int(m.get('away_score') or 0))
            if k not in existing:
                rich_raw.append(m);existing.add(k)
        # v68: recovered match participation never changes current squad membership.
    target_eids={p for vals in squads.values() for p in vals}
    for m in rich_raw:
        for key in ('home_players','away_players'):
            for r in m.get(key,[]):target_eids.add(int(r['player_id']))
    people=bind_target_people(db,target_eids)
    players,unresolved,ambiguous=build_players(squads,selected,people,rich_raw)
    # v72: ambiguity is evidence, not permission to guess and not a reason to lose
    # the rest of an otherwise valid league import. Ambiguous people are absent from
    # `players` (therefore cannot be selected) and remain in `ambiguous` for debugging
    # and future current-database-only resolver paths.
    pbyeid={int(p['pid']):p for p in players}
    rich_matches=join_rich_matches(rich_raw,fixtures,pbyeid) if rich_raw else []
    _rich_fixture_ids={int(m.get('fixture_id') or 0) for m in rich_matches}
    _coverage={}
    for _gw in sorted({int(f.get('gameweek') or 0) for f in fixtures if int(f.get('gameweek') or 0)>0}):
        _pf=[f for f in fixtures if int(f.get('gameweek') or 0)==_gw and f.get('status')=='played']
        _coverage[str(_gw)]={'played_fixtures':len(_pf),'rich_fixtures':sum(1 for f in _pf if int(f.get('fixture_id') or 0) in _rich_fixture_ids),
                            'missing_fixture_ids':[int(f.get('fixture_id') or 0) for f in _pf if int(f.get('fixture_id') or 0) not in _rich_fixture_ids]}
    history_identity_diag=aggregate_player_history(players,rich_matches)
    availability_diag=_structural_availability_from_fs(players,fixtures)
    reprice_players(players,fixtures)
    fixtures.sort(key=lambda x:(x['gameweek'],x['date'],x['fixture_id']))
    sched=gameweek_schedule_meta(fixtures,fixture_info['total_gameweeks'])
    current=sched['completed_contiguous']
    table=build_table(fixtures)
    star_teams=build_star_teams(players,current)
    meta={'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','fixture_club_mapping_policy':fixture_info.get('fixture_club_mapping_policy'),'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence'),'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY,'fingerprint':fingerprint,'competition':fixture_info['competition'],'competition_code':fixture_info['competition_code'],'competition_fixture_id':fixture_info['competition_id'],'fixture_season_start':fixture_info['season_start'],'fixture_to_club_shift':shift,'fixture_candidates_considered':fixture_info['candidate_groups'],'fixture_exact_candidates':fixture_info['exact_candidate_groups'],'fixture_rich_name_overlap':fixture_info['rich_name_overlap'],'rich_competition_counts':dict(comp_counts),'rich_selected_competition':expected_league,'requested_league':requested_league,'requested_league_honoured':(not requested_league or fixture_info['competition']==requested_league),'league_selection_source':fixture_info.get('selection_mode',('user_preference_locked' if requested_league else 'auto_latest_season')),'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','fixture_club_mapping_policy':fixture_info.get('fixture_club_mapping_policy'),'fixture_club_mapping_evidence':fixture_info.get('selected_mapping_evidence'),'current_season_candidates':fixture_info.get('current_season_candidates',[]),'gameweek_relabels':fixture_info['gameweek_relabels'],'calendar_gameweek_model':'deadline-window-v1','calendar_gameweek_windows':fixture_info['calendar_gameweek_windows'],'calendar_reassigned_fixtures':fixture_info['calendar_reassigned_count'],'calendar_reassigned_examples':fixture_info['calendar_reassigned_examples'],'gameweek_fixture_counts':sched['fixture_counts'],'gameweek_played_counts':sched['played_counts'],'double_gameweek_clubs':sched['double_gameweek_clubs'],'blank_gameweek_clubs':sched['blank_gameweek_clubs'],'pricing_model':'fpl-shaped-v65-role-projection-guardrails','availability_decoder':'structural-v1','injured_players':availability_diag.get('injured_players',0),'suspended_players':availability_diag.get('suspended_players',0),'availability_save_date':availability_diag.get('save_date'),'availability_diagnostics':availability_diag,'observed_position_reclassifications':sum(1 for p in players if p.get('position_source','').startswith('observed_')),'observed_position_usage_diagnostics':position_usage_diag,'squad_scan_fallbacks':squad_diag['fallbacks'],'squad_scan_missing_club_eids':squad_diag['missing_club_eids'],'squad_rich_augmented_players':squad_diag['rich_augmented_players'],'current_squad_identity_policy':'strict-db-membership-only-no-history-mutation-v68','current_squad_ambiguity_policy':'v72-quarantine-preserve-evidence-no-history-guess','current_squad_block_policy':'v74-require-current-db-block-consensus-no-heuristic-tiebreak','current_squad_ambiguous_players_quarantined':len(ambiguous),'history_identity_safety':history_identity_diag,'rich_match_validation_policy':'official-score-plus-strict-current-cohort-v69','rich_fixture_coverage':_coverage,'game_db_rich_matches_recovered':game_db_rich_diag['recovered'],'game_db_rich_recovery_attempted':game_db_rich_diag['attempted'],'game_db_rich_windows_with_stats':game_db_rich_diag['windows_with_stats'],'game_db_rich_candidate_pairs':game_db_rich_diag['candidate_pairs'],'clubs':fixture_info['team_count'],'team_count':fixture_info['team_count'],'total_gameweeks':fixture_info['total_gameweeks'],'fixtures':len(fixtures),'played_results':len(results),'rich_matches':len(rich_matches),'post_selection_rich_matches_recovered':post_recovered,'selected_rich_team_aliases':len(selected_aliases),'players':len(players),'unresolved_squad_eids':unresolved,'ambiguous_memberships':ambiguous,'fully_completed_gameweeks':sched['fully_completed'],'latest_gameweek_with_result':sched['latest_result'],'completed_gameweek':current,'current_gameweek':min(fixture_info['total_gameweeks'],current+1) if current<fixture_info['total_gameweeks'] else fixture_info['total_gameweeks'],'next_gameweek':min(fixture_info['total_gameweeks'],current+1) if current<fixture_info['total_gameweeks'] else fixture_info['total_gameweeks'],'hidden_unresolved':len(unresolved),'scoring_note':'Bonus uses an FM-derived BPS proxy; MID/FWD DEFCON uses FM possession-won as the recovery-equivalent.'}
    clubs_payload=[{'eid':c.eid,'uid':c.uid,'name':c.name,'short_name':normalize_club_name(c.short)} for c in sorted(selected.values(),key=lambda c:c.name)]
    return {'meta':meta,'clubs':clubs_payload,'players':players,'fixtures':fixtures,'matches':rich_matches,'table':table,'star_teams':star_teams}


def import_save(save_path:str|Path, include_rich:bool=True)->dict[str,Any]:
    save_path=Path(save_path)
    h=hashlib.sha256()
    with save_path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(8*1024*1024),b''):h.update(chunk)
    fingerprint=h.hexdigest()
    _save,items=read_manifest(save_path)
    byname={m.name:m for m in items}
    game=byname.get('game_db.dat');fix_member=byname.get('fix_man.dat')
    if not game or not fix_member:raise RuntimeError('Required FM database/fixture members not found')
    fix=extract_member(save_path,fix_member)
    # game_db is ~170 MB on the regression save. Decompress it to disk and mmap it
    # so a normal web server never needs duplicate 170 MB Python byte buffers.
    with tempfile.TemporaryDirectory(prefix='fmfantasy_') as td:
        db_path=extract_member_to_path(save_path,game,Path(td)/'game_db.dat')
        with db_path.open('rb') as fh:
            with mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ) as db:
                return _build_payload(save_path,fingerprint,db,fix,include_rich)


if __name__=='__main__' and not globals().get('FM_BROWSER_RUNTIME', False):
    import argparse,time
    ap=argparse.ArgumentParser();ap.add_argument('save');ap.add_argument('-o','--output',default='fm_fantasy_payload.json');ap.add_argument('--no-rich',action='store_true');a=ap.parse_args()
    t=__import__('time').time();payload=import_save(a.save,not a.no_rich)
    Path(a.output).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload['meta'],indent=2));print('seconds',round(__import__('time').time()-t,2))



def _rich_candidate_squad_pairs(stats:list[dict[str,Any]], played_score_pairs:set[tuple[int,int]]|None=None):
    """Return plausible retained home/away stat blocks without assuming one fixed squad size.

    Keep the legacy 20+20 path first. When that exact window is unavailable or its aggregate
    score cannot exist in the already-decoded played calendar, try a bounded 18..22 rows per
    side fallback. The fallback must satisfy the same byte-compactness rules AND an authoritative
    played-score constraint, so it expands schema coverage without creating free-form matches.
    """
    pairs=[]
    if len(stats)<36:return pairs
    played_score_pairs=set(played_score_pairs or ())

    def window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        max_l=max((left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)),default=0)
        max_r=max((right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)),default=0)
        if gap<=500 or max_l>=1500 or max_r>=1500:return None
        return left,right

    def agg(pair):
        left,right=pair
        return (
            sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right),
            sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left)
        )

    for j in range(17,len(stats)-18):
        strict=window(j,20,20)
        if strict:
            pairs.append(strict)
            # If the legacy representation already produces a score that exists in the
            # authoritative league calendar, do not manufacture alternative sizes here.
            if not played_score_pairs or agg(strict) in played_score_pairs:continue

        # Alternate FM schema / competition matchday-list sizes. Only candidates whose score
        # is already known to exist in the decoded played calendar are eligible.
        viable=[]
        for left_n in range(18,23):
            for right_n in range(18,23):
                if left_n==20 and right_n==20:continue
                pair=window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
                viable.append((left_n+right_n,-abs(left_n-right_n),-abs(left_n-20)-abs(right_n-20),pair))
        if viable:
            # Prefer the fullest compact representation, then balanced sides, then sizes nearest
            # the legacy 20. Downstream fixture/player identity still has to validate the match.
            viable.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
            pairs.append(viable[0][3])
    return pairs


def _rich_scan_stats_fast(buf:bytes,start:int,end:int):
    """Same validation as _rich_scan_stats, but jumps between 0x02 candidate bytes."""
    out=[];p=max(0,start);end=min(len(buf),end)
    while p<end-214:
        p=buf.find(b'\x02',p,end-213)
        if p<0:break
        r=_rich_stat_record_at(buf,p)
        if r:
            out.append(r);p+=140
        else:p+=1
    return out




def _rich_is_retained_match_member(name:str):
    # Only isolated retained match files are safe input for unlabelled player-side recovery.
    # Aggregate databases such as news.dat/play_fixture_manager.dat contain repeated copies of
    # the same 214-byte-looking structures and create hundreds of false lineup windows.
    return Path(str(name or '')).suffix.lower() in ('.scm','.apm','.pkm')


def recover_unlabelled_rich_members(rich_names:list[str], selected_clubs:dict[int,Club], squads:dict[int,list[int]],
                                    fixtures:list[dict[str,Any]], fixture_shift:int, competition:str):
    """Recover retained player-match blocks that have no reliable team/competition label.

    Multi-path identity strategy (all after one archive scan):
      A. strict current-squad anchors (legacy path);
      B. repeated-side cluster labels;
      C. semi-supervised player/cohort propagation from confidently identified sides;
      D. fixture-constrained global matching using both side identity and exact score;
      E. one-strong-side bridge when the known club + score identifies exactly one fixture.

    Text labels are intentionally not required here. Every accepted recovery is still tied to one
    authoritative played fixture and exact aggregate score. Ambiguous candidates are left unused.
    """
    diagnostics={
        'members_scanned':0,'members_with_stats':0,'stat_records':0,'candidate_pairs':0,
        'matches_recovered':0,'cached_candidate_pairs':0,'side_clusters':0,'labelled_side_clusters':0,
        'propagation_rounds':0,'propagation_matches':0,'strict_seed_matches':0,
        'cluster_matches':0,'unmatched_cached_pairs':0,
        'cohort_side_labels':0,'fixture_identity_matches':0,'single_side_bridge_matches':0,
        'identity_rounds':0,'ambiguous_seed_player_ids':0,'transfer_conflict_neutralized_players':0,
        'adaptive_cluster_edges':0,'adaptive_cluster_edges_rejected_conflict':0,
        'near_duplicate_candidate_pairs_collapsed':0,'near_duplicate_candidate_pairs_soft_collapsed':0,
        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0,'sub40_stat_members':0,
        'same_lineup_distinct_regions_preserved':0,'non_retained_members_skipped':0,'non_retained_member_names':[]
    }
    club_sets={eid:set(int(x) for x in squads.get(eid,[])) for eid in selected_clubs}
    membership_owners=collections.defaultdict(set)
    for _eid,_pids in club_sets.items():
        for _pid in _pids:membership_owners[int(_pid)].add(_eid)
    unique_club_sets={eid:{pid for pid in pids if len(membership_owners.get(int(pid),()))==1}
                      for eid,pids in club_sets.items()}
    ambiguous_seed_player_ids={pid for pid,owners in membership_owners.items() if len(owners)>1}
    club_names={eid:normalize_club_name(c.short or c.name) for eid,c in selected_clubs.items()}
    played=[]
    for f in fixtures:
        if f.get('status')!='played':continue
        heid=int(f['home_tid'])-int(fixture_shift);aeid=int(f['away_tid'])-int(fixture_shift)
        played.append((heid,aeid,int(f.get('home_score') or 0),int(f.get('away_score') or 0),f))
    played_score_pairs={(hs,as_) for _h,_a,hs,as_,_f in played}
    played_score_pairs|={(as_,hs) for _h,_a,hs,as_,_f in played}

    cached=[];seen_pairs=set()
    for i,name in enumerate(rich_names):
        path=Path(f'/tmp/rich_{i}.bin')
        if not path.exists():continue
        if not _rich_is_retained_match_member(name):
            diagnostics['non_retained_members_skipped']+=1
            if len(diagnostics['non_retained_member_names'])<20:diagnostics['non_retained_member_names'].append(str(name))
            continue
        diagnostics['members_scanned']+=1
        buf=path.read_bytes()
        stats=_rich_scan_stats_fast(buf,0,len(buf))
        diagnostics['stat_records']+=len(stats)
        if len(stats)<36:continue
        if len(stats)<40:diagnostics['sub40_stat_members']+=1
        diagnostics['members_with_stats']+=1
        pairs=_rich_candidate_squad_pairs(stats,played_score_pairs)
        diagnostics['candidate_pairs']+=len(pairs)
        diagnostics['variable_squad_size_candidate_pairs']+=sum(1 for left,right in pairs if len(left)!=20 or len(right)!=20)
        for left,right in pairs:
            pk=(name,left[0]['offset'],left[-1]['offset'],right[0]['offset'],right[-1]['offset'])
            if pk in seen_pairs:continue
            seen_pairs.add(pk)
            cached.append({'name':name,'left':left,'right':right,'pk':pk})
    # Normalize near-identical scanner windows before any identity inference. A save may
    # contain several candidate windows around the same retained player block; allowing all
    # of them into proposal ranking artificially lowers uniqueness margins. v59's exact-set
    # path remains first. A second conservative path handles adjacent windows which gained or
    # lost one/two edge player rows: same source member, same aggregate score, near-identical
    # byte span and >=88% Jaccard overlap on both sides (allowing side orientation to flip).
    if cached:
        compact=[];seen_exact=collections.defaultdict(list);seen_member=collections.defaultdict(list)
        def _norm_ids(rows):
            return frozenset(int(x.get('player_id') or 0) for x in rows if int(x.get('player_id') or 0)>0)
        def _jac(a,b):
            u=len(a|b)
            return (len(a&b)/u) if u else 0.0
        def _pair_score_inline(c):
            left,right=c['left'],c['right']
            return (sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right),
                    sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left))
        for c in cached:
            lids=_norm_ids(c['left']);rids=_norm_ids(c['right'])
            pair_key=tuple(sorted((tuple(sorted(lids)),tuple(sorted(rids)))))
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            end=max(int(c['left'][-1]['offset']),int(c['right'][-1]['offset']))
            score=_pair_score_inline(c)
            sig=(c['name'],pair_key)
            duplicate=False
            for ps,pe in seen_exact[sig]:
                if abs(start-ps)<=2048 and abs(end-pe)<=2048:
                    duplicate=True;break
            if duplicate:
                diagnostics['near_duplicate_candidate_pairs_collapsed']+=1
                continue
            # Soft duplicate path. Byte locality is mandatory, so two genuine matches which
            # reuse almost the same XI do not collapse just because their lineups look alike.
            for prev in seen_member[c['name']]:
                if abs(start-prev['start'])>2048 or abs(end-prev['end'])>2048:continue
                ps=prev['score']
                same_score=(score==ps or score==(ps[1],ps[0]))
                if not same_score:continue
                pl,pr=prev['lids'],prev['rids']
                direct=min(_jac(lids,pl),_jac(rids,pr))
                flipped=min(_jac(lids,pr),_jac(rids,pl))
                best=max(direct,flipped)
                if best<0.88:continue
                # Also cap total player-set drift. This keeps the fallback targeted at
                # neighbouring scanner windows rather than merely similar rotated lineups.
                if direct>=flipped:
                    drift=len(lids^pl)+len(rids^pr)
                else:
                    drift=len(lids^pr)+len(rids^pl)
                if drift>4:continue
                duplicate=True;diagnostics['near_duplicate_candidate_pairs_soft_collapsed']+=1;break
            if duplicate:continue
            seen_exact[sig].append((start,end))
            seen_member[c['name']].append({'start':start,'end':end,'score':score,'lids':lids,'rids':rids})
            compact.append(c)
        cached=compact
        # Exact/adjacent scanner duplicates are already removed by byte locality.
        # Repeated lineup signatures which survive are distinct retained regions.
        _lineup_counts=collections.Counter()
        for _c in cached:
            _l=tuple(sorted(ids_of_row for ids_of_row in (int(x.get('player_id') or 0) for x in _c['left']) if ids_of_row>0))
            _r=tuple(sorted(ids_of_row for ids_of_row in (int(x.get('player_id') or 0) for x in _c['right']) if ids_of_row>0))
            _lineup_counts[(_c['name'],tuple(sorted((_l,_r))))]+=1
        diagnostics['same_lineup_distinct_regions_preserved']=sum(max(0,n-1) for n in _lineup_counts.values())
    diagnostics['cached_candidate_pairs']=len(cached)
    if not cached:return [],diagnostics

    def ids_of(rows):
        return {int(x['player_id']) for x in rows if int(x.get('player_id') or 0)>0}

    def score_of(c):
        left,right=c['left'],c['right']
        lhg=sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right)
        lag=sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left)
        return lhg,lag

    sides=[]
    for ci,c in enumerate(cached):
        for which in ('left','right'):
            rows=c[which];sides.append({'candidate':ci,'which':which,'rows':rows,'ids':ids_of(rows)})
    n=len(sides);parent=list(range(n));size=[1]*n
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        a=find(a);b=find(b)
        if a==b:return
        if size[a]<size[b]:a,b=b,a
        parent[b]=a;size[a]+=size[b]

    occ=collections.defaultdict(list)
    for si,s in enumerate(sides):
        for pid in s['ids']:occ[pid].append(si)
    shared=collections.Counter()
    for arr in occ.values():
        if len(arr)>80:continue
        for ai in range(len(arr)):
            for bi in range(ai+1,len(arr)):
                a,b=arr[ai],arr[bi]
                if a>b:a,b=b,a
                shared[(a,b)]+=1
    def direct_anchor_club(ids):
        rank=[]
        for eid,pids in unique_club_sets.items():
            n=len(ids & pids)
            if n:rank.append((n,eid))
        rank.sort(reverse=True)
        if not rank or rank[0][0]<4:return None
        if len(rank)>1 and rank[0][0]-rank[1][0]<2:return None
        return rank[0][1]

    for (a,b),cnt in shared.items():
        if cnt>=8:
            union(a,b);continue
        # Rotation-safe fallback: six shared players can be highly significant when the
        # two retained sides are 15-22 player matchday groups. Require a meaningful
        # proportional overlap and block the edge when independent unique squad anchors
        # confidently identify different clubs.
        if cnt<6:continue
        ia=sides[a]['ids'];ib=sides[b]['ids']
        denom=max(1,min(len(ia),len(ib)))
        overlap=float(cnt)/denom
        if overlap<0.34:continue
        ca=direct_anchor_club(ia);cb=direct_anchor_club(ib)
        if ca is not None and cb is not None and ca!=cb:
            diagnostics['adaptive_cluster_edges_rejected_conflict']+=1
            continue
        union(a,b);diagnostics['adaptive_cluster_edges']+=1

    clusters=collections.defaultdict(list)
    for si in range(n):clusters[find(si)].append(si)
    diagnostics['side_clusters']=len(clusters)

    player_votes=collections.defaultdict(lambda:collections.Counter())
    diagnostics['ambiguous_seed_player_ids']=len(ambiguous_seed_player_ids)
    for eid,pids in unique_club_sets.items():
        for pid in pids:player_votes[int(pid)][eid]+=4.0
    transfer_conflicts=set()
    confirmed_side_cohorts=collections.defaultdict(list)
    confirmed_cohort_seen=set()
    diagnostics.setdefault('confirmed_cohort_side_labels',0)
    diagnostics.setdefault('confirmed_cohort_conflicts_rejected',0)
    diagnostics.setdefault('confirmed_cohort_fixture_matches',0)
    diagnostics.setdefault('confirmed_roster_fixture_matches',0)
    diagnostics.setdefault('confirmed_roster_side_uses',0)
    diagnostics.setdefault('confirmed_roster_conflicts_rejected',0)
    diagnostics.setdefault('confirmed_roster_one_side_fixture_matches',0)
    diagnostics.setdefault('confirmed_roster_one_side_side_uses',0)
    diagnostics.setdefault('confirmed_roster_one_side_ambiguities_rejected',0)
    diagnostics.setdefault('global_constraint_unique_components',0)
    diagnostics.setdefault('global_constraint_fixture_matches',0)
    diagnostics.setdefault('global_constraint_oversized_components_rejected',0)
    diagnostics.setdefault('global_constraint_unbalanced_components_rejected',0)
    diagnostics.setdefault('global_constraint_no_perfect_match_rejected',0)
    diagnostics.setdefault('global_constraint_nonunique_components_rejected',0)
    # Confirmed retained matches supply dated club appearances. Keep them separately from the
    # ordinary player votes so transfer ambiguity can remain neutral by default while fixture
    # scoring may use a very small nearest-date signal when BOTH clubs have confirmed dates.
    confirmed_temporal_clubs=collections.defaultdict(list)
    def _history_date_ordinal(v):
        try:
            y,m,d=(int(x) for x in str(v or '')[:10].split('-'))
            return y*372+m*31+d
        except Exception:
            return 0

    def player_club_weight(pid,eid):
        votes=player_votes.get(int(pid))
        if not votes:return 0.0
        total=sum(votes.values())
        if total<=0:return 0.0
        top=votes.most_common(3)
        # Once the same player has meaningful evidence for two clubs, treat that player as
        # transfer/identity-ambiguous for historical side labelling. Teammate cohorts still
        # identify the side, but this individual can no longer drag an old match toward his
        # present-day club. Confirmed match rows remain available for fantasy scoring.
        meaningful=[(ceid,v) for ceid,v in top if v>=1.75]
        if len(meaningful)>1:
            transfer_conflicts.add(int(pid));diagnostics['transfer_conflict_neutralized_players']=len(transfer_conflicts)
            return 0.0
        if len(top)>1 and abs(top[0][1]-top[1][1])<0.75 and eid in (top[0][0],top[1][0]):
            return 0.0
        return min(1.0,float(votes.get(eid,0.0))/max(1.0,total)*1.35)

    def side_scores(ids):
        scores=[]
        for eid in selected_clubs:
            weighted=sum(player_club_weight(pid,eid) for pid in ids)
            direct=len(ids & unique_club_sets[eid])
            score=weighted+0.55*direct
            if score>0:scores.append((score,direct,eid))
        scores.sort(reverse=True)
        return scores

    def confirmed_cohort_club(ids):
        # A later retained side may rotate heavily away from today's current squad but still
        # overlap a side already attached to an authoritative fixture. Require substantial
        # direct player overlap with a CONFIRMED side and a clear club margin.
        ranked=[]
        for eid,cohorts in confirmed_side_cohorts.items():
            best_shared=0;best_frac=0.0
            for cohort in cohorts:
                shared=len(ids & cohort)
                frac=shared/max(1,min(len(ids),len(cohort)))
                if (shared,frac)>(best_shared,best_frac):best_shared,best_frac=shared,frac
            if best_shared>=6 and best_frac>=0.34:ranked.append((best_shared,best_frac,eid))
        ranked.sort(reverse=True)
        if not ranked:return None
        top=ranked[0];second=ranked[1] if len(ranked)>1 else (0,0.0,None)
        # Seven shared players is strong on its own; six requires a two-player margin.
        if top[0]<7 and top[0]-second[0]<2:return None
        if top[0]==second[0] and abs(top[1]-second[1])<0.10:
            diagnostics['confirmed_cohort_conflicts_rejected']+=1;return None
        # Never let historical cohort evidence contradict a confident unique CURRENT-squad anchor.
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top[2]:
            diagnostics['confirmed_cohort_conflicts_rejected']+=1;return None
        return top[2],top[0],top[1]

    def confirmed_roster_club(ids):
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
        scores=side_scores(ids)
        if scores and scores[0][0]>=min_score:
            second=scores[1][0] if len(scores)>1 else 0.0
            if scores[0][0]-second>=min_margin:return scores[0][2],scores[0][0],second,scores[0][1]
        cohort=confirmed_cohort_club(ids)
        if cohort:
            diagnostics['confirmed_cohort_side_labels']+=1
            # Return a bounded confidence score compatible with existing callers; fixture
            # registration still requires exact score and authoritative fixture uniqueness.
            eid,shared,frac=cohort
            return eid,4.6+min(2.0,(shared-6)*0.35+frac),0.0,shared
        return None

    def temporal_side_evidence(ids,eid,date_value):
        target=_history_date_ordinal(date_value)
        if not target:return 0.0
        value=0.0
        for pid in ids:
            pid=int(pid)
            if pid not in transfer_conflicts:continue
            recs=confirmed_temporal_clubs.get(pid,[])
            # A single dated club is not enough: it may simply be the old club plus today's
            # squad membership. Require confirmed retained appearances for at least two clubs.
            if len({ceid for _ord,ceid in recs})<2:continue
            nearest=min(recs,key=lambda x:abs(x[0]-target))
            gap=abs(nearest[0]-target)
            if gap>93:continue
            closeness=1.0-(gap/94.0)
            if nearest[1]==eid:value+=0.55*closeness
            elif gap<=31:value-=0.45*(1.0-gap/32.0)
        return value

    cluster_labels={}
    def relabel_clusters():
        cluster_labels.clear()
        for root,members in clusters.items():
            votes=collections.Counter()
            for si in members:
                hit=best_side_club(sides[si]['ids'],2.75,0.9)
                if hit:votes[hit[0]]+=max(1.0,hit[1])
            if votes:
                top=votes.most_common(2)
                if len(top)==1 or top[0][1]-top[1][1]>=2.0:cluster_labels[root]=top[0][0]
        diagnostics['labelled_side_clusters']=max(diagnostics['labelled_side_clusters'],len(cluster_labels))

    used_fixtures=set();used_candidates=set();out=[]

    def fixture_identity(f):
        raw=int(f.get('fixture_id') or 0)
        if raw>0:return ('id',raw)
        # Alternate FM schema generations may omit/zero fixture_id. Calendar structure is
        # already authoritative at this point, so use a composite identity rather than
        # collapsing every such fixture onto key 0. Include score because this recovery
        # operates only on played fixtures and include GW/date when available to separate
        # repeated opponents/doubles.
        return ('struct',int(f.get('home_tid') or 0),int(f.get('away_tid') or 0),
                str(f.get('date') or ''),int(f.get('gameweek') or f.get('round') or 0),
                int(f.get('home_score') or 0),int(f.get('away_score') or 0))

    def candidate_fixture_options(ci,leid=None,reid=None):
        c=cached[ci];lhg,lag=score_of(c);opts=[]
        for heid,aeid,hs,as_,f in played:
            fid=fixture_identity(f)
            if fid in used_fixtures:continue
            if hs==lhg and as_==lag:
                if (leid is None or heid==leid) and (reid is None or aeid==reid):opts.append((f,False,heid,aeid))
            if hs==lag and as_==lhg:
                if (leid is None or aeid==leid) and (reid is None or heid==reid):opts.append((f,True,aeid,heid))
        return opts

    def register_match(ci,f,rev,leid,reid,source_kind):
        if ci in used_candidates:return False
        fid=fixture_identity(f)
        if fid in used_fixtures:return False
        c=cached[ci];left,right=c['left'],c['right']
        H,A=(right,left) if rev else (left,right)
        heid,realaeid=(reid,leid) if rev else (leid,reid)
        hcalc=sum(int(x.get('goals',0) or 0) for x in H)+sum(int(x.get('own_goals',0) or 0) for x in A)
        acalc=sum(int(x.get('goals',0) or 0) for x in A)+sum(int(x.get('own_goals',0) or 0) for x in H)
        if hcalc!=int(f.get('home_score') or 0) or acalc!=int(f.get('away_score') or 0):return False
        used_fixtures.add(fid);used_candidates.add(ci)
        # v93: only an already-accepted authoritative match may teach a retained cohort.
        # Store each exact side once; no unconfirmed/propagated candidate can self-reinforce.
        _lids=ids_of(left);_rids=ids_of(right)
        for _eid,_ids in ((leid,_lids),(reid,_rids)):
            _sig=(_eid,tuple(sorted(_ids)))
            if _sig not in confirmed_cohort_seen:
                confirmed_cohort_seen.add(_sig);confirmed_side_cohorts[_eid].append(set(_ids))
        # Only accepted matches teach temporal membership. Speculative side labels never enter
        # this table, preventing a guessed transfer timeline from reinforcing itself.
        ford=_history_date_ordinal(f.get('date'))
        if ford:
            for pid in ids_of(H):confirmed_temporal_clubs[int(pid)].append((ford,heid))
            for pid in ids_of(A):confirmed_temporal_clubs[int(pid)].append((ford,realaeid))
        out.append({'stadium':f.get('stadium'),'home':club_names[heid],'away':club_names[realaeid],
                    'home_tid':f['home_tid'],'away_tid':f['away_tid'],'competition':competition,
                    'competition_code':SUPPORTED_LEAGUES.get(competition,{}).get('code'),
                    'home_score':int(f['home_score']),'away_score':int(f['away_score']),'date':f.get('date'),
                    'grounded_fixture_id':int(f.get('fixture_id') or 0),
                    'home_players':_rich_decorate(H),'away_players':_rich_decorate(A),
                    'offset':min(H[0]['offset'],A[0]['offset']),'source_member':c['name'],'source':source_kind})
        for pid in ids_of(H):
            club_sets[heid].add(pid);player_votes[pid][heid]+=2.0
        for pid in ids_of(A):
            club_sets[realaeid].add(pid);player_votes[pid][realaeid]+=2.0
        return True

    def strict_seed(ci):
        c=cached[ci];lids=ids_of(c['left']);rids=ids_of(c['right'])
        lc=[];rc=[]
        for eid,sset in club_sets.items():
            uset=unique_club_sets.get(eid,set());lo=len(lids&uset);ro=len(rids&uset)
            if lo>=5:lc.append((lo,eid))
            if ro>=5:rc.append((ro,eid))
        lc.sort(reverse=True);rc.sort(reverse=True)
        best=None
        for lov,leid in lc[:4]:
            for rov,reid in rc[:4]:
                if leid==reid or lov+rov<14:continue
                score=(lov+rov,min(lov,rov))
                if best is None or score>best[0]:best=(score,leid,reid)
        if not best:return False
        opts=candidate_fixture_options(ci,best[1],best[2])
        if len(opts)!=1:return False
        f,rev,leid,reid=opts[0]
        return register_match(ci,f,rev,leid,reid,'unlabelled_retained_stat_blocks_strict')

    for ci in range(len(cached)):
        if strict_seed(ci):diagnostics['strict_seed_matches']+=1

    def propagate_side_identities(max_rounds=8):
        accepted=0
        labelled_side=set()
        for _ in range(max_rounds):
            progress=0
            relabel_clusters()
            for si,s in enumerate(sides):
                if si in labelled_side:continue
                hit=best_side_club(s['ids'],3.0,1.15)
                if not hit:
                    ceid=cluster_labels.get(find(si))
                    if ceid is None:continue
                    scores=side_scores(s['ids']);sc=next((x[0] for x in scores if x[2]==ceid),0.0)
                    if sc<2.2:continue
                    hit=(ceid,sc,0.0,0)
                eid=hit[0]
                labelled_side.add(si);progress+=1;accepted+=1
                for pid in s['ids']:player_votes[pid][eid]+=0.7
            if not progress:break
            diagnostics['identity_rounds']+=1
        diagnostics['cohort_side_labels']=max(diagnostics['cohort_side_labels'],accepted)

    propagate_side_identities()
    relabel_clusters()

    for ci in range(len(cached)):
        if ci in used_candidates:continue
        leid=cluster_labels.get(find(ci*2));reid=cluster_labels.get(find(ci*2+1))
        if leid is None or reid is None or leid==reid:continue
        opts=candidate_fixture_options(ci,leid,reid)
        if len(opts)==1:
            f,rev,le,re=opts[0]
            if register_match(ci,f,rev,le,re,'unlabelled_retained_cluster_match'):
                diagnostics['cluster_matches']+=1

    def fixture_identity_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right']);ls=side_scores(lids);rs=side_scores(rids)
            lmap={eid:(sc,direct) for sc,direct,eid in ls};rmap={eid:(sc,direct) for sc,direct,eid in rs}
            lhg,lag=score_of(c);rank=[]
            for heid,aeid,hs,as_,f in played:
                fid=fixture_identity(f)
                if fid in used_fixtures:continue
                for rev in (False,True):
                    if not rev:
                        if hs!=lhg or as_!=lag:continue
                        leid,reid=heid,aeid
                    else:
                        if hs!=lag or as_!=lhg:continue
                        leid,reid=aeid,heid
                    lsc,ld=lmap.get(leid,(0.0,0));rsc,rd=rmap.get(reid,(0.0,0))
                    if lsc<=0 or rsc<=0:continue
                    bonus=0.0
                    lcl=cluster_labels.get(find(ci*2));rcl=cluster_labels.get(find(ci*2+1))
                    if lcl==leid:bonus+=2.0
                    elif lcl is not None and lcl!=leid:bonus-=4.0
                    if rcl==reid:bonus+=2.0
                    elif rcl is not None and rcl!=reid:bonus-=4.0
                    temporal=temporal_side_evidence(lids,leid,f.get('date'))+temporal_side_evidence(rids,reid,f.get('date'))
                    if abs(temporal)>=0.05:diagnostics['temporal_transfer_fixture_evidence']+=1
                    total=lsc+rsc+bonus+0.35*(ld+rd)+temporal
                    rank.append((total,min(lsc,rsc),f,rev,leid,reid))
            rank.sort(key=lambda x:(x[0],x[1]),reverse=True)
            if not rank:continue
            best=rank[0];second=rank[1][0] if len(rank)>1 else -999.0
            if best[0]>=7.2 and best[1]>=1.65 and best[0]-second>=1.35:
                proposals.append((best[0]-second,best[0],ci,best))
        proposals.sort(reverse=True)
        added=0
        for _margin,_score,ci,best in proposals:
            if ci in used_candidates:continue
            _,_,f,rev,leid,reid=best
            if fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_fixture_identity'):
                added+=1;diagnostics['fixture_identity_matches']+=1
        return added

    def confirmed_cohort_fixture_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lh=confirmed_cohort_club(ids_of(c['left']));rh=confirmed_cohort_club(ids_of(c['right']))
            if not lh or not rh:continue
            leid,lshared,_lfrac=lh;reid,rshared,_rfrac=rh
            if leid==reid or lshared<7 or rshared<7:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(lshared,rshared),lshared+rshared,ci,f,rev,le,re))
        proposals.sort(reverse=True)
        added=0
        for _minshared,_sumshared,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_cohort_fixture'):
                added+=1;diagnostics['confirmed_cohort_fixture_matches']+=1
        return added

    def confirmed_roster_fixture_pass():
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

    def confirmed_roster_one_side_pass():
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

    def confirmed_roster_global_constraint_pass():
        # v97: some one-side-confirmed candidates are individually ambiguous because the
        # known club + exact score fits >1 unused authoritative fixture. Recover ONLY when
        # the complete candidate/fixture ambiguity component has one unique one-to-one
        # assignment. This is constraint propagation, not score-only or threshold guessing.
        edge_options={};strengths={}
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lr=confirmed_roster_club(lids);rr=confirmed_roster_club(rids)
            # v95 handles both-known; v96 handles individually unique one-known cases.
            if bool(lr)==bool(rr):continue
            lscore,rscore=score_of(c);options=[];strength=0.0
            if lr:
                known=int(lr[0]);strength=float(lr[4])
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==heid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==aeid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            else:
                known=int(rr[0]);strength=float(rr[4])
                for heid,aeid,hs,as_,f in played:
                    if fixture_identity(f) in used_fixtures:continue
                    if known==aeid and lscore==hs and rscore==as_:
                        options.append((f,False,heid,aeid))
                    elif known==heid and lscore==as_ and rscore==hs:
                        options.append((f,True,aeid,heid))
            uniq={fixture_identity(o[0]):o for o in options}
            # Exactly-one is v96's job. Very broad ambiguity is deliberately left unresolved.
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
                    fs.add(fk)
                    stack.extend(x for x in fixture_to_candidates[fk] if x not in cs)
            components.append((cs,fs))

        def perfect_matching(cands,blocked=None):
            match_f={}
            def aug(ci,seen):
                for fk in sorted(edge_options[ci],key=repr):
                    if blocked is not None and blocked==(ci,fk):continue
                    if fk in seen:continue
                    seen.add(fk)
                    prev=match_f.get(fk)
                    if prev is None or aug(prev,seen):
                        match_f[fk]=ci;return True
                return False
            for ci in sorted(cands,key=lambda x:(len(edge_options[x]),-strengths.get(x,0.0),x)):
                if not aug(ci,set()):return None
            return {ci:fk for fk,ci in match_f.items()}

        accepted=[]
        for cs,fs in components:
            if len(cs)<2:continue
            if len(cs)>12:
                diagnostics['global_constraint_oversized_components_rejected']+=1;continue
            if len(cs)!=len(fs):
                diagnostics['global_constraint_unbalanced_components_rejected']+=1;continue
            match=perfect_matching(cs)
            if match is None:
                diagnostics['global_constraint_no_perfect_match_rejected']+=1;continue
            # A perfect matching is accepted only if removing ANY selected edge destroys
            # all perfect matchings. If an alternative complete assignment exists, preserve ambiguity.
            unique=True
            for ci,fk in match.items():
                if perfect_matching(cs,(ci,fk)) is not None:
                    unique=False;break
            if not unique:
                diagnostics['global_constraint_nonunique_components_rejected']+=1;continue
            diagnostics['global_constraint_unique_components']+=1
            for ci,fk in match.items():
                accepted.append((strengths.get(ci,0.0),ci,edge_options[ci][fk]))
        accepted.sort(key=lambda x:x[0],reverse=True);added=0
        for _strength,ci,opt in accepted:
            f,rev,leid,reid=opt
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_roster_global_unique'):
                added+=1;diagnostics['global_constraint_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lh=best_side_club(ids_of(c['left']),4.4,1.5);rh=best_side_club(ids_of(c['right']),4.4,1.5)
            options=[]
            if lh:
                options.extend(candidate_fixture_options(ci,leid=lh[0],reid=None))
            if rh:
                options.extend(candidate_fixture_options(ci,leid=None,reid=rh[0]))
            uniq={fixture_identity(o[0]):o for o in options}
            if len(uniq)!=1:continue
            f,rev,leid,reid=next(iter(uniq.values()))
            heid=int(f['home_tid'])-int(fixture_shift);aeid=int(f['away_tid'])-int(fixture_shift)
            left_eid,right_eid=(aeid,heid) if rev else (heid,aeid)
            unknown_ids=ids_of(c['right'] if lh else c['left'])
            ss=side_scores(unknown_ids)
            if ss and ss[0][0]>=3.0 and ss[0][2]!=(right_eid if lh else left_eid):continue
            strength=(lh[1] if lh else rh[1])
            proposals.append((strength,ci,f,rev,left_eid,right_eid))
        proposals.sort(reverse=True)
        added=0
        for _strength,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_single_side_bridge'):
                added+=1;diagnostics['single_side_bridge_matches']+=1
        return added

    for _round in range(8):
        before=len(out)
        propagate_side_identities(2);relabel_clusters()
        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();b=single_side_bridge_pass()
        if a or b or c or r or q or g:
            diagnostics['propagation_rounds']+=1
            diagnostics['propagation_matches']+=a+b+c+r+q+g
        if len(out)==before:break

    diagnostics['matches_recovered']=len(out)
    diagnostics['unmatched_cached_pairs']=max(0,len(cached)-len(used_candidates))
    return out,diagnostics

def recover_game_db_rich_matches(db:bytes, fixtures:list[dict[str,Any]], selected_clubs:dict[int,Club],
                                 squads:dict[int,list[int]], fixture_shift:int, competition:str):
    """Recover historical player-match rows that FM keeps in game_db.dat.

    Some saves retain final league scores/table state but purge the separate match-detail members.
    The completed-result record gives us a grounded anchor in game_db.dat.  Around each anchor we
    search only for already-proven FM player-stat record shapes, then require:
      * strong home/away senior-squad membership overlap, and
      * the stat-block goal total to exactly reproduce the decoded fixture score.
    This runs AFTER league selection, so it can never change or mix the selected division.
    """
    out=[];diagnostics={'attempted':0,'recovered':0,'windows_with_stats':0,'candidate_pairs':0}
    played=[f for f in fixtures if f.get('status')=='played' and f.get('result_offset') is not None]
    for f in played:
        diagnostics['attempted']+=1
        off=int(f['result_offset'])
        # Keep the window bounded. This is intentionally conservative: a false historical row is
        # worse than leaving a fixture score-only.
        start=max(0,off-240_000);end=min(len(db),off+240_000)
        stats=_rich_scan_stats_fast(db,start,end)
        if len(stats)<40:continue
        diagnostics['windows_with_stats']+=1
        pairs=_rich_candidate_squad_pairs(stats)
        diagnostics['candidate_pairs']+=len(pairs)
        if not pairs:continue
        heid=int(f['home_tid'])-int(fixture_shift);aeid=int(f['away_tid'])-int(fixture_shift)
        hset=set(int(x) for x in squads.get(heid,[]));aset=set(int(x) for x in squads.get(aeid,[]))
        best=None
        for left,right in pairs:
            for orientation in (0,1):
                H,A=(left,right) if orientation==0 else (right,left)
                hids={int(x['player_id']) for x in H};aids={int(x['player_id']) for x in A}
                hov=len(hids & hset);aov=len(aids & aset);membership=hov+aov
                # Calculate raw final score from player event rows before decoration.
                hg=sum(int(x.get('goals',0) or 0) for x in H)+sum(int(x.get('own_goals',0) or 0) for x in A)
                ag=sum(int(x.get('goals',0) or 0) for x in A)+sum(int(x.get('own_goals',0) or 0) for x in H)
                score_match=(hg==int(f.get('home_score') or 0) and ag==int(f.get('away_score') or 0))
                if not score_match:continue
                # Both sides must have convincing senior-squad identity evidence.
                if hov<5 or aov<5 or membership<14:continue
                center=(H[0]['offset']+A[-1]['offset'])//2
                dist=abs(center-off)
                score=(membership,min(hov,aov),-dist)
                if best is None or score>best[0]:
                    best=(score,H,A)
        if not best:continue
        _score,H,A=best
        home=_rich_decorate(H);away=_rich_decorate(A)
        out.append({'stadium':f.get('stadium'),'home':f['home'],'away':f['away'],
                    'home_tid':f['home_tid'],'away_tid':f['away_tid'],'competition':competition,
                    'competition_code':SUPPORTED_LEAGUES.get(competition,{}).get('code'),
                    'home_score':int(f['home_score']),'away_score':int(f['away_score']),
                    'home_players':home,'away_players':away,'offset':off,
                    'source_member':'game_db.dat','source':'game_db_result_anchor'})
        diagnostics['recovered']+=1
    return out,diagnostics


def select_current_competition_player_cohort(squads:dict[int,list[int]], selected_clubs:dict[int,Club]):
    """Identify FM's current competition player/registration cohort dynamically.

    FM saves keep per-competition `rgman/comp_<id>.dat` records. The internal competition
    entity number is not assumed. The browser extracts only reasonably-sized competition
    records and this function selects a record solely when it has a uniquely strong, sane
    overlap with EVERY already-proven current league club squad. That distinguishes the
    current league record from cups/other divisions without hard-coding Championship id 12.

    The selected record is then authoritative for fantasy eligibility: club-owned players who
    are absent from the current competition cohort stay in the payload for stable identity/debug
    purposes but are not selectable/visible. If the structural proof is not decisive, no player
    is hidden.
    """
    idx=Path('/tmp/comp_roster_names.json')
    diag={'version':'current-competition-cohort-v86','selected':False,'candidate_count':0,
          'selected_member':None,'eligible_players':None,'ineligible_players':None,
          'club_counts':{},'runner_up':None,'selection_margin':None,'reason':None}
    if not idx.exists():diag['reason']='competition-record-candidates-not-extracted';return None,diag
    try:names=json.loads(idx.read_text())
    except Exception:diag['reason']='competition-record-index-invalid';return None,diag
    candidates=[];total_current=sum(len(set(int(x) for x in vals if int(x)>0)) for vals in squads.values())
    for i,name in enumerate(names):
        path=Path(f'/tmp/comp_roster_{i}.bin')
        if not path.exists():continue
        buf=path.read_bytes(); counts={};members=set()
        for ceid in selected_clubs:
            hits=0
            for pid in set(int(x) for x in squads.get(ceid,[]) if int(x)>0):
                if buf.find(struct.pack('<I',pid))>=0:
                    hits+=1;members.add(pid)
            counts[ceid]=hits
        covered=sum(1 for n in counts.values() if n>=12);minimum=min(counts.values()) if counts else 0
        total=sum(counts.values());candidate={'name':name,'total':total,'covered':covered,'minimum':minimum,
                                             'counts':counts,'members':members,'size':len(buf)}
        candidates.append(candidate)
    diag['candidate_count']=len(candidates)
    # Clean temp files immediately; no second archive pass is needed.
    for i,_ in enumerate(names):Path(f'/tmp/comp_roster_{i}.bin').unlink(missing_ok=True)
    idx.unlink(missing_ok=True)
    if not candidates:diag['reason']='no-readable-competition-record-candidates';return None,diag
    candidates.sort(key=lambda c:(c['covered'],c['total'],c['minimum']),reverse=True)
    best=candidates[0];second=candidates[1] if len(candidates)>1 else None
    team_count=len(selected_clubs);ratio=(best['total']/max(1,total_current));margin=(best['total']/max(1,second['total'])) if second else 99.0
    # Current league competition cohorts are broad across every club. A cup/other competition
    # record does not pass all three gates. The runner-up margin prevents accidental filtering
    # on saves whose schema does not expose a distinct registration/player cohort.
    safe=(best['covered']==team_count and best['minimum']>=12 and ratio>=0.55 and margin>=1.08)
    diag.update({'selected':safe,'selected_member':best['name'] if safe else None,'eligible_players':len(best['members']) if safe else None,
                 'ineligible_players':max(0,total_current-len(best['members'])) if safe else None,
                 'club_counts':{normalize_club_name(selected_clubs[e].short or selected_clubs[e].name):best['counts'].get(e,0) for e in selected_clubs},
                 'runner_up':{'name':second['name'],'total':second['total'],'covered':second['covered'],'minimum':second['minimum']} if second else None,
                 'selection_margin':round(margin,3),'current_squad_overlap_ratio':round(ratio,3),
                 'reason':'unique-all-club-current-competition-cohort' if safe else 'competition-cohort-proof-not-decisive'})
    return (best['members'] if safe else None),diag


def apply_competition_eligibility(players:list[dict[str,Any]], eligible_eids:set[int]|None, diag:dict[str,Any]):
    if not eligible_eids:return
    hidden=0
    for p in players:
        try:eid=int(p.get('pid') or p.get('id') or 0)
        except Exception:eid=0
        ok=eid in eligible_eids
        p['competition_eligible']=ok
        p['registration_status']='competition_eligible' if ok else 'not_in_current_competition_cohort'
        p['registration_evidence']={'source':'current_competition_player_cohort_v86','competition_member':diag.get('selected_member'),'eligible':ok}
        if not ok:
            p['available']=False;p['visible']=False;hidden+=1
    diag['players_hidden_from_fantasy']=hidden

def browser_build_payload_from_fs(fingerprint:str, rich_names_json:str, preferred_league:str|None=None):
    dbp=Path('/tmp/game_db.dat'); db=dbp.read_bytes(); dbp.unlink(missing_ok=True)
    fixp=Path('/tmp/fix_man.dat'); fix=fixp.read_bytes(); fixp.unlink(missing_ok=True)
    all_clubs=scan_clubs(db)
    rich_team_names={c.uid+1:normalize_club_name(c.short or c.name) for c in all_clubs.values()}
    raw=[]
    rich_names=json.loads(rich_names_json)
    # Pass 1 uses the broad club aliases only to collect any retained match objects and
    # identity hints. Keep the temp members for a second, league-scoped pass below.
    for i,name in enumerate(rich_names):
        p=Path(f'/tmp/rich_{i}.bin')
        if not p.exists(): continue
        buf=p.read_bytes()
        raw.extend(_rich_extract_member(buf,rich_team_names,name))
    rich_raw=[]; seen=set()
    for m in raw:
        key=(m['home'],m['away'],m['home_score'],m['away_score'],tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))
        if key in seen: continue
        seen.add(key); rich_raw.append(m)
    comp_counts=collections.Counter(m.get('competition') for m in rich_raw if m.get('competition'))
    requested_league=preferred_league if preferred_league in SUPPORTED_LEAGUES else None
    preselect_rich=[m for m in rich_raw if (not requested_league or m.get('competition')==requested_league)]
    expected_names={normalize_club_name(m[k]) for m in preselect_rich for k in ('home','away')} if (requested_league and preselect_rich) else None
    fixtures,fixture_info=select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)
    expected_league=fixture_info['competition']
    rich_raw=[m for m in rich_raw if m.get('competition')==expected_league]
    team_ids={x for f in fixtures for x in (f['home_tid'],f['away_tid'])}
    shift=fixture_info['fixture_to_club_shift']
    selected={tid-shift:all_clubs[tid-shift] for tid in team_ids}

    # IMPORTANT: browser imports previously stopped here and never ran the historical
    # recovery logic that existed in the non-browser payload builder.  This second pass
    # re-decodes the exact same retained members using aliases ONLY from the already-selected
    # current league. It cannot change the selected competition or clubs.
    selected_aliases=selected_rich_team_aliases(selected)
    selected_names={normalize_club_name(c.short or c.name) for c in selected.values()}
    post_raw=[]
    for i,name in enumerate(rich_names):
        p=Path(f'/tmp/rich_{i}.bin')
        if not p.exists(): continue
        buf=p.read_bytes()
        for mm in _rich_extract_member(buf,selected_aliases,name):
            if mm.get('competition')!=fixture_info['competition']: continue
            if normalize_club_name(mm.get('home','')) not in selected_names or normalize_club_name(mm.get('away','')) not in selected_names: continue
            post_raw.append(mm)
    post_recovered=0
    if post_raw:
        combined=[];seen_post=set()
        for mm in list(rich_raw)+post_raw:
            key=(mm.get('competition'),mm.get('home'),mm.get('away'),mm.get('home_score'),mm.get('away_score'),
                 tuple(x.get('player_id') for x in mm.get('home_players',[])),tuple(x.get('player_id') for x in mm.get('away_players',[])))
            if key in seen_post: continue
            seen_post.add(key);combined.append(mm)
        post_recovered=max(0,len(combined)-len(rich_raw));rich_raw=combined

    fixture_name={tid:normalize_club_name(selected[tid-shift].short or selected[tid-shift].name) for tid in team_ids}
    # v87: schedule dates/Gameweeks can change after postponements. The selected league
    # has already passed the exact full double-round-robin shape check, so ordered team
    # pairs are immutable season identities and must own the public fixture_id.
    pair_keys=[(int(f['home_tid']),int(f['away_tid'])) for f in fixtures]
    if len(set(pair_keys))!=len(fixtures):
        raise RuntimeError('Current league fixture identity is not unique by ordered team pair; refusing mutable schedule-based IDs')
    for i,f in enumerate(sorted(fixtures,key=lambda x:(int(x['home_tid']),int(x['away_tid']))),1):
        f['fixture_id']=i
        f['stable_fixture_key']=f"{fixture_info['season_start']}:{int(f['home_tid'])}>{int(f['away_tid'])}"
        f['home']=fixture_name[f['home_tid']];f['away']=fixture_name[f['away_tid']]
    results=scan_completed_results(db,fixtures)

    # Recover senior squads first.  Then, for saves where FM no longer exposes separate rich
    # match members, use each *known played league result* as an anchor in game_db.dat and
    # search locally for the already-validated 214-byte player match-stat records.  The score
    # and both senior-squad overlaps must agree before a historical match is accepted.
    squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)
    competition_eligible_eids,competition_eligibility_diag=select_current_competition_player_cohort(squads,selected)

    # v19: recover current-league match blocks that do not carry a competition-name string.
    member_rich,member_rich_diag=recover_unlabelled_rich_members(
        rich_names,selected,squads,fixtures,shift,fixture_info['competition'])
    if member_rich:
        existing={(normalize_club_name(mm.get('home','')),normalize_club_name(mm.get('away','')),
                   int(mm.get('home_score') or 0),int(mm.get('away_score') or 0),mm.get('date')) for mm in rich_raw}
        for mm in member_rich:
            k=(normalize_club_name(mm.get('home','')),normalize_club_name(mm.get('away','')),
               int(mm.get('home_score') or 0),int(mm.get('away_score') or 0),mm.get('date'))
            if k not in existing:
                rich_raw.append(mm);existing.add(k)
        squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)

    game_db_rich,game_db_rich_diag=recover_game_db_rich_matches(
        db,fixtures,selected,squads,shift,fixture_info['competition'])
    if game_db_rich:
        existing={(normalize_club_name(mm.get('home','')),normalize_club_name(mm.get('away','')),
                   int(mm.get('home_score') or 0),int(mm.get('away_score') or 0)) for mm in rich_raw}
        for mm in game_db_rich:
            k=(normalize_club_name(mm.get('home','')),normalize_club_name(mm.get('away','')),
               int(mm.get('home_score') or 0),int(mm.get('away_score') or 0))
            if k not in existing:
                rich_raw.append(mm);existing.add(k)
        # Re-run squad identity with recovered participation as extra evidence.
        squads,squad_diag=scan_first_team_squads(db,selected,rich_raw)

    for i,_name in enumerate(rich_names):
        Path(f'/tmp/rich_{i}.bin').unlink(missing_ok=True)

    target_eids={p for vals in squads.values() for p in vals}
    for mm in rich_raw:
        for side in ('home_players','away_players'):
            for r in mm.get(side,[]):
                try: target_eids.add(int(r['player_id']))
                except Exception: pass
    people=bind_target_people(db,target_eids)
    players,unresolved,ambiguous=build_players(squads,selected,people,rich_raw)
    apply_competition_eligibility(players,competition_eligible_eids,competition_eligibility_diag)
    pbyeid={int(p['pid']):p for p in players}
    # v86: resolve genuine DEF/MID hybrids from the selected league's own retained
    # match usage BEFORE fantasy scoring.  The decoder self-calibrates FM's match
    # marker/starting-XI slots from unambiguous players in this save, so this is a
    # general observed-role rule rather than a player-name override.
    position_usage_diag=infer_hybrid_positions_from_match_markers(rich_raw,pbyeid) if rich_raw else {'marker_roles':{},'slot_roles':{},'hybrid_players_reclassified':[]}
    rich_matches=join_rich_matches(rich_raw,fixtures,pbyeid) if rich_raw else []
    aggregate_player_history(players,rich_matches)
    availability_diag=_structural_availability_from_fs(players,fixtures)
    # V76: every accepted browser import carries a dated historical boundary.  This is
    # a data cutoff, never the browser clock.  Supabase freezes accepted history behind
    # the previous boundary while current-state fields continue to refresh.
    snapshot_date=availability_diag.get('save_date')
    snapshot_date_source='structural_save_or_fixture_floor_v1' if snapshot_date else None
    if not snapshot_date:
        played_dates=[]
        for _f in fixtures:
            if _f.get('status')!='played' or not _f.get('date'):continue
            try:played_dates.append(dt.date.fromisoformat(str(_f['date'])[:10]))
            except Exception:pass
        if played_dates:
            snapshot_date=max(played_dates).isoformat();snapshot_date_source='latest_played_league_fixture'
    if not snapshot_date:snapshot_date_source='preseason_undated'

    reprice_players(players,fixtures)
    fixtures.sort(key=lambda x:(x['gameweek'],x['date'],x['fixture_id']))
    sched=gameweek_schedule_meta(fixtures,fixture_info['total_gameweeks'])
    current=sched['completed_contiguous']
    table=build_table(fixtures); star_teams=build_star_teams(players,current)
    meta={'fingerprint':fingerprint,'competition':fixture_info['competition'],'competition_code':fixture_info['competition_code'],'competition_fixture_id':fixture_info['competition_id'],'fixture_season_start':fixture_info['season_start'],'fixture_to_club_shift':shift,'fixture_candidates_considered':fixture_info['candidate_groups'],'fixture_exact_candidates':fixture_info['exact_candidate_groups'],'fixture_rich_name_overlap':fixture_info['rich_name_overlap'],'rich_competition_counts':dict(comp_counts),'rich_selected_competition':expected_league,'requested_league':requested_league,'requested_league_honoured':(not requested_league or fixture_info['competition']==requested_league),'league_selection_source':fixture_info.get('selection_mode',('user_preference_locked' if requested_league else 'auto_latest_season')),'current_season_candidates':fixture_info.get('current_season_candidates',[]),'gameweek_relabels':fixture_info['gameweek_relabels'],'calendar_gameweek_model':'deadline-window-v1','calendar_gameweek_windows':fixture_info['calendar_gameweek_windows'],'calendar_reassigned_fixtures':fixture_info['calendar_reassigned_count'],'calendar_reassigned_examples':fixture_info['calendar_reassigned_examples'],'gameweek_fixture_counts':sched['fixture_counts'],'gameweek_played_counts':sched['played_counts'],'double_gameweek_clubs':sched['double_gameweek_clubs'],'blank_gameweek_clubs':sched['blank_gameweek_clubs'],'pricing_model':'fpl-shaped-v65-role-projection-guardrails','snapshot_date':snapshot_date,'snapshot_date_source':snapshot_date_source,'snapshot_date_semantics':'FM data boundary; not browser time','historical_freeze_policy':'append-only-by-snapshot-date-v1','fixture_identity_policy':'ordered-team-pair-v87-stable-across-reschedule','availability_decoder':'structural-v1','injured_players':availability_diag.get('injured_players',0),'suspended_players':availability_diag.get('suspended_players',0),'availability_save_date':availability_diag.get('save_date'),'availability_diagnostics':availability_diag,'observed_position_reclassifications':sum(1 for p in players if p.get('position_source','').startswith('observed_')),'observed_position_usage_diagnostics':position_usage_diag,'competition_eligibility_policy':'current-competition-player-cohort-v86','competition_eligibility_diagnostics':competition_eligibility_diag,'squad_scan_fallbacks':squad_diag['fallbacks'],'squad_scan_missing_club_eids':squad_diag['missing_club_eids'],'squad_rich_augmented_players':squad_diag['rich_augmented_players'],'game_db_rich_matches_recovered':game_db_rich_diag['recovered'],'game_db_rich_recovery_attempted':game_db_rich_diag['attempted'],'game_db_rich_windows_with_stats':game_db_rich_diag['windows_with_stats'],'game_db_rich_candidate_pairs':game_db_rich_diag['candidate_pairs'],'post_selection_rich_matches_recovered':post_recovered,'selected_rich_team_aliases':len(selected_aliases),'unlabelled_rich_members_scanned':member_rich_diag['members_scanned'],'unlabelled_rich_non_retained_members_skipped':member_rich_diag.get('non_retained_members_skipped',0),'unlabelled_rich_non_retained_member_names':member_rich_diag.get('non_retained_member_names',[]),'unlabelled_rich_members_with_stats':member_rich_diag['members_with_stats'],'unlabelled_rich_stat_records':member_rich_diag['stat_records'],'unlabelled_rich_candidate_pairs':member_rich_diag['candidate_pairs'],'unlabelled_rich_matches_recovered':member_rich_diag['matches_recovered'],'unlabelled_rich_cached_candidate_pairs':member_rich_diag.get('cached_candidate_pairs',0),'unlabelled_rich_side_clusters':member_rich_diag.get('side_clusters',0),'unlabelled_rich_labelled_side_clusters':member_rich_diag.get('labelled_side_clusters',0),'unlabelled_rich_strict_seed_matches':member_rich_diag.get('strict_seed_matches',0),'unlabelled_rich_cluster_matches':member_rich_diag.get('cluster_matches',0),'unlabelled_rich_propagation_rounds':member_rich_diag.get('propagation_rounds',0),'unlabelled_rich_propagation_matches':member_rich_diag.get('propagation_matches',0),'unlabelled_rich_cohort_side_labels':member_rich_diag.get('cohort_side_labels',0),'unlabelled_rich_fixture_identity_matches':member_rich_diag.get('fixture_identity_matches',0),'unlabelled_rich_single_side_bridge_matches':member_rich_diag.get('single_side_bridge_matches',0),'unlabelled_rich_identity_rounds':member_rich_diag.get('identity_rounds',0),'unlabelled_rich_ambiguous_seed_player_ids':member_rich_diag.get('ambiguous_seed_player_ids',0),'unlabelled_rich_transfer_conflict_neutralized_players':member_rich_diag.get('transfer_conflict_neutralized_players',0),'unlabelled_rich_adaptive_cluster_edges':member_rich_diag.get('adaptive_cluster_edges',0),'unlabelled_rich_adaptive_cluster_edges_rejected_conflict':member_rich_diag.get('adaptive_cluster_edges_rejected_conflict',0),'unlabelled_rich_unmatched_cached_pairs':member_rich_diag.get('unmatched_cached_pairs',0),'unlabelled_rich_confirmed_cohort_side_labels':member_rich_diag.get('confirmed_cohort_side_labels',0),'unlabelled_rich_confirmed_cohort_conflicts_rejected':member_rich_diag.get('confirmed_cohort_conflicts_rejected',0),'unlabelled_rich_confirmed_cohort_fixture_matches':member_rich_diag.get('confirmed_cohort_fixture_matches',0),'unlabelled_rich_confirmed_roster_fixture_matches':member_rich_diag.get('confirmed_roster_fixture_matches',0),'unlabelled_rich_confirmed_roster_side_uses':member_rich_diag.get('confirmed_roster_side_uses',0),'unlabelled_rich_confirmed_roster_conflicts_rejected':member_rich_diag.get('confirmed_roster_conflicts_rejected',0),'unlabelled_rich_confirmed_roster_one_side_fixture_matches':member_rich_diag.get('confirmed_roster_one_side_fixture_matches',0),'unlabelled_rich_confirmed_roster_one_side_side_uses':member_rich_diag.get('confirmed_roster_one_side_side_uses',0),'unlabelled_rich_confirmed_roster_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_roster_one_side_ambiguities_rejected',0),'unlabelled_rich_global_constraint_unique_components':member_rich_diag.get('global_constraint_unique_components',0),'unlabelled_rich_global_constraint_fixture_matches':member_rich_diag.get('global_constraint_fixture_matches',0),'unlabelled_rich_global_constraint_oversized_components_rejected':member_rich_diag.get('global_constraint_oversized_components_rejected',0),'unlabelled_rich_global_constraint_unbalanced_components_rejected':member_rich_diag.get('global_constraint_unbalanced_components_rejected',0),'unlabelled_rich_global_constraint_no_perfect_match_rejected':member_rich_diag.get('global_constraint_no_perfect_match_rejected',0),'unlabelled_rich_global_constraint_nonunique_components_rejected':member_rich_diag.get('global_constraint_nonunique_components_rejected',0),'unlabelled_rich_missing_fixture_fallback_matches':member_rich_diag.get('missing_fixture_fallback_matches',0),'clubs':fixture_info['team_count'],'team_count':fixture_info['team_count'],'total_gameweeks':fixture_info['total_gameweeks'],'fixtures':len(fixtures),'played_results':len(results),'rich_matches':len(rich_matches),'players':len(players),'unresolved_squad_eids':unresolved,'ambiguous_memberships':ambiguous,'fully_completed_gameweeks':sched['fully_completed'],'latest_gameweek_with_result':sched['latest_result'],'completed_gameweek':current,'current_gameweek':min(fixture_info['total_gameweeks'],current+1) if current<fixture_info['total_gameweeks'] else fixture_info['total_gameweeks'],'next_gameweek':min(fixture_info['total_gameweeks'],current+1) if current<fixture_info['total_gameweeks'] else fixture_info['total_gameweeks'],'hidden_unresolved':len(unresolved),'scoring_note':'Bonus uses an FM-derived BPS proxy; MID/FWD DEFCON uses FM possession-won as the recovery-equivalent.'}
    clubs_payload=[{'eid':c.eid,'uid':c.uid,'name':c.name,'short_name':normalize_club_name(c.short)} for c in sorted(selected.values(),key=lambda c:c.name)]
    return json.dumps({'meta':meta,'clubs':clubs_payload,'players':players,'fixtures':fixtures,'matches':rich_matches,'table':table,'star_teams':star_teams},ensure_ascii=False)

