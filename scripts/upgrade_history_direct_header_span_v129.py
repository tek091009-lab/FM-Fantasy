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

# v129: v126-v128 widened where the match header may sit relative to the player arrays,
# but still assumed the AWAY sub-header follows the HOME sub-header within ~96 bytes.
# That bound came from one proven schema, not a universal invariant. Preserve all earlier
# paths and add a second direct-binary route for a variable HOME->AWAY metadata span of
# 97..512 bytes. The wider span is never trusted alone: ordered team IDs + exact player-
# reconstructed score must collapse to one authoritative unused fixture and one physical
# array orientation before register_match() can attach anything.

diag_anchor="        'direct_header_extended_far_matches':0\n"
diag_new=("        'direct_header_extended_far_matches':0,\n"
          "        'direct_header_long_span_candidates_scanned':0,\n"
          "        'direct_header_long_span_structural_pairs_found':0,\n"
          "        'direct_header_long_span_fixture_matches':0,\n"
          "        'direct_header_long_span_ambiguous_rejected':0,\n"
          "        'direct_header_long_span_max_span':0\n")
if "'direct_header_long_span_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v129 diagnostics anchor missing; apply v128 first')
    py=py.replace(diag_anchor,diag_new,1)

anchor="    def single_side_bridge_pass():\n"
code=r'''    def _v129_header_pairs_long_span(raw,start):
        if not raw or start<=0:return []
        lo=max(0,int(start)-120000);hi=min(len(raw),int(start))
        out=[];q=lo
        while True:
            q=raw.find(b'\x03\x02',q,hi)
            if q<0:break
            if q+12<=hi and raw[q+6]==2:
                home_tid=int.from_bytes(raw[q+7:q+11],'little')
                # v126-v128 already cover <=96-byte HOME->AWAY spans. This path exists only
                # for longer metadata blocks so it cannot duplicate the earlier representation.
                search_lo=q+97
                search_hi=min(hi,q+513)
                marker=raw.find(b'\x00\x03\x02',search_lo,search_hi)
                while marker>=0:
                    if marker+12<=hi and raw[marker+7]==2:
                        away_tid=int.from_bytes(raw[marker+8:marker+12],'little')
                        if 0<home_tid<1000000 and 0<away_tid<1000000 and home_tid!=away_tid:
                            distance=int(start)-q;span=marker-q
                            if 12<=distance<=120000 and 97<=span<=512:
                                out.append((q,home_tid,away_tid,distance,span))
                    marker=raw.find(b'\x00\x03\x02',marker+1,search_hi)
            q+=1
        return out

    def direct_binary_header_long_span_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            diagnostics['direct_header_long_span_candidates_scanned']+=1
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            left_score,right_score=score_of(c)
            compatible=[]
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for q,home_id,away_id,distance,span in _v129_header_pairs_long_span(raw,start):
                    diagnostics['direct_header_long_span_max_span']=max(diagnostics['direct_header_long_span_max_span'],int(span))
                    for f,heid,aeid,mode in _v126_fixture_modes(home_id,away_id,left_score,right_score):
                        compatible.append((fixture_identity(f),False,distance,span,q,f,heid,aeid,mode))
                        diagnostics['direct_header_long_span_structural_pairs_found']+=1
                    if int(left_score)!=int(right_score):
                        for f,heid,aeid,mode in _v127_reversed_fixture_modes(home_id,away_id,left_score,right_score):
                            compatible.append((fixture_identity(f),True,distance,span,q,f,heid,aeid,mode))
                            diagnostics['direct_header_long_span_structural_pairs_found']+=1
            if not compatible:continue
            # The wider internal span increases incidental-pattern risk, so be stricter than
            # nearest-header selection: all compatible evidence must prove one fixture+orientation.
            by_key=collections.defaultdict(list)
            for hit in compatible:by_key[(hit[0],hit[1])].append(hit)
            if len(by_key)!=1:
                diagnostics['direct_header_long_span_ambiguous_rejected']+=1
                continue
            group=next(iter(by_key.values()))
            hit=min(group,key=lambda x:(x[2],x[3],-x[4]))
            _fid,rev,distance,span,q,f,heid,aeid,mode=hit
            proposals.append((distance,span,ci,rev,f,heid,aeid,mode,q))
        proposals.sort(key=lambda x:(x[0],x[1],x[2]))
        added=0
        for distance,span,ci,rev,f,heid,aeid,mode,q in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            leid,reid=(aeid,heid) if rev else (heid,aeid)
            source='unlabelled_retained_direct_match_header_long_span_reversed_v129' if rev else 'unlabelled_retained_direct_match_header_long_span_v129'
            if register_match(ci,f,rev,leid,reid,source):
                added+=1
                diagnostics['direct_header_long_span_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
'''
if 'def direct_binary_header_long_span_pass():' not in py:
    if anchor not in py:raise RuntimeError('v129 insertion anchor missing')
    py=py.replace(anchor,code,1)

loop_anchor=("    _v128_direct_extended=direct_binary_header_extended_locality_pass()\n"
             "    if _v128_direct_extended:\n"
             "        diagnostics['propagation_matches']+=_v128_direct_extended\n\n"
             "    for _round in range(8):\n")
loop_new=("    _v128_direct_extended=direct_binary_header_extended_locality_pass()\n"
          "    if _v128_direct_extended:\n"
          "        diagnostics['propagation_matches']+=_v128_direct_extended\n"
          "    _v129_direct_long_span=direct_binary_header_long_span_pass()\n"
          "    if _v129_direct_long_span:\n"
          "        diagnostics['propagation_matches']+=_v129_direct_long_span\n\n"
          "    for _round in range(8):\n")
if '_v129_direct_long_span=direct_binary_header_long_span_pass()' not in py:
    if loop_anchor not in py:raise RuntimeError('v129 loop anchor missing; apply v128 first')
    py=py.replace(loop_anchor,loop_new,1)

handoff_anchor="'unlabelled_rich_direct_header_extended_far_matches':member_rich_diag.get('direct_header_extended_far_matches',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_direct_header_long_span_candidates_scanned':member_rich_diag.get('direct_header_long_span_candidates_scanned',0),"+
    "'unlabelled_rich_direct_header_long_span_structural_pairs_found':member_rich_diag.get('direct_header_long_span_structural_pairs_found',0),"+
    "'unlabelled_rich_direct_header_long_span_fixture_matches':member_rich_diag.get('direct_header_long_span_fixture_matches',0),"+
    "'unlabelled_rich_direct_header_long_span_ambiguous_rejected':member_rich_diag.get('direct_header_long_span_ambiguous_rejected',0),"+
    "'unlabelled_rich_direct_header_long_span_max_span':member_rich_diag.get('direct_header_long_span_max_span',0),")
if 'unlabelled_rich_direct_header_long_span_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v129 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v129_header_pairs_long_span(raw,start):',
    'search_lo=q+97',
    'search_hi=min(hi,q+513)',
    'def direct_binary_header_long_span_pass():',
    "if len(by_key)!=1:",
    '_v129_direct_long_span=direct_binary_header_long_span_pass()',
    'unlabelled_rich_direct_header_long_span_fixture_matches',
]:
    if token not in py:raise RuntimeError('v129 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_direct_match_header_long_span_v129' in cpy
assert 'unlabelled_retained_direct_match_header_long_span_reversed_v129' in cpy
print('v129 variable retained match-header span recovery applied')
