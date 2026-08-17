from pathlib import Path
import base64,gzip,re

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

# Role first: actual usage is a hard pricing constraint. Quality/CA/team strength may
# separate players only inside the band permitted by their observed role. New arrivals
# are judged only on matches they were actually at the current club for.
needle="""            raw_scores[p['id']]=raw
            c['distribution_cap']=round(raw,2)
"""
replacement="""            obs=max(0,int(c.get('observed_matches') or 0))
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
            absence_excused=bool(p.get('injured') or p.get('suspended') or p.get('injury_status')=='injured' or p.get('suspension_status')=='suspended')
            c['observed_minute_share']=round(minute_share,3)
            if obs>=2 and not absence_excused:
                if minute_share<0.20:
                    role='backup';role_cap={'GK':4.0,'DEF':4.5,'MID':5.0,'FWD':5.5}[pos]
                elif minute_share<0.45:
                    role='rotation';role_cap={'GK':4.5,'DEF':5.0,'MID':6.0,'FWD':6.5}[pos]
                elif minute_share<0.70:
                    role='squad';role_cap={'GK':5.0,'DEF':5.5,'MID':7.0,'FWD':7.5}[pos]
                else:
                    role='starter';role_cap={'GK':6.0,'DEF':8.0,'MID':15.0,'FWD':14.0}[pos]
                raw=min(raw,role_cap)
                c['usage_role']=role;c['usage_role_cap']=role_cap
            elif c.get('new_arrival'):
                c['usage_role']='new_arrival_unproven'
            elif absence_excused:
                c['usage_role']='absence_excused'
            else:
                c['usage_role']='unproven'
            raw_scores[p['id']]=raw
            c['distribution_cap']=round(raw,2)
"""
if needle not in py: raise SystemExit('pricing writeback marker missing')
py=py.replace(needle,replacement,1)

# Same club + same fantasy position: if one available player is clearly the established
# starter by usage, a materially lower-usage alternative cannot cost more than him.
# Newly arrived players are excluded until they have >=2 eligible club matches.
anchor="""    # Round to FPL-style half-million prices.
"""
guard="""    by_club_pos={}
    for p in players:by_club_pos.setdefault((p.get('club'),p.get('pos')),[]).append(p)
    for (_club,_pos),arr in by_club_pos.items():
        def _usage(x):
            c=x.get('price_context') or {};obs=max(0,int(c.get('current_club_observed_matches',c.get('observed_matches') or 0)));mins=max(0.0,float(x.get('minutes') or 0))
            return min(1.0,mins/max(1.0,obs*90.0)) if obs else 0.0
        available=[x for x in arr if not (x.get('injured') or x.get('suspended') or x.get('injury_status')=='injured' or x.get('suspension_status')=='suspended')]
        established=[x for x in available if not (x.get('price_context') or {}).get('new_arrival')]
        established.sort(key=_usage,reverse=True)
        if not established:continue
        leader=established[0];lu=_usage(leader);leader_raw=raw_scores.get(leader['id'],0.0)
        for p in established[1:]:
            u=_usage(p)
            if lu>=0.60 and lu-u>=0.20:
                floor={'GK':4.0,'DEF':4.0,'MID':4.5,'FWD':4.5}[p['pos']]
                cap=max(floor,leader_raw-0.5)
                if raw_scores.get(p['id'],0.0)>cap:
                    raw_scores[p['id']]=cap
                    c=p.get('price_context') or {};c['depth_chart_cap']=round(cap,2);c['depth_chart_leader']=leader.get('id');c['usage_role']='rotation_behind_starter'

"""
if anchor not in py: raise SystemExit('rounding marker missing')
py=py.replace(anchor,guard+anchor,1)

# Repeated actual deployment overrides nominal DEF/MID eligibility. This removes the old
# secondary-position >=12 gate that kept clear midfield deployments coded as defenders.
old="""        st=_position_strengths(p)
        if max(st['DEF'],st['MID'])<15 or min(st['DEF'],st['MID'])<12:continue
        dm=c['DEF']+c['MID']
        if dm<3:continue
        if c['MID']/dm>=0.75 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage';changed.append(eid)
        elif c['DEF']/dm>=0.75 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage';changed.append(eid)
"""
new="""        st=_position_strengths(p)
        if max(st['DEF'],st['MID'])<15:continue
        dm=c['DEF']+c['MID']
        if dm<2:continue
        if c['MID']/dm>=0.80 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage_v63';changed.append(eid)
        elif c['DEF']/dm>=0.80 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage_v63';changed.append(eid)
"""
if old not in py: raise SystemExit('v62 hybrid block missing')
py=py.replace(old,new,1)

py=py.replace("'pricing_model':'fpl-shaped-v62-availability-aware'","'pricing_model':'fpl-shaped-v63-role-first-transfer-aware'")
py=py.replace('FPL-shaped v6.2 launch pricing.','FPL-shaped v6.3 role-first transfer-aware launch pricing.')
for req in ['observed_minute_share','rotation_behind_starter','observed_midfield_usage_v63','usage_role_cap','new_arrival_unproven','current_club_observed_matches']:
    if req not in py:raise SystemExit('missing '+req)
compile(py,'fm_importer.py','exec')

b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+b64+html[m.end(1):]
packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(packed)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(packed[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=packed:raise SystemExit('repack mismatch')
print('v6.3 role-first transfer-aware pricing + observed deployment classification applied')
