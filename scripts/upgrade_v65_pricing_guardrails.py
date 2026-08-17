from pathlib import Path
import base64,gzip,re

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

marker='\ndef scan_completed_results(db:bytes,fixtures:list[dict[str,Any]]):\n'
if marker not in py: raise SystemExit('scan_completed_results marker missing')

patch=r'''
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
'''

py=py.replace(marker,'\n'+patch+marker,1)
py=py.replace("'pricing_model':'fpl-shaped-v64-role-evidence-aware'","'pricing_model':'fpl-shaped-v65-role-projection-guardrails'",2)
py=py.replace('FPL-shaped v6.4 role-evidence-aware launch pricing.','FPL-shaped v6.5 role-projection launch pricing.',1)
for token in ['v65_established_absence','v65_new_arrival_projection','projected_arrival_price','fpl-shaped-v65-role-projection-guardrails']:
    if token not in py: raise SystemExit('missing '+token)
compile(py,'fm_importer.py','exec')

b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+b64+html[m.end(1):]
html=html.replace('v24-role-evidence-rich-recovery','v25-pricing-guardrails')
out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out:raise SystemExit('repack mismatch')
print('v6.5 pricing guardrails applied')
