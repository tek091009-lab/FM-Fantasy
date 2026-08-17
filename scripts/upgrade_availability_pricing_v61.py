from pathlib import Path
import base64,gzip,re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
parts=[root/'app'/f'part{i:02d}' for i in range(17)]+[root/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('FM python source missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

old_susp="""                games=None
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
"""
new_susp="""                # A row in discipline.dat is itself evidence of an active FM ban.
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
"""
if old_susp not in py: raise SystemExit('suspension decoder block missing')
py=py.replace(old_susp,new_susp,1)

old_pricing='''    # v6: raw model still decides who is better, but positional rank controls scarcity.
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
new_pricing='''    # v6.1: the raw FM-derived model decides ordering; positional rank then controls
    # the shape of the market. Premium prices are deliberately scarce and the middle/
    # value tiers step down rather than bunching at one high cap.
    ranked={pos:sorted((p for p in players if p['pos']==pos),key=lambda p:raw_scores[p['id']],reverse=True) for pos in ('GK','DEF','MID','FWD')}
    for pos,arr in ranked.items():
        for i,p in enumerate(arr):
            raw=raw_scores[p['id']];c=p['price_context'];att=float(c['attack_profile']);team=float(c['team_strength']);nailed=float(c['nailedness']);q=float(c['quality'])
            c['position_price_rank']=i+1
            if p.get('minutes',0)==0 and c['observed_matches']>=2 and club_usage_coverage.get(p.get('club'),False) and not c['zero_minute_exception']:
                raw=min(raw,{'GK':4.0,'DEF':4.5,'MID':4.5,'FWD':5.0}[pos])
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
            raw_scores[p['id']]=raw
            c['distribution_cap']=round(raw,2)
'''
if old_pricing not in py: raise SystemExit('v6 pricing block missing')
py=py.replace(old_pricing,new_pricing,1)
py=py.replace('fpl-shaped-v6-position-distribution-calibrated','fpl-shaped-v61-tiered-distribution')
py=py.replace('FPL-shaped v6 launch pricing.','FPL-shaped v6.1 launch pricing.')
compile(py,'fm_importer.py','exec')

newb64=base64.b64encode(py.encode()).decode(); html=html[:m.start(1)]+newb64+html[m.end(1):]

start=html.find('function fmInferActiveSuspensions(payload){')
end=html.find('\nfunction fmInferActiveInjuries(payload){',start)
if start<0 or end<0: raise SystemExit('suspension UI function missing')
new_js="""function fmInferActiveSuspensions(payload){const out=[];for(const p of payload?.players||[]){const explicit=Number(p.suspension_remaining??p.suspension_games_remaining??p.ban_games_remaining??0),status=String(p.suspension_status??'').toLowerCase(),until=p.banned_until??p.suspension_until??null;if(explicit>0||/(suspend|ban|unavailable)/.test(status)||until){const bits=['Suspended'];if(explicit>0)bits.push(`${explicit} league match${explicit===1?'':'es'} remaining`);else if(until)bits.push(`until ${fmFmtStatusDate(until)}`);const reason=String(p.suspension_detail??'').trim();if(reason&&!/^active fm suspension$/i.test(reason))bits.push(reason);out.push({pid:String(p.pid),name:playerName(p),club:p.club,pos:p.pos,detail:bits.join(' · ')});continue}const hist=[...(p.history||[])].filter(h=>h.date).sort((a,b)=>String(a.date).localeCompare(String(b.date)));if(!hist.length)continue;const incidents=[];for(const h of hist){const rc=Number(h.red_cards??h.rc??0),yc=Number(h.yellow_cards??h.yc??0);if(rc>0)incidents.push({date:String(h.date),ban:1,reason:yc>=2?'second-yellow red':'red card'});}let yellows=[];for(const h of hist){const yc=Number(h.yellow_cards??h.yc??0);for(let i=0;i<yc;i++)yellows.push(String(h.date));}for(const [threshold,ban] of [[5,1],[10,2],[15,3]])if(yellows.length>=threshold)incidents.push({date:yellows[threshold-1],ban,reason:`${threshold} yellow cards`});incidents.sort((a,b)=>String(b.date).localeCompare(String(a.date)));for(const inc of incidents){const served=fmClubPlayedAfter(payload,p.club,inc.date),remaining=Math.max(0,Number(inc.ban)-served);if(remaining>0){out.push({pid:String(p.pid),name:playerName(p),club:p.club,pos:p.pos,detail:`Suspended · ${remaining} league match${remaining===1?'':'es'} remaining · ${inc.reason}`});break}}}return out}"""
html=html[:start]+new_js+html[end:]

packed=base64.b64encode(gzip.compress(html.encode(),9)).decode(); n=len(parts); size=(len(packed)+n-1)//n
chunks=[packed[i*size:(i+1)*size] for i in range(n)]
for p,c in zip(parts,chunks):p.write_text(c)
print('v6.1 patched',len(py),len(html),len(packed))
