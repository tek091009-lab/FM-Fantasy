from pathlib import Path
import base64, gzip, re

PARTS=[Path('app')/f'part{i:02d}' for i in range(17)]+[Path('app')/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# ---- Structural FM availability decoder ------------------------------------
marker="def _clamp(x:float,a:float=0.0,b:float=1.0)->float:return max(a,min(b,x))\n"
helper=r'''

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
    out={'decoder':'structural-v1','save_date':None,'injury_records':0,'injured_players':0,
         'suspension_records':0,'suspended_players':0,'injury_source':'injury_manager.dat',
         'suspension_source':'discipline.dat'}
    save_date=None

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
                            seen=set();recs=0
                            for i in range(c2):
                                o=s2+i*14
                                earliest=_fm_struct_date(u32(b,o+1));full=_fm_struct_date(u32(b,o+5));eid=u32(b,o+9)
                                if not full or not save_date or full<save_date:continue
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

    if save_date is None:
        ds=[]
        for f in fixtures:
            if f.get('status')!='played' or not f.get('date'):continue
            try:ds.append(dt.date.fromisoformat(str(f['date'])[:10]))
            except Exception:pass
        if ds:save_date=max(ds)
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
                if not p or not expiry or (save_date and expiry<save_date):continue
                games=None
                if save_date and p.get('club'):
                    upcoming=set()
                    for f in fixtures:
                        try:fd=dt.date.fromisoformat(str(f.get('date') or '')[:10])
                        except Exception:continue
                        if fd<=save_date or fd>expiry:continue
                        if p.get('club') in (f.get('home'),f.get('away')):upcoming.add(fd)
                    if upcoming:games=max(1,len(upcoming))
                p['suspension_status']='suspended';p['suspended']=True;p['banned_until']=expiry.isoformat()
                p['suspension_games_remaining']=games;p['suspension_remaining']=games
                p['suspension_detail']='Active FM suspension'
                p['suspension_evidence_structural']={'source':'discipline.dat/active-ban-v1','expiry':expiry.isoformat(),'games_remaining':games}
                seen.add(int(eid));recs+=1
            out['suspension_records']=recs;out['suspended_players']=len(seen)
        except Exception as e:out['suspension_error']=str(e)[:220]
    return out
'''
if '_structural_availability_from_fs' not in py:
    if marker not in py:raise SystemExit('availability insertion marker missing')
    py=py.replace(marker,marker+helper,1)

# ---- General FPL-shaped launch price distribution ---------------------------
start=py.find("    defs=sorted((p for p in players if p['pos']=='DEF'),key=lambda p:raw_scores[p['id']],reverse=True)")
end=py.find("\n    for p in players:\n        c=p['price_context'];basement=",start)
if start<0 or end<0:raise SystemExit('pricing distribution block not found')
pricing=r'''    # v6: raw model still decides who is better, but positional rank controls scarcity.
    # This prevents a strong league/team from accidentally creating dozens of "premium" assets.
    ranked={pos:sorted((p for p in players if p['pos']==pos),key=lambda p:raw_scores[p['id']],reverse=True) for pos in ('GK','DEF','MID','FWD')}
    for pos,arr in ranked.items():
        for i,p in enumerate(arr):
            raw=raw_scores[p['id']];c=p['price_context'];att=float(c['attack_profile']);team=float(c['team_strength']);nailed=float(c['nailedness']);q=float(c['quality'])
            c['position_price_rank']=i+1
            if p.get('minutes',0)==0 and c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and not c['zero_minute_exception']:
                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos])
            elif pos=='GK':
                # Only the very best keepers sit above the normal starter band.
                cap=5.5 if i<2 else 5.0 if i<8 else 4.5
                raw=min(raw,cap)
            elif pos=='DEF':
                # £6.0m+ is premium. A low-attacking defender needs elite team/nailedness
                # and a top-three rank even to reach £6.0m.
                if att<0.42:
                    cap=6.0 if i<3 and team>=0.78 and nailed>=0.84 else 5.5
                    raw=min(raw,cap)
                elif i==0 and team>=0.70 and att>=0.58:
                    raw=min(7.5,raw+0.35)
                elif i<3 and team>=0.58:
                    raw=min(raw,6.5)
                elif i<6:
                    raw=min(raw,6.0)
                else:
                    raw=min(raw,5.5)
            elif pos=='MID':
                if att<0.34:
                    # Defensive midfielders may be excellent footballers without being
                    # premium fantasy assets.
                    raw=min(raw,6.0 if i<8 and q>=0.88 and team>=0.62 and nailed>=0.80 else 5.5)
                else:
                    cap=15.0 if i<2 else 12.5 if i<5 else 10.5 if i<10 else 9.0 if i<20 else 8.0 if i<40 else 7.0
                    raw=min(raw,cap)
            else: # FWD
                cap=14.0 if i<2 else 11.5 if i<5 else 9.5 if i<10 else 8.0 if i<20 else 7.0
                raw=min(raw,cap)
            raw_scores[p['id']]=raw
            c['distribution_cap']=round(raw,2)
'''
py=py[:start]+pricing+py[end:]
py=py.replace("'pricing_model':'fpl-shaped-v5b-launch-role-coverage-safe'","'pricing_model':'fpl-shaped-v6-position-distribution-calibrated'")
py=py.replace('"""FPL-shaped v5 launch pricing.','"""FPL-shaped v6 launch pricing.')

# Run availability after pricing/history has been built in both payload paths.
needle="aggregate_player_history(players,rich_matches)\n    reprice_players(players,fixtures)"
repl="aggregate_player_history(players,rich_matches)\n    reprice_players(players,fixtures)\n    availability_diag=_structural_availability_from_fs(players,fixtures)"
py=py.replace(needle,repl)

# Surface diagnostics in metadata without making successful import depend on availability.
meta_key="'pricing_model':'fpl-shaped-v6-position-distribution-calibrated','observed_position_reclassifications'"
meta_repl="'pricing_model':'fpl-shaped-v6-position-distribution-calibrated','availability_decoder':'structural-v1','injured_players':availability_diag.get('injured_players',0),'suspended_players':availability_diag.get('suspended_players',0),'availability_save_date':availability_diag.get('save_date'),'availability_diagnostics':availability_diag,'observed_position_reclassifications'"
py=py.replace(meta_key,meta_repl)

# Replace embedded Python.
newb64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+newb64+html[m.end(1):]

# Browser importer must retain the dedicated FM members long enough for Python to decode them.
old="const fixM=by.get('fix_man.dat'),dbM=by.get('game_db.dat');if(!fixM||!dbM)throw new Error('Required FM database/fixture members were not found in this save.');"
new="const fixM=by.get('fix_man.dat'),dbM=by.get('game_db.dat'),injM=by.get('injury_manager.dat'),discM=by.get('discipline.dat');if(!fixM||!dbM)throw new Error('Required FM database/fixture members were not found in this save.');"
if old in html:html=html.replace(old,new,1)
elif "injM=by.get('injury_manager.dat')" not in html:raise SystemExit('archive member declaration marker missing')
old2="report('Extracting players, clubs and results…',63);let db=get(dbM);py.FS.writeFile('/tmp/game_db.dat',db);db=null;b=null;rawBuffer=null;report('Players, clubs and results extracted.',69);"
new2="report('Extracting players, clubs and results…',63);let db=get(dbM);py.FS.writeFile('/tmp/game_db.dat',db);db=null;if(injM){let ib=get(injM);py.FS.writeFile('/tmp/injury_manager.dat',ib);ib=null}if(discM){let sb=get(discM);py.FS.writeFile('/tmp/discipline.dat',sb);sb=null}b=null;rawBuffer=null;report('Players, clubs, results and availability extracted.',69);"
if old2 in html:html=html.replace(old2,new2,1)
elif "py.FS.writeFile('/tmp/injury_manager.dat'" not in html:raise SystemExit('archive availability extraction marker missing')

packed=base64.b64encode(gzip.compress(html.encode(),9)).decode()
n=len(PARTS);size=(len(packed)+n-1)//n
chunks=[packed[i*size:(i+1)*size] for i in range(n)]
for p,c in zip(PARTS,chunks):p.write_text(c)
print('patched',len(py),'python bytes;',len(html),'html bytes;',len(packed),'packed chars')
