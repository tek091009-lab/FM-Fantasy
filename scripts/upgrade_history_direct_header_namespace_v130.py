from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v130: direct retained match headers are much stronger than player-cohort inference, but
# v126-v129 only understand three fixed team-ID namespaces (fixture tid, club eid, eid+1).
# Unknown FM schema generations may preserve the same proven HOME/AWAY header while shifting
# the numeric team namespace by another constant. Learn that transform ONLY from retained
# candidates that register_match() has already attached to authoritative played fixtures.
# A learned transform requires multiple independent confirmed fixtures and equal HOME/AWAY
# deltas inside each confirming match. It can then be used on unresolved candidates, still
# requiring exact score + one fixture identity/orientation + register_match().

diag_anchor="        'direct_header_long_span_max_span':0\n"
diag_new=("        'direct_header_long_span_max_span':0,\n"
          "        'direct_header_namespace_confirmed_pairs':0,\n"
          "        'direct_header_namespace_fixture_shift':None,\n"
          "        'direct_header_namespace_fixture_shift_support':0,\n"
          "        'direct_header_namespace_club_shift':None,\n"
          "        'direct_header_namespace_club_shift_support':0,\n"
          "        'direct_header_namespace_fixture_matches':0,\n"
          "        'direct_header_namespace_ambiguous_rejected':0\n")
if "'direct_header_namespace_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v130 diagnostics anchor missing; apply v129 first')
    py=py.replace(diag_anchor,diag_new,1)

# Keep a minimal authoritative candidate->fixture ledger. It is populated only after the
# existing register_match() acceptance gate succeeds; no speculative candidate can train v130.
store_anchor="    confirmed_cohort_seen=set()\n"
store_new="    confirmed_cohort_seen=set()\n    confirmed_candidate_fixture_pairs=[]\n"
if 'confirmed_candidate_fixture_pairs=[]' not in py:
    if store_anchor not in py:raise RuntimeError('v130 confirmed-pair store anchor missing; apply v93 first')
    py=py.replace(store_anchor,store_new,1)

reg_anchor="        used_fixtures.add(fid);used_candidates.add(ci)\n        # v93: only an already-accepted authoritative match may teach a retained cohort.\n"
reg_new="        used_fixtures.add(fid);used_candidates.add(ci)\n        confirmed_candidate_fixture_pairs.append((ci,f,int(leid),int(reid)))\n        # v93: only an already-accepted authoritative match may teach a retained cohort.\n"
if 'confirmed_candidate_fixture_pairs.append((ci,f,int(leid),int(reid)))' not in py:
    if reg_anchor not in py:raise RuntimeError('v130 register_match ledger anchor missing')
    py=py.replace(reg_anchor,reg_new,1)

anchor="    def single_side_bridge_pass():\n"
code=r'''    def _v130_all_header_pairs(raw,start):
        # Reuse the two proven direct-header representations without inventing a new marker:
        # <=96-byte HOME->AWAY span (v128 locality) and 97..512 span (v129).
        out=[]
        seen=set()
        for row in _v128_header_pairs_extended(raw,start):
            q,h,a,distance=row
            key=(q,h,a,distance)
            if key not in seen:seen.add(key);out.append((q,h,a,distance))
        for row in _v129_header_pairs_long_span(raw,start):
            q,h,a,distance,_span=row
            key=(q,h,a,distance)
            if key not in seen:seen.add(key);out.append((q,h,a,distance))
        return out

    def _v130_learn_shift():
        fixture_votes=collections.Counter();club_votes=collections.Counter()
        fixture_support=collections.defaultdict(set);club_support=collections.defaultdict(set)
        for ci,f,heid,aeid in confirmed_candidate_fixture_pairs:
            if ci<0 or ci>=len(cached):continue
            c=cached[ci]
            if not c.get('left') or not c.get('right'):continue
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            fid=fixture_identity(f)
            per_fixture=set();per_club=set()
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for _q,hh,aa,_distance in _v130_all_header_pairs(raw,start):
                    # Equal HOME/AWAY delta is a structural invariant for a constant namespace
                    # transform. Count each shift at most once per authoritative fixture.
                    if fh>0 and fa>0:
                        dh=hh-fh;da=aa-fa
                        if dh==da and abs(dh)<=1000000:per_fixture.add(int(dh))
                    dh=hh-int(heid);da=aa-int(aeid)
                    if dh==da and abs(dh)<=1000000:per_club.add(int(dh))
            for shift in per_fixture:
                fixture_votes[shift]+=1;fixture_support[shift].add(fid)
            for shift in per_club:
                club_votes[shift]+=1;club_support[shift].add(fid)

        def choose(votes,support):
            ranked=[]
            for shift,count in votes.items():
                n=len(support.get(shift,set()))
                if n>=3:ranked.append((n,count,-abs(int(shift)),int(shift)))
            ranked.sort(reverse=True)
            if not ranked:return None,0
            top=ranked[0];second=ranked[1] if len(ranked)>1 else (0,0,0,0)
            # Require at least three independent fixtures and a clear two-fixture lead over
            # any competing transform. This prevents one noisy nearby header from training it.
            if top[0]-second[0]<2:return None,0
            return top[3],top[0]

        fshift,fsupport=choose(fixture_votes,fixture_support)
        cshift,csupport=choose(club_votes,club_support)
        diagnostics['direct_header_namespace_confirmed_pairs']=len({fixture_identity(x[1]) for x in confirmed_candidate_fixture_pairs})
        diagnostics['direct_header_namespace_fixture_shift']=fshift
        diagnostics['direct_header_namespace_fixture_shift_support']=fsupport
        diagnostics['direct_header_namespace_club_shift']=cshift
        diagnostics['direct_header_namespace_club_shift_support']=csupport
        return fshift,cshift

    def _v130_fixture_modes(home_id,away_id,hs,as_,fixture_shift,club_shift):
        hits=[]
        for heid,aeid,fhs,fas,f in played:
            if fixture_identity(f) in used_fixtures:continue
            if int(fhs)!=int(hs) or int(fas)!=int(as_):continue
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            if fixture_shift is not None and fh>0 and fa>0:
                if (home_id-fixture_shift,away_id-fixture_shift)==(fh,fa):hits.append((f,heid,aeid,'learned_fixture_shift'))
            if club_shift is not None:
                if (home_id-club_shift,away_id-club_shift)==(int(heid),int(aeid)):hits.append((f,heid,aeid,'learned_club_shift'))
        return hits

    def direct_binary_header_learned_namespace_pass():
        fixture_shift,club_shift=_v130_learn_shift()
        if fixture_shift is None and club_shift is None:return 0
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            left_score,right_score=score_of(c)
            compatible=[]
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for q,home_id,away_id,distance in _v130_all_header_pairs(raw,start):
                    for f,heid,aeid,mode in _v130_fixture_modes(home_id,away_id,left_score,right_score,fixture_shift,club_shift):
                        compatible.append((fixture_identity(f),False,distance,q,f,heid,aeid,mode))
                    if int(left_score)!=int(right_score):
                        for f,heid,aeid,mode in _v130_fixture_modes(home_id,away_id,right_score,left_score,fixture_shift,club_shift):
                            compatible.append((fixture_identity(f),True,distance,q,f,heid,aeid,mode))
            if not compatible:continue
            by_key=collections.defaultdict(list)
            for hit in compatible:by_key[(hit[0],hit[1])].append(hit)
            if len(by_key)!=1:
                diagnostics['direct_header_namespace_ambiguous_rejected']+=1
                continue
            group=next(iter(by_key.values()))
            hit=min(group,key=lambda x:(x[2],-x[3]))
            _fid,rev,distance,q,f,heid,aeid,mode=hit
            proposals.append((distance,ci,rev,f,heid,aeid,mode,q))
        proposals.sort(key=lambda x:(x[0],x[1]))
        added=0
        for distance,ci,rev,f,heid,aeid,mode,q in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            leid,reid=(aeid,heid) if rev else (heid,aeid)
            source='unlabelled_retained_direct_match_header_learned_namespace_reversed_v130' if rev else 'unlabelled_retained_direct_match_header_learned_namespace_v130'
            if register_match(ci,f,rev,leid,reid,source):
                added+=1;diagnostics['direct_header_namespace_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
'''
if 'def direct_binary_header_learned_namespace_pass():' not in py:
    if anchor not in py:raise RuntimeError('v130 insertion anchor missing')
    py=py.replace(anchor,code,1)

# Learn after the existing direct structural passes have registered anything they can. Then run
# v130 inside each fixed-point round too, because newly confirmed matches may establish a shift.
loop_anchor=("    _v129_direct_long_span=direct_binary_header_long_span_pass()\n"
             "    if _v129_direct_long_span:\n"
             "        diagnostics['propagation_matches']+=_v129_direct_long_span\n\n"
             "    for _round in range(8):\n")
loop_new=("    _v129_direct_long_span=direct_binary_header_long_span_pass()\n"
          "    if _v129_direct_long_span:\n"
          "        diagnostics['propagation_matches']+=_v129_direct_long_span\n"
          "    _v130_direct_namespace=direct_binary_header_learned_namespace_pass()\n"
          "    if _v130_direct_namespace:\n"
          "        diagnostics['propagation_matches']+=_v130_direct_namespace\n\n"
          "    for _round in range(8):\n")
if '_v130_direct_namespace=direct_binary_header_learned_namespace_pass()' not in py:
    if loop_anchor not in py:raise RuntimeError('v130 pre-loop anchor missing; apply v129 first')
    py=py.replace(loop_anchor,loop_new,1)

# Re-run after each recovery round so new authoritative matches can create a previously unknown
# namespace transform. Idempotence is guaranteed by used_candidates/used_fixtures.
round_anchor="        if not added:break\n"
round_new=("        _v130_round=direct_binary_header_learned_namespace_pass()\n"
           "        if _v130_round:\n"
           "            added+=_v130_round\n"
           "            diagnostics['propagation_matches']+=_v130_round\n"
           "        if not added:break\n")
if '_v130_round=direct_binary_header_learned_namespace_pass()' not in py:
    if round_anchor not in py:raise RuntimeError('v130 fixed-point round anchor missing')
    py=py.replace(round_anchor,round_new,1)

handoff_anchor="'unlabelled_rich_direct_header_long_span_max_span':member_rich_diag.get('direct_header_long_span_max_span',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_direct_header_namespace_confirmed_pairs':member_rich_diag.get('direct_header_namespace_confirmed_pairs',0),"+
    "'unlabelled_rich_direct_header_namespace_fixture_shift':member_rich_diag.get('direct_header_namespace_fixture_shift'),"+
    "'unlabelled_rich_direct_header_namespace_fixture_shift_support':member_rich_diag.get('direct_header_namespace_fixture_shift_support',0),"+
    "'unlabelled_rich_direct_header_namespace_club_shift':member_rich_diag.get('direct_header_namespace_club_shift'),"+
    "'unlabelled_rich_direct_header_namespace_club_shift_support':member_rich_diag.get('direct_header_namespace_club_shift_support',0),"+
    "'unlabelled_rich_direct_header_namespace_fixture_matches':member_rich_diag.get('direct_header_namespace_fixture_matches',0),"+
    "'unlabelled_rich_direct_header_namespace_ambiguous_rejected':member_rich_diag.get('direct_header_namespace_ambiguous_rejected',0),")
if 'unlabelled_rich_direct_header_namespace_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v130 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'confirmed_candidate_fixture_pairs=[]',
    'confirmed_candidate_fixture_pairs.append((ci,f,int(leid),int(reid)))',
    'def _v130_learn_shift():',
    'if dh==da and abs(dh)<=1000000:per_fixture.add(int(dh))',
    'if n>=3:ranked.append',
    'if top[0]-second[0]<2:return None,0',
    'def direct_binary_header_learned_namespace_pass():',
    '_v130_direct_namespace=direct_binary_header_learned_namespace_pass()',
    '_v130_round=direct_binary_header_learned_namespace_pass()',
    'unlabelled_rich_direct_header_namespace_fixture_matches',
]:
    if token not in py:raise RuntimeError('v130 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_direct_match_header_learned_namespace_v130' in cpy
assert 'unlabelled_retained_direct_match_header_learned_namespace_reversed_v130' in cpy
print('v130 learned retained-header team-ID namespace recovery applied')
