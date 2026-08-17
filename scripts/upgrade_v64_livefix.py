from pathlib import Path
import base64,gzip,re

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise SystemExit('FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

# -----------------------------------------------------------------------------
# 1) Pricing: an injury/suspension is not, by itself, proof of a starting role.
# Preserve an absent zero-minute player only when quality/depth evidence says they
# are an established senior option. Low-quality injured reserves remain backups.
# ----------------------------------------------------------------------------
old="""        absence_excused=bool(p.get('injured') or p.get('suspended') or p.get('injury_status')=='injured' or p.get('suspension_status')=='suspended')
        expected_exception=absence_excused
"""
new="""        _status_text=' '.join(str(p.get(k) or '').lower() for k in ('injury_status','suspension_status','status'))
        current_unavailable=bool(p.get('injured') or p.get('suspended') or 'injur' in _status_text or 'suspend' in _status_text or p.get('injury_return_date') or p.get('injury_evidence'))
        # Missing games are excused only for a ZERO-MINUTE player who has real senior-role
        # evidence. This prevents a low-CA injured reserve being treated as a nailed starter.
        established_absence=bool(current_unavailable and mins<=0 and (q>=0.55 or d>=0.55 or ca>=130))
        absence_excused=established_absence
        expected_exception=established_absence
"""
if old not in py: raise SystemExit('pricing absence marker missing')
py=py.replace(old,new,1)

# v6.3 role-band block has its own absence test; make it use the established split too.
old2="""            absence_excused=bool(p.get('injured') or p.get('suspended') or p.get('injury_status')=='injured' or p.get('suspension_status')=='suspended')
            c['observed_minute_share']=round(minute_share,3)
"""
new2="""            _status_text=' '.join(str(p.get(k) or '').lower() for k in ('injury_status','suspension_status','status'))
            current_unavailable=bool(p.get('injured') or p.get('suspended') or 'injur' in _status_text or 'suspend' in _status_text or p.get('injury_return_date') or p.get('injury_evidence'))
            q0=float(c.get('quality') or 0);d0=float(c.get('depth_score') or 0);ca0=float(p.get('ca') or 0)
            absence_excused=bool(current_unavailable and mins<=0 and (q0>=0.55 or d0>=0.55 or ca0>=130))
            c['current_unavailable']=current_unavailable
            c['established_absence']=absence_excused
            c['observed_minute_share']=round(minute_share,3)
"""
if old2 not in py: raise SystemExit('v63 role absence marker missing')
py=py.replace(old2,new2,1)

# Established zero-minute absences need a sensible floor as well as a cap.
old3="""            elif p.get('minutes',0)==0 and c['zero_minute_exception']:
                raw=min(raw,{'GK':5.0,'DEF':5.5,'MID':7.0,'FWD':7.5}[pos])
"""
new3="""            elif p.get('minutes',0)==0 and c['zero_minute_exception']:
                _floor={'GK':4.5,'DEF':5.0,'MID':5.5,'FWD':6.0}[pos]
                _cap={'GK':5.0,'DEF':5.5,'MID':7.0,'FWD':7.5}[pos]
                raw=max(_floor,min(raw,_cap))
"""
if old3 not in py: raise SystemExit('zero-minute absence distribution marker missing')
py=py.replace(old3,new3,1)

# -----------------------------------------------------------------------------
# 2) Position: marker byte is mostly zero in this save. Calibrate starter lineup
# slots from unambiguous players, then use repeated starter slots for DEF/MID hybrids.
# ----------------------------------------------------------------------------
anchor="""    changed=[]
    for eid,c in usage.items():
        p=players_by_eid.get(eid)
        if not p:continue
        st=_position_strengths(p)
        if max(st['DEF'],st['MID'])<15:continue
        dm=c['DEF']+c['MID']
        if dm<2:continue
        if c['MID']/dm>=0.80 and p.get('pos')!='MID':p['pos']='MID';p['position_source']='observed_midfield_usage_v63';changed.append(eid)
        elif c['DEF']/dm>=0.80 and p.get('pos')!='DEF':p['pos']='DEF';p['position_source']='observed_defensive_usage_v63';changed.append(eid)
    return {'marker_roles':marker_roles,'hybrid_players_reclassified':changed}
"""
replacement="""    changed=[]
    for eid,c in usage.items():
        p=players_by_eid.get(eid)
        if not p:continue
        st=_position_strengths(p)
        if max(st['DEF'],st['MID'])<15:continue
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
        if max(st['DEF'],st['MID'])<15:continue
        dm=c['DEF']+c['MID']
        if dm<2:continue
        if c['MID']/dm>=0.75 and p.get('pos')!='MID':
            p['pos']='MID';p['position_source']='observed_midfield_usage_v64_lineup_slot';p['observed_lineup_role_counts']=dict(c);changed.append(eid)
        elif c['DEF']/dm>=0.75 and p.get('pos')!='DEF':
            p['pos']='DEF';p['position_source']='observed_defensive_usage_v64_lineup_slot';p['observed_lineup_role_counts']=dict(c);changed.append(eid)
    return {'marker_roles':marker_roles,'slot_roles':slot_roles,'hybrid_players_reclassified':sorted(set(changed))}
"""
if anchor not in py: raise SystemExit('hybrid function block missing')
py=py.replace(anchor,replacement,1)

# -----------------------------------------------------------------------------
# 3) Early rich-match recovery: final conservative fallback for missing played
# fixtures. Exact score is mandatory, both sides must match the fixture's clubs,
# and the best candidate must beat the runner-up by a clear overlap margin.
# ----------------------------------------------------------------------------
loop_anchor="""    for _round in range(8):
        before=len(out)
        propagate_side_identities(2);relabel_clusters()
        a=fixture_identity_pass();b=single_side_bridge_pass()
        if a or b:
            diagnostics['propagation_rounds']+=1
            diagnostics['propagation_matches']+=a+b
        if len(out)==before:break

    diagnostics['matches_recovered']=len(out)
"""
loop_replacement="""    for _round in range(8):
        before=len(out)
        propagate_side_identities(2);relabel_clusters()
        a=fixture_identity_pass();b=single_side_bridge_pass()
        if a or b:
            diagnostics['propagation_rounds']+=1
            diagnostics['propagation_matches']+=a+b
        if len(out)==before:break

    # v6.4 final missing-fixture pass. The previous recovery left many perfectly usable
    # early-season blocks unmatched because it demanded 14 unique current-squad anchors.
    # For each still-missing authoritative played fixture, rank unused stat blocks by exact
    # final score + BOTH club squad/cohort overlaps. Accept only a strong, unique winner.
    diagnostics['missing_fixture_fallback_matches']=0
    proposals=[]
    for heid,aeid,hs,as_,f in played:
        if fixture_identity(f) in used_fixtures:continue
        ranked=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right']);lhg,lag=score_of(c)
            for rev in (False,True):
                if not rev:
                    if lhg!=hs or lag!=as_:continue
                    Hids,Aids=lids,rids;leid,reid=heid,aeid
                else:
                    if lag!=hs or lhg!=as_:continue
                    Hids,Aids=rids,lids;leid,reid=aeid,heid
                hov=len(Hids & club_sets.get(heid,set()));aov=len(Aids & club_sets.get(aeid,set()))
                hscore=sum(player_club_weight(pid,heid) for pid in Hids)
                ascore=sum(player_club_weight(pid,aeid) for pid in Aids)
                # Exact score is already mandatory. Require both sides to carry several
                # independent club identities; this is permissive enough for transfers but
                # still rejects score-only coincidences.
                if hov<4 or aov<4 or hov+aov<10:continue
                total=hov+aov+0.55*(hscore+ascore)
                ranked.append((total,min(hov,aov),hov+aov,ci,rev,leid,reid))
        ranked.sort(reverse=True)
        if not ranked:continue
        best=ranked[0];second=ranked[1][0] if len(ranked)>1 else -999.0
        if best[0]>=12.0 and best[1]>=4 and best[0]-second>=1.75:
            proposals.append((best[0]-second,best[0],f,best))
    proposals.sort(reverse=True)
    for _margin,_score,f,best in proposals:
        _total,_minov,_sumov,ci,rev,leid,reid=best
        if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
        if register_match(ci,f,rev,leid,reid,'unlabelled_retained_missing_fixture_v64'):
            diagnostics['missing_fixture_fallback_matches']+=1

    diagnostics['matches_recovered']=len(out)
"""
if loop_anchor not in py: raise SystemExit('recovery loop marker missing')
py=py.replace(loop_anchor,loop_replacement,1)

# Expose diagnostics/version clearly.
py=py.replace("'pricing_model':'fpl-shaped-v63-role-bands-transfer-aware'","'pricing_model':'fpl-shaped-v64-role-evidence-aware'",2)
py=py.replace('FPL-shaped v6.3 role-band transfer-aware launch pricing.','FPL-shaped v6.4 role-evidence-aware launch pricing.',1)
meta_anchor="""'unlabelled_rich_unmatched_cached_pairs':member_rich_diag.get('unmatched_cached_pairs',0),"""
if meta_anchor in py:
    py=py.replace(meta_anchor,meta_anchor+"'unlabelled_rich_missing_fixture_fallback_matches':member_rich_diag.get('missing_fixture_fallback_matches',0),",2)

for token in ['established_absence','observed_midfield_usage_v64_lineup_slot','missing_fixture_fallback_matches','fpl-shaped-v64-role-evidence-aware']:
    if token not in py: raise SystemExit('missing verification token '+token)
compile(py,'fm_importer.py','exec')

b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+b64+html[m.end(1):]
# Make debug builds visibly distinguishable if this legacy label is present.
html=html.replace('v23-fast-propagating-history','v24-role-evidence-rich-recovery')
out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out:raise SystemExit('repack mismatch')
print('v6.4 livefix applied: pricing + lineup positions + early rich recovery')
