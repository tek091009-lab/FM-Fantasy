from pathlib import Path
import base64,gzip,re

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def unpack():
    html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m: raise RuntimeError('FM_PY_SOURCE_B64 missing')
    return html,m,base64.b64decode(m.group(1)).decode('utf-8')

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')
    if ''.join(p.read_text().strip() for p in PARTS)!=packed: raise RuntimeError('repack mismatch')

def main():
    html,m,py=unpack()

    # Availability has to exist before launch pricing. v6.1 did this backwards, so an
    # injured zero-minute player was indistinguishable from an unused squad player.
    old="""    aggregate_player_history(players,rich_matches)\n    reprice_players(players,fixtures)\n    availability_diag=_structural_availability_from_fs(players,fixtures)\n"""
    new="""    aggregate_player_history(players,rich_matches)\n    availability_diag=_structural_availability_from_fs(players,fixtures)\n    reprice_players(players,fixtures)\n"""
    n=py.count(old)
    if n<2: raise RuntimeError(f'expected both payload builders to have old availability order, got {n}')
    py=py.replace(old,new)

    # Remove the CA-over-actual-usage escape hatch. It was allowing a zero-minute high-CA
    # reserve to bypass all backup caps and become an £8m+ fantasy asset.
    pat=re.compile(r"(?P<indent>\s*)active=group_active\.get\(\(p\['club'\],p\['pos'\]\)\)\n(?P=indent)active_ca=float\(active\.get\('ca'\) or 0\) if active else 0\.0\n(?P=indent)expected_exception=bool\(games>=2 and mins==0 and d>=0\.78 and q>=0\.78 and ca>=active_ca\+4\)")
    py,n=pat.subn(lambda x: x.group('indent')+"active=group_active.get((p['club'],p['pos']))\n"+x.group('indent')+"# Availability is decoded before pricing in v6.2. Only a verified current absence\n"+x.group('indent')+"# may excuse zero minutes; reputation/CA alone can never bypass usage caps.\n"+x.group('indent')+"absence_excused=bool(p.get('injured') or p.get('suspended') or p.get('injury_status')=='injured' or p.get('suspension_status')=='suspended')\n"+x.group('indent')+"expected_exception=absence_excused",py)
    if n!=1: raise RuntimeError(f'expected_exception definition patch count {n}')

    # An excused zero-minute player should keep a sensible role-based launch valuation,
    # but should not become premium solely because FM rates them highly.
    old_exc="""        if expected_exception:\n            nailed=max(0.68,d*0.80)\n"""
    new_exc="""        if expected_exception:\n            nailed=max(0.48,min(0.72,0.62*d+0.10*q))\n"""
    if old_exc not in py: raise RuntimeError('expected-exception nailedness block missing')
    py=py.replace(old_exc,new_exc,1)

    # Add explicit caps for players with a verified current absence and no season minutes.
    # They are not £4m basement fodder, but neither are they priced as nailed premiums.
    needle="""            if p.get('minutes',0)==0 and c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and not c['zero_minute_exception']:\n                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos])\n            elif pos=='GK':\n"""
    replacement="""            if p.get('minutes',0)==0 and c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and not c['zero_minute_exception']:\n                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos])\n            elif p.get('minutes',0)==0 and c['zero_minute_exception']:\n                raw=min(raw,{'GK':5.0,'DEF':5.5,'MID':7.0,'FWD':7.5}[pos])\n            elif pos=='GK':\n"""
    if needle not in py: raise RuntimeError('v6.1 distribution zero-minute block missing')
    py=py.replace(needle,replacement,1)

    # Observed match role should resolve genuine hybrids even when FM rates the secondary
    # position just below 'natural'. Keep the marker mapping self-calibrated and conservative.
    py=py.replace("if not p or not marker or marker==4:continue\n                strengths=_position_strengths(p)","if not p or not marker or marker==4 or float(r.get('minutes') or 0)<=0:continue\n                strengths=_position_strengths(p)",1)
    py=py.replace("if total<12:continue\n        role,n=c.most_common(1)[0]\n        if n/total>=0.75:marker_roles[marker]=role","if total<8:continue\n        role,n=c.most_common(1)[0]\n        if n/total>=0.80:marker_roles[marker]=role",1)
    old_hybrid="""        st=_position_strengths(p)\n        if st['DEF']<15 or st['MID']<15:continue\n        dm=c['DEF']+c['MID']\n        if dm<2:continue\n        if c['MID']/dm>=0.67 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage';changed.append(eid)\n        elif c['DEF']/dm>=0.67 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage';changed.append(eid)\n"""
    new_hybrid="""        st=_position_strengths(p)\n        # FM's 15+ 'natural' cutoff is too strict for fantasy classification: a player can\n        # be a genuine DEF/MID hybrid at 12-14 in one band yet be deployed there every week.\n        if max(st['DEF'],st['MID'])<15 or min(st['DEF'],st['MID'])<12:continue\n        dm=c['DEF']+c['MID']\n        if dm<3:continue\n        if c['MID']/dm>=0.75 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage';changed.append(eid)\n        elif c['DEF']/dm>=0.75 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage';changed.append(eid)\n"""
    if old_hybrid not in py: raise RuntimeError('hybrid classification block missing')
    py=py.replace(old_hybrid,new_hybrid,1)

    py=py.replace('FPL-shaped v6.1 launch pricing.','FPL-shaped v6.2 launch pricing.',1)
    py=py.replace("'pricing_model':'fpl-shaped-v61-tiered-distribution'","'pricing_model':'fpl-shaped-v62-availability-aware'",2)

    # Safety checks for the regressions fixed here.
    if py.count('availability_diag=_structural_availability_from_fs(players,fixtures)')<2: raise RuntimeError('availability calls missing')
    if 'ca>=active_ca+4' in py: raise RuntimeError('CA backup bypass still present')
    if "reprice_players(players,fixtures)\n    availability_diag=" in py: raise RuntimeError('pricing still precedes availability')
    if "def fixture_key(f):\n        fid=fixture_key(f)" in py: raise RuntimeError('recursive fixture_key regression returned')
    compile(py,'fm_importer.py','exec')

    b64=base64.b64encode(py.encode()).decode()
    html=html[:m.start(1)]+b64+html[m.end(1):]
    repack(html)
    print('v6.2: availability-aware pricing + usage-led hybrid position classification applied')

if __name__=='__main__': main()
