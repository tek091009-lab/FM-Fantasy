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

# v127: v126 proved a direct retained match header can carry ordered HOME/AWAY team IDs,
# but it assumed the following player-stat arrays were also serialized HOME then AWAY.
# FM array order is a separate representation concern. Recover the alternate physical layout
# where the retained player arrays are AWAY then HOME, using the binary header itself to prove
# home/away identity. No club/cohort inference is used by this path.

diag_anchor="        'direct_header_namespace_club_eid_plus1':0\n"
diag_new=("        'direct_header_namespace_club_eid_plus1':0,\n"
          "        'direct_header_reversed_candidates_scanned':0,\n"
          "        'direct_header_reversed_fixture_matches':0,\n"
          "        'direct_header_reversed_ambiguous_rejected':0,\n"
          "        'direct_header_reversed_equal_score_skipped':0\n")
if "'direct_header_reversed_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v127 diagnostics anchor missing; apply v126 first')
    py=py.replace(diag_anchor,diag_new,1)

anchor="    def single_side_bridge_pass():\n"
code=r'''    def _v127_reversed_fixture_modes(home_id,away_id,left_score,right_score):
        # Header is HOME/AWAY, but the retained stat arrays may physically be AWAY/HOME.
        # Only non-level scores can prove this representation; level scores are orientation-
        # invariant and are already handled safely by v126.
        if int(left_score)==int(right_score):return []
        hits=[]
        for heid,aeid,fhs,fas,f in played:
            if fixture_identity(f) in used_fixtures:continue
            # Candidate left is AWAY and candidate right is HOME.
            if int(fhs)!=int(right_score) or int(fas)!=int(left_score):continue
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            modes=[]
            if (home_id,away_id)==(fh,fa):modes.append('fixture_tid')
            if (home_id,away_id)==(int(heid),int(aeid)):modes.append('club_eid')
            if (home_id,away_id)==(int(heid)+1,int(aeid)+1):modes.append('club_eid_plus1')
            for mode in modes:hits.append((f,heid,aeid,mode))
        return hits

    def direct_binary_header_reversed_fixture_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            diagnostics['direct_header_reversed_candidates_scanned']+=1
            left_score,right_score=score_of(c)
            if int(left_score)==int(right_score):
                diagnostics['direct_header_reversed_equal_score_skipped']+=1
                continue
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            raw_hits=[]
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for q,home_id,away_id,distance in _v126_header_pairs(raw,start):
                    for f,heid,aeid,mode in _v127_reversed_fixture_modes(home_id,away_id,left_score,right_score):
                        raw_hits.append((fixture_identity(f),distance,q,f,heid,aeid,mode))
            if not raw_hits:continue
            by_fixture=collections.defaultdict(list)
            for hit in raw_hits:by_fixture[hit[0]].append(hit)
            if len(by_fixture)!=1:
                diagnostics['direct_header_reversed_ambiguous_rejected']+=1
                continue
            group=next(iter(by_fixture.values()))
            hit=min(group,key=lambda x:(x[1],-x[2]))
            _fid,distance,q,f,heid,aeid,mode=hit
            proposals.append((distance,ci,f,heid,aeid,mode,q))
        proposals.sort(key=lambda x:(x[0],x[1]))
        added=0
        for distance,ci,f,heid,aeid,mode,q in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            # rev=True swaps the physical left/right arrays into authoritative HOME/AWAY.
            # leid/reid describe the physical left/right identities: left=away, right=home.
            if register_match(ci,f,True,aeid,heid,'unlabelled_retained_direct_match_header_reversed_v127'):
                added+=1
                diagnostics['direct_header_reversed_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
'''
if 'def direct_binary_header_reversed_fixture_pass():' not in py:
    if anchor not in py:raise RuntimeError('v127 insertion anchor missing')
    py=py.replace(anchor,code,1)

loop_anchor="    _v126_direct=direct_binary_header_fixture_pass()\n    if _v126_direct:\n        diagnostics['propagation_matches']+=_v126_direct\n\n    for _round in range(8):\n"
loop_new=("    _v126_direct=direct_binary_header_fixture_pass()\n"
          "    if _v126_direct:\n"
          "        diagnostics['propagation_matches']+=_v126_direct\n"
          "    _v127_direct_reversed=direct_binary_header_reversed_fixture_pass()\n"
          "    if _v127_direct_reversed:\n"
          "        diagnostics['propagation_matches']+=_v127_direct_reversed\n\n"
          "    for _round in range(8):\n")
if '_v127_direct_reversed=direct_binary_header_reversed_fixture_pass()' not in py:
    if loop_anchor not in py:raise RuntimeError('v127 loop anchor missing; apply v126 first')
    py=py.replace(loop_anchor,loop_new,1)

handoff_anchor="'unlabelled_rich_direct_header_namespace_club_eid_plus1':member_rich_diag.get('direct_header_namespace_club_eid_plus1',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_direct_header_reversed_candidates_scanned':member_rich_diag.get('direct_header_reversed_candidates_scanned',0),"
    "'unlabelled_rich_direct_header_reversed_fixture_matches':member_rich_diag.get('direct_header_reversed_fixture_matches',0),"
    "'unlabelled_rich_direct_header_reversed_ambiguous_rejected':member_rich_diag.get('direct_header_reversed_ambiguous_rejected',0),"
    "'unlabelled_rich_direct_header_reversed_equal_score_skipped':member_rich_diag.get('direct_header_reversed_equal_score_skipped',0),")
if 'unlabelled_rich_direct_header_reversed_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v127 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v127_reversed_fixture_modes(home_id,away_id,left_score,right_score):',
    'if int(fhs)!=int(right_score) or int(fas)!=int(left_score):continue',
    'def direct_binary_header_reversed_fixture_pass():',
    "register_match(ci,f,True,aeid,heid,'unlabelled_retained_direct_match_header_reversed_v127')",
    '_v127_direct_reversed=direct_binary_header_reversed_fixture_pass()',
    'unlabelled_rich_direct_header_reversed_fixture_matches',
]:
    if token not in py:raise RuntimeError('v127 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_direct_match_header_reversed_v127' in cpy
print('v127 reversed retained-header orientation recovery applied')
