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

# v128: the proven labelled rich extractor scans player stats out to 120,000 bytes after
# the competition/header area. v126's direct-header fallback introduced a much tighter
# 32 KiB backward window plus an unsupported minimum 64-byte header distance. Preserve
# v126/v127 exactly, then give unresolved candidates a second conservative locality path:
# scan 12..120,000 bytes before the first stat row, but accept only when ALL compatible
# header evidence collapses to one authoritative fixture + one physical array orientation.
# This attacks alternate padding/header-to-array layouts, not club/player identity.

diag_anchor="        'direct_header_reversed_equal_score_skipped':0\n"
diag_new=("        'direct_header_reversed_equal_score_skipped':0,\n"
          "        'direct_header_extended_candidates_scanned':0,\n"
          "        'direct_header_extended_structural_pairs_found':0,\n"
          "        'direct_header_extended_fixture_matches':0,\n"
          "        'direct_header_extended_ambiguous_rejected':0,\n"
          "        'direct_header_extended_near_matches':0,\n"
          "        'direct_header_extended_far_matches':0\n")
if "'direct_header_extended_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v128 diagnostics anchor missing; apply v127 first')
    py=py.replace(diag_anchor,diag_new,1)

anchor="    def single_side_bridge_pass():\n"
code=r'''    def _v128_header_pairs_extended(raw,start):
        # Original labelled extractor allows the stat payload to live as far as 120 kB after
        # the match header/competition block. Do not assume v126's 64..32768 byte spacing.
        if not raw or start<=0:return []
        lo=max(0,int(start)-120000);hi=min(len(raw),int(start))
        out=[];q=lo
        while True:
            q=raw.find(b'\x03\x02',q,hi)
            if q<0:break
            if q+12<=hi and raw[q+6]==2:
                home_tid=int.from_bytes(raw[q+7:q+11],'little')
                marker=raw.find(b'\x00\x03\x02',q+11,min(hi,q+96))
                if marker>=0 and marker+12<=hi and raw[marker+7]==2:
                    away_tid=int.from_bytes(raw[marker+8:marker+12],'little')
                    if 0<home_tid<1000000 and 0<away_tid<1000000 and home_tid!=away_tid:
                        distance=int(start)-q
                        # Header itself occupies at least 11 bytes; require it to precede the
                        # player record rather than overlap it, but impose no artificial 64 B floor.
                        if 12<=distance<=120000:out.append((q,home_tid,away_tid,distance))
            q+=1
        return out

    def direct_binary_header_extended_locality_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            diagnostics['direct_header_extended_candidates_scanned']+=1
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            left_score,right_score=score_of(c)
            compatible=[]
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for q,home_id,away_id,distance in _v128_header_pairs_extended(raw,start):
                    # v126 normal HOME/AWAY physical array orientation.
                    for f,heid,aeid,mode in _v126_fixture_modes(home_id,away_id,left_score,right_score):
                        compatible.append((fixture_identity(f),False,distance,q,f,heid,aeid,mode))
                        diagnostics['direct_header_extended_structural_pairs_found']+=1
                    # v127 alternate physical array serialization: AWAY block then HOME block.
                    if int(left_score)!=int(right_score):
                        for f,heid,aeid,mode in _v127_reversed_fixture_modes(home_id,away_id,left_score,right_score):
                            compatible.append((fixture_identity(f),True,distance,q,f,heid,aeid,mode))
                            diagnostics['direct_header_extended_structural_pairs_found']+=1
            if not compatible:continue
            # Strong locality safety: the broader window is allowed only when every structurally
            # compatible header collapses to one authoritative fixture AND one array orientation.
            by_key=collections.defaultdict(list)
            for hit in compatible:by_key[(hit[0],hit[1])].append(hit)
            if len(by_key)!=1:
                diagnostics['direct_header_extended_ambiguous_rejected']+=1
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
            source='unlabelled_retained_direct_match_header_extended_reversed_v128' if rev else 'unlabelled_retained_direct_match_header_extended_v128'
            if register_match(ci,f,rev,leid,reid,source):
                added+=1
                diagnostics['direct_header_extended_fixture_matches']+=1
                if distance<64:diagnostics['direct_header_extended_near_matches']+=1
                if distance>32768:diagnostics['direct_header_extended_far_matches']+=1
        return added

    def single_side_bridge_pass():
'''
if 'def direct_binary_header_extended_locality_pass():' not in py:
    if anchor not in py:raise RuntimeError('v128 insertion anchor missing')
    py=py.replace(anchor,code,1)

loop_anchor=("    _v127_direct_reversed=direct_binary_header_reversed_fixture_pass()\n"
             "    if _v127_direct_reversed:\n"
             "        diagnostics['propagation_matches']+=_v127_direct_reversed\n\n"
             "    for _round in range(8):\n")
loop_new=("    _v127_direct_reversed=direct_binary_header_reversed_fixture_pass()\n"
          "    if _v127_direct_reversed:\n"
          "        diagnostics['propagation_matches']+=_v127_direct_reversed\n"
          "    _v128_direct_extended=direct_binary_header_extended_locality_pass()\n"
          "    if _v128_direct_extended:\n"
          "        diagnostics['propagation_matches']+=_v128_direct_extended\n\n"
          "    for _round in range(8):\n")
if '_v128_direct_extended=direct_binary_header_extended_locality_pass()' not in py:
    if loop_anchor not in py:raise RuntimeError('v128 loop anchor missing; apply v127 first')
    py=py.replace(loop_anchor,loop_new,1)

handoff_anchor="'unlabelled_rich_direct_header_reversed_equal_score_skipped':member_rich_diag.get('direct_header_reversed_equal_score_skipped',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_direct_header_extended_candidates_scanned':member_rich_diag.get('direct_header_extended_candidates_scanned',0),"+
    "'unlabelled_rich_direct_header_extended_structural_pairs_found':member_rich_diag.get('direct_header_extended_structural_pairs_found',0),"+
    "'unlabelled_rich_direct_header_extended_fixture_matches':member_rich_diag.get('direct_header_extended_fixture_matches',0),"+
    "'unlabelled_rich_direct_header_extended_ambiguous_rejected':member_rich_diag.get('direct_header_extended_ambiguous_rejected',0),"+
    "'unlabelled_rich_direct_header_extended_near_matches':member_rich_diag.get('direct_header_extended_near_matches',0),"+
    "'unlabelled_rich_direct_header_extended_far_matches':member_rich_diag.get('direct_header_extended_far_matches',0),")
if 'unlabelled_rich_direct_header_extended_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v128 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v128_header_pairs_extended(raw,start):',
    'if 12<=distance<=120000:out.append((q,home_tid,away_tid,distance))',
    'def direct_binary_header_extended_locality_pass():',
    "if len(by_key)!=1:",
    '_v128_direct_extended=direct_binary_header_extended_locality_pass()',
    'unlabelled_rich_direct_header_extended_fixture_matches',
]:
    if token not in py:raise RuntimeError('v128 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_direct_match_header_extended_v128' in cpy
assert 'unlabelled_retained_direct_match_header_extended_reversed_v128' in cpy
print('v128 extended retained-header locality recovery applied')