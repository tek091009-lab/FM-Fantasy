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

# v131: v126-v130 begin with an already-constructed retained candidate, then look backwards for
# the proven FM HOME/AWAY match header. That cannot recover a match whose player rows were found
# but whose side segmentation never produced the correct candidate. The original direct FM26
# extractor did the stronger inverse operation: parse a proven match header first, scan forward
# for GAME_MATCH_PLAYER_STATS, then construct the two squads. Recreate that path over the already
# cached /tmp/rich_N.bin members (no .fm/archive rescan), reusing the CURRENT stat-record parser and
# all current v122-v125 side-layout decoders. A header-anchored pair is accepted only when binary
# HOME/AWAY identity + exact reconstructed score resolve to exactly one unused authoritative fixture
# and one physical array orientation, followed by the normal register_match() gate.

for prereq in [
    'def _rich_candidate_squad_pairs(stats,played_score_pairs):',
    'def _v126_fixture_modes(home_id,away_id,hs,as_):',
    'def _v130_fixture_modes(home_id,away_id,hs,as_,fixture_shift,club_shift):',
    'def _v130_learn_shift():',
    'def register_match(',
    "unrated_inactive=(rating==0",
]:
    if prereq not in py:raise RuntimeError('v131 prerequisite missing: '+prereq)

# Discover the live 214-byte stat parser by locating the v125 inactive-row marker and taking the
# nearest containing function. This deliberately reuses every field mapping/validation improvement
# already present in the packed importer instead of duplicating an older stat layout in v131.
mark=py.find("unrated_inactive=(rating==0")
defs=list(re.finditer(r'(?m)^([ \t]*)def\s+([A-Za-z_]\w*)\s*\(',py[:mark]))
if not defs:raise RuntimeError('v131 could not locate live rich stat-record parser')
record_fn=defs[-1].group(2)

# Diagnostics live beside the other retained-match counters.
diag_anchor="        'direct_header_namespace_ambiguous_rejected':0\n"
diag_new=("        'direct_header_namespace_ambiguous_rejected':0,\n"
          "        'header_anchored_members_scanned':0,'header_anchored_headers_found':0,\n"
          "        'header_anchored_stat_records':0,'header_anchored_candidate_pairs':0,\n"
          "        'header_anchored_fixture_matches':0,'header_anchored_reversed_matches':0,\n"
          "        'header_anchored_ambiguous_headers_rejected':0,\n"
          "        'header_anchored_headers_without_pairs':0,\n"
          "        'header_anchored_duplicate_pairs_skipped':0\n")
if "'header_anchored_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v131 diagnostics anchor missing; apply v130 first')
    py=py.replace(diag_anchor,diag_new,1)

anchor="    def single_side_bridge_pass():\n"
code=r'''    _v131_header_cache=None
    _v131_consumed_header_pairs=set()

    def _v131_record_at(raw,p):
        # Bound at upgrade time to the CURRENT importer parser, including v125 inactive rows.
        return __RECORD_FN__(raw,p)

    def _v131_structural_headers(raw):
        out=[];seen=set();q=0
        while raw:
            q=raw.find(b'\x03\x02',q)
            if q<0:break
            if q+12<=len(raw) and raw[q+6]==2:
                home_id=int.from_bytes(raw[q+7:q+11],'little')
                lim=min(len(raw),q+513);marker=q+11
                while True:
                    marker=raw.find(b'\x00\x03\x02',marker,lim)
                    if marker<0:break
                    if marker+12<=len(raw) and raw[marker+7]==2:
                        away_id=int.from_bytes(raw[marker+8:marker+12],'little')
                        span=marker-q
                        key=(q,home_id,away_id,span)
                        if 0<home_id<1000000 and 0<away_id<1000000 and home_id!=away_id and 11<=span<=512 and key not in seen:
                            seen.add(key);out.append(key)
                    marker+=1
            q+=1
        out.sort(key=lambda x:(x[0],x[3],x[1],x[2]))
        return out

    def _v131_scan_stats(raw,start,end):
        rows=[];p=max(0,int(start));end=min(len(raw),int(end))
        while p+214<=end:
            if raw[p]==2:
                try:r=_v131_record_at(raw,p)
                except Exception:r=None
                if r is not None:
                    rows.append(r);p+=140;continue
            p+=1
        return rows

    def _v131_pair_signature(left,right):
        return (tuple(int(x.get('offset',-1)) for x in left),tuple(int(x.get('offset',-1)) for x in right))

    def _v131_build_header_cache():
        nonlocal _v131_header_cache
        if _v131_header_cache is not None:return _v131_header_cache
        built=[]
        # Existing cached candidates are used only for de-duplication; v131's point is to create
        # candidates that the normal segmentation path never built.
        existing=collections.defaultdict(set)
        for c in cached:
            if not c.get('left') or not c.get('right'):continue
            existing[str(c.get('source_member_name') or c.get('name') or '')].add(_v131_pair_signature(c['left'],c['right']))
        for ri,member_name in enumerate(rich_names):
            raw=_v126_raw_member(ri)
            if not raw:continue
            diagnostics['header_anchored_members_scanned']+=1
            headers=_v131_structural_headers(raw)
            if not headers:continue
            diagnostics['header_anchored_headers_found']+=len(headers)
            # Delimit by the next proven structural header, matching the original extractor's
            # header->forward scan model while preventing one header from consuming the next match.
            for hi,(q,home_id,away_id,span) in enumerate(headers):
                next_q=headers[hi+1][0] if hi+1<len(headers) else len(raw)
                end=min(len(raw),q+120000,next_q)
                if end<=q+214:continue
                stats=_v131_scan_stats(raw,q,end)
                diagnostics['header_anchored_stat_records']+=len(stats)
                if len(stats)<22:
                    diagnostics['header_anchored_headers_without_pairs']+=1;continue
                try:pairs=_rich_candidate_squad_pairs(stats,played_score_pairs)
                except Exception:pairs=[]
                # De-duplicate overlapping structural variants before fixture proof.
                uniq=[];seen_pairs=set()
                for left,right in pairs:
                    sig=_v131_pair_signature(left,right)
                    if sig in seen_pairs:continue
                    seen_pairs.add(sig)
                    if sig in existing.get(str(member_name),set()):
                        diagnostics['header_anchored_duplicate_pairs_skipped']+=1
                        continue
                    uniq.append((left,right,sig))
                diagnostics['header_anchored_candidate_pairs']+=len(uniq)
                if not uniq:
                    diagnostics['header_anchored_headers_without_pairs']+=1;continue
                built.append((ri,str(member_name),q,home_id,away_id,uniq))
        _v131_header_cache=built
        return built

    def _v131_fixture_hits(home_id,away_id,left_score,right_score,fixture_shift,club_shift):
        hits=[]
        for f,heid,aeid,mode in _v126_fixture_modes(home_id,away_id,left_score,right_score):
            hits.append((fixture_identity(f),False,f,heid,aeid,'fixed_'+mode))
        for f,heid,aeid,mode in _v130_fixture_modes(home_id,away_id,left_score,right_score,fixture_shift,club_shift):
            hits.append((fixture_identity(f),False,f,heid,aeid,mode))
        if int(left_score)!=int(right_score):
            for f,heid,aeid,mode in _v126_fixture_modes(home_id,away_id,right_score,left_score):
                hits.append((fixture_identity(f),True,f,heid,aeid,'fixed_'+mode))
            for f,heid,aeid,mode in _v130_fixture_modes(home_id,away_id,right_score,left_score,fixture_shift,club_shift):
                hits.append((fixture_identity(f),True,f,heid,aeid,mode))
        return hits

    def direct_header_anchored_candidate_pass_v131():
        fixture_shift,club_shift=_v130_learn_shift()
        added=0
        for ri,member_name,q,home_id,away_id,pairs in _v131_build_header_cache():
            proposals={}
            for left,right,sig in pairs:
                hdr_key=(ri,q,sig)
                if hdr_key in _v131_consumed_header_pairs:continue
                temp={'name':member_name,'left':left,'right':right}
                left_score,right_score=score_of(temp)
                for fid,rev,f,heid,aeid,mode in _v131_fixture_hits(home_id,away_id,left_score,right_score,fixture_shift,club_shift):
                    key=(sig,fid,rev)
                    proposals.setdefault(key,(left,right,sig,fid,rev,f,heid,aeid,mode))
            if not proposals:continue
            # Do not choose between alternative squad segmentations, fixtures or orientations.
            # Header anchoring is useful only when the binary evidence collapses to one answer.
            if len(proposals)!=1:
                diagnostics['header_anchored_ambiguous_headers_rejected']+=1
                continue
            left,right,sig,fid,rev,f,heid,aeid,mode=next(iter(proposals.values()))
            hdr_key=(ri,q,sig)
            if hdr_key in _v131_consumed_header_pairs or fixture_identity(f) in used_fixtures:continue
            synthetic_name=f'{member_name}#header-v131-{ri}-{q}'
            _rich_name_indexes[synthetic_name]=[ri]
            c={'name':synthetic_name,'source_member_name':member_name,'source_member_index':ri,
               'header_offset_v131':q,'left':left,'right':right,'header_anchored_v131':True}
            ci=len(cached);cached.append(c)
            leid,reid=(aeid,heid) if rev else (heid,aeid)
            source='unlabelled_retained_header_anchored_reversed_v131' if rev else 'unlabelled_retained_header_anchored_v131'
            if register_match(ci,f,rev,leid,reid,source):
                _v131_consumed_header_pairs.add(hdr_key)
                diagnostics['header_anchored_fixture_matches']+=1
                if rev:diagnostics['header_anchored_reversed_matches']+=1
                added+=1
            else:
                # Keep the candidate universe evidence-clean if the authoritative registration
                # gate rejects it; later identity propagation must not learn from a failed v131 pair.
                cached.pop();_rich_name_indexes.pop(synthetic_name,None)
        return added

    def single_side_bridge_pass():
'''.replace('__RECORD_FN__',record_fn)
if 'def direct_header_anchored_candidate_pass_v131():' not in py:
    if anchor not in py:raise RuntimeError('v131 insertion anchor missing')
    py=py.replace(anchor,code,1)

# Run after the current candidate-first direct header stack, so already-safe matches and any v130
# learned namespace are available. Re-run inside fixed-point rounds; raw parsing is cached, while a
# newly learned namespace can make a previously unresolved header-anchored pair provable.
pre_anchor=("    _v130_direct_namespace=direct_binary_header_learned_namespace_pass()\n"
            "    if _v130_direct_namespace:\n"
            "        diagnostics['propagation_matches']+=_v130_direct_namespace\n\n"
            "    for _round in range(8):\n")
pre_new=("    _v130_direct_namespace=direct_binary_header_learned_namespace_pass()\n"
         "    if _v130_direct_namespace:\n"
         "        diagnostics['propagation_matches']+=_v130_direct_namespace\n"
         "    _v131_header_anchored=direct_header_anchored_candidate_pass_v131()\n"
         "    if _v131_header_anchored:\n"
         "        diagnostics['propagation_matches']+=_v131_header_anchored\n\n"
         "    for _round in range(8):\n")
if '_v131_header_anchored=direct_header_anchored_candidate_pass_v131()' not in py:
    if pre_anchor not in py:raise RuntimeError('v131 pre-loop anchor missing')
    py=py.replace(pre_anchor,pre_new,1)

round_anchor=("        _v130_round=direct_binary_header_learned_namespace_pass()\n"
              "        if _v130_round:\n"
              "            added+=_v130_round\n"
              "            diagnostics['propagation_matches']+=_v130_round\n"
              "        if not added:break\n")
round_new=("        _v130_round=direct_binary_header_learned_namespace_pass()\n"
           "        if _v130_round:\n"
           "            added+=_v130_round\n"
           "            diagnostics['propagation_matches']+=_v130_round\n"
           "        _v131_round=direct_header_anchored_candidate_pass_v131()\n"
           "        if _v131_round:\n"
           "            added+=_v131_round\n"
           "            diagnostics['propagation_matches']+=_v131_round\n"
           "        if not added:break\n")
if '_v131_round=direct_header_anchored_candidate_pass_v131()' not in py:
    if round_anchor not in py:raise RuntimeError('v131 fixed-point anchor missing')
    py=py.replace(round_anchor,round_new,1)

handoff_anchor="'unlabelled_rich_direct_header_namespace_ambiguous_rejected':member_rich_diag.get('direct_header_namespace_ambiguous_rejected',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_members_scanned':member_rich_diag.get('header_anchored_members_scanned',0),"+
    "'unlabelled_rich_header_anchored_headers_found':member_rich_diag.get('header_anchored_headers_found',0),"+
    "'unlabelled_rich_header_anchored_stat_records':member_rich_diag.get('header_anchored_stat_records',0),"+
    "'unlabelled_rich_header_anchored_candidate_pairs':member_rich_diag.get('header_anchored_candidate_pairs',0),"+
    "'unlabelled_rich_header_anchored_fixture_matches':member_rich_diag.get('header_anchored_fixture_matches',0),"+
    "'unlabelled_rich_header_anchored_reversed_matches':member_rich_diag.get('header_anchored_reversed_matches',0),"+
    "'unlabelled_rich_header_anchored_ambiguous_headers_rejected':member_rich_diag.get('header_anchored_ambiguous_headers_rejected',0),"+
    "'unlabelled_rich_header_anchored_headers_without_pairs':member_rich_diag.get('header_anchored_headers_without_pairs',0),"+
    "'unlabelled_rich_header_anchored_duplicate_pairs_skipped':member_rich_diag.get('header_anchored_duplicate_pairs_skipped',0),")
if 'unlabelled_rich_header_anchored_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v131 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def direct_header_anchored_candidate_pass_v131():',
    'def _v131_scan_stats(raw,start,end):',
    'return '+record_fn+'(raw,p)',
    '_rich_candidate_squad_pairs(stats,played_score_pairs)',
    'end=min(len(raw),q+120000,next_q)',
    "if len(proposals)!=1:",
    "source='unlabelled_retained_header_anchored_reversed_v131' if rev else 'unlabelled_retained_header_anchored_v131'",
    '_v131_header_anchored=direct_header_anchored_candidate_pass_v131()',
    '_v131_round=direct_header_anchored_candidate_pass_v131()',
    'unlabelled_rich_header_anchored_fixture_matches',
]:
    if token not in py:raise RuntimeError('v131 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_header_anchored_v131' in cpy
assert 'unlabelled_retained_header_anchored_reversed_v131' in cpy
print('v131 header-anchored retained candidate construction applied using live stat parser:',record_fn)
