from pathlib import Path
import base64,gzip,re

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')

m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('embedded FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

if 'structural-v2-fixture-floor' not in py:
    old="""    save_date=None

    ip=Path('/tmp/injury_manager.dat')"""
    new="""    save_date=None
    # Dates inside injury_manager.dat describe injury windows, not necessarily the current
    # save date. The latest played league fixture is a hard lower bound for the save timeline.
    # Never allow an older injury-table date to move the availability clock backwards.
    fixture_dates=[]
    for f in fixtures:
        if f.get('status')!='played' or not f.get('date'):continue
        try:fixture_dates.append(dt.date.fromisoformat(str(f['date'])[:10]))
        except Exception:pass
    fixture_floor=max(fixture_dates) if fixture_dates else None

    ip=Path('/tmp/injury_manager.dat')"""
    if old not in py: raise SystemExit('availability save-date anchor missing')
    py=py.replace(old,new,1)

    old="""                            if past:save_date=max(past)
                            if save_date is None and future:save_date=min(future)
                            seen=set();recs=0"""
    new="""                            if past:save_date=max(past)
                            if save_date is None and future:save_date=min(future)
                            if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor
                            seen=set();recs=0"""
    if old not in py: raise SystemExit('injury table timeline anchor missing')
    py=py.replace(old,new,1)

    old="""                                if not full or not save_date or full<save_date:continue"""
    new="""                                if not full or not save_date or full<=save_date:continue"""
    if old not in py: raise SystemExit('injury expiry comparison anchor missing')
    py=py.replace(old,new,1)

    old="""    if save_date is None:
        ds=[]
        for f in fixtures:
            if f.get('status')!='played' or not f.get('date'):continue
            try:ds.append(dt.date.fromisoformat(str(f['date'])[:10]))
            except Exception:pass
        if ds:save_date=max(ds)"""
    new="""    if fixture_floor and (save_date is None or fixture_floor>save_date):save_date=fixture_floor"""
    if old not in py: raise SystemExit('availability fallback timeline anchor missing')
    py=py.replace(old,new,1)

    old="""    out={'decoder':'structural-v1','save_date':None,'injury_records':0,'injured_players':0,"""
    new="""    out={'decoder':'structural-v2-fixture-floor','save_date':None,'injury_records':0,'injured_players':0,"""
    if old not in py: raise SystemExit('availability decoder marker anchor missing')
    py=py.replace(old,new,1)

    # Expiry equal to the availability clock is no longer future availability.
    old="""                if not p or not expiry or (save_date and expiry<save_date):continue"""
    new="""                if not p or not expiry or (save_date and expiry<=save_date):continue"""
    if old not in py: raise SystemExit('suspension expiry comparison anchor missing')
    py=py.replace(old,new,1)

for token in ['structural-v2-fixture-floor','fixture_floor','full<=save_date','expiry<=save_date']:
    if token not in py: raise SystemExit('missing '+token)

py_b64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+py_b64+html[m.end(1):]

out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out: raise SystemExit('repack mismatch')
print('structural availability timeline v2 applied to embedded Python importer')
