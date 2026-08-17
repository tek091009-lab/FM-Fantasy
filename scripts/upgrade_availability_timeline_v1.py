from pathlib import Path
import base64,gzip

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')

old="""    save_date=None

    ip=Path('/tmp/injury_manager.dat')"""
new="""    save_date=None
    # The injury member itself does not expose a trustworthy global save-date field.  The
    # latest PLAYED league fixture is a hard lower bound for the current save timeline and
    # must win over older dates found inside injury history tables.  This prevents an old
    # September injury window from remaining active in an October save.
    fixture_dates=[]
    for f in fixtures:
        if f.get('status')!='played' or not f.get('date'):continue
        try:fixture_dates.append(dt.date.fromisoformat(str(f['date'])[:10]))
        except Exception:pass
    fixture_floor=max(fixture_dates) if fixture_dates else None

    ip=Path('/tmp/injury_manager.dat')"""
if old not in html: raise SystemExit('availability save-date anchor missing')
html=html.replace(old,new,1)

old="""                            if past:save_date=max(past)
                            if save_date is None and future:save_date=min(future)
                            seen=set();recs=0"""
new="""                            if past:save_date=max(past)
                            if save_date is None and future:save_date=min(future)
                            if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor
                            seen=set();recs=0"""
if old not in html: raise SystemExit('injury table timeline anchor missing')
html=html.replace(old,new,1)

old="""                                if not full or not save_date or full<save_date:continue"""
new="""                                if not full or not save_date or full<=save_date:continue"""
if old not in html: raise SystemExit('injury expiry comparison anchor missing')
html=html.replace(old,new,1)

old="""    if save_date is None:
        ds=[]
        for f in fixtures:
            if f.get('status')!='played' or not f.get('date'):continue
            try:ds.append(dt.date.fromisoformat(str(f['date'])[:10]))
            except Exception:pass
        if ds:save_date=max(ds)"""
new="""    if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor"""
if old not in html: raise SystemExit('availability fallback timeline anchor missing')
html=html.replace(old,new,1)

# Mark this importer build explicitly so debug exports prove which availability decoder ran.
old="""    out={'decoder':'structural-v1','save_date':None,'injury_records':0,'injured_players':0,"""
new="""    out={'decoder':'structural-v2-fixture-floor','save_date':None,'injury_records':0,'injured_players':0,"""
if old not in html: raise SystemExit('availability decoder marker anchor missing')
html=html.replace(old,new,1)

for token in ['structural-v2-fixture-floor','fixture_floor','full<=save_date']:
    if token not in html: raise SystemExit('missing '+token)

out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out: raise SystemExit('repack mismatch')
print('structural availability timeline v2 applied')
