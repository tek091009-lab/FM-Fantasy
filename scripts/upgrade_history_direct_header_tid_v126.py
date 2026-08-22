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

# v126: bypass weak historical side-club inference when the retained binary itself carries
# the proven FM match header layout immediately before a candidate player-stat block:
#   03 02 <home-side meta:u32> 02 <HOME TEAM:u32> ...
#   00 03 02 <away-side meta:u32> 02 <AWAY TEAM:u32> ...
# This layout was independently reverse-engineered in the original direct .fm match extractor.
# The header is never trusted by itself: its ordered team pair + candidate's exact reconstructed
# score must identify one unique unused authoritative played fixture, then register_match() remains
# the final attachment gate. All work is done from /tmp/rich_N.bin cached by the existing pass.

# Add diagnostics to the recovery-local dictionary.
diag_anchor="        'same_lineup_distinct_regions_preserved':0\n"
diag_new=("        'same_lineup_distinct_regions_preserved':0,\n"
          "        'direct_header_candidates_scanned':0,'direct_header_pairs_found':0,\n"
          "        'direct_header_fixture_matches':0,'direct_header_ambiguous_rejected':0,\n"
          "        'direct_header_namespace_fixture_tid':0,'direct_header_namespace_club_eid':0,\n"
          "        'direct_header_namespace_club_eid_plus1':0\n")
if "'direct_header_fixture_matches':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v126 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

# Insert the direct binary-header pass after score/fixture/register helpers already exist and
# immediately before the legacy one-side bridge. It is deliberately independent of cluster votes.
pass_anchor="    def single_side_bridge_pass():\n"
pass_code=r'''    _rich_name_indexes=collections.defaultdict(list)
    for _ri,_rn in enumerate(rich_names):_rich_name_indexes[str(_rn)].append(_ri)
    _rich_raw_cache={}

    def _v126_raw_member(index):
        if index in _rich_raw_cache:return _rich_raw_cache[index]
        path=Path(f'/tmp/rich_{index}.bin')
        try:raw=path.read_bytes()
        except Exception:raw=b''
        _rich_raw_cache[index]=raw
        return raw

    def _v126_header_pairs(raw,start):
        # Match headers are local to their player arrays. Keep the probe bounded so a header
        # for an earlier retained match in the same archive member cannot label a distant block.
        if not raw or start<=0:return []
        lo=max(0,int(start)-32768);hi=min(len(raw),int(start))
        out=[];q=lo
        while True:
            q=raw.find(b'\x03\x02',q,hi)
            if q<0:break
            if q+12<=hi and raw[q+6]==2:
                home_tid=int.from_bytes(raw[q+7:q+11],'little')
                marker=raw.find(b'\x00\x03\x02',q+11,min(hi,q+96))
                if marker>=0 and marker+12<=hi and raw[marker+7]==2:
                    away_tid=int.from_bytes(raw[marker+8:marker+12],'little')
                    # Reject zero/self pairs and absurd IDs before fixture comparison.
                    if 0<home_tid<1000000 and 0<away_tid<1000000 and home_tid!=away_tid:
                        distance=int(start)-q
                        if 64<=distance<=32768:out.append((q,home_tid,away_tid,distance))
            q+=1
        return out

    def _v126_fixture_modes(home_id,away_id,hs,as_):
        hits=[]
        for heid,aeid,fhs,fas,f in played:
            if fixture_identity(f) in used_fixtures:continue
            if int(fhs)!=int(hs) or int(fas)!=int(as_):continue
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            modes=[]
            if (home_id,away_id)==(fh,fa):modes.append('fixture_tid')
            if (home_id,away_id)==(int(heid),int(aeid)):modes.append('club_eid')
            # Original direct extractor resolved the header's team value through club_id = tid-1.
            if (home_id,away_id)==(int(heid)+1,int(aeid)+1):modes.append('club_eid_plus1')
            for mode in modes:hits.append((f,heid,aeid,mode))
        return hits

    def direct_binary_header_fixture_pass():
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            diagnostics['direct_header_candidates_scanned']+=1
            start=min(int(c['left'][0]['offset']),int(c['right'][0]['offset']))
            hs,as_=score_of(c)
            raw_hits=[]
            for ri in _rich_name_indexes.get(str(c.get('name') or ''),[]):
                raw=_v126_raw_member(ri)
                for q,home_id,away_id,distance in _v126_header_pairs(raw,start):
                    for f,heid,aeid,mode in _v126_fixture_modes(home_id,away_id,hs,as_):
                        raw_hits.append((fixture_identity(f),distance,q,f,heid,aeid,mode))
                        diagnostics['direct_header_pairs_found']+=1
            if not raw_hits:continue
            # Repeated copies of the same physical header/fixture are harmless. Distinct fixture
            # identities are ambiguity and must never be resolved by nearest-header guessing.
            by_fixture=collections.defaultdict(list)
            for hit in raw_hits:by_fixture[hit[0]].append(hit)
            if len(by_fixture)!=1:
                diagnostics['direct_header_ambiguous_rejected']+=1;continue
            group=next(iter(by_fixture.values()))
            # Within one fixture identity use the closest compatible header only for deterministic
            # provenance; it does not affect which fixture is selected.
            hit=min(group,key=lambda x:(x[1],-x[2]))
            _fid,distance,q,f,heid,aeid,mode=hit
            proposals.append((distance,ci,f,heid,aeid,mode,q))
        added=0
        # Earlier/closer header first; no tuple comparison of fixture dictionaries.
        proposals.sort(key=lambda x:(x[0],x[1]))
        for distance,ci,f,heid,aeid,mode,q in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,False,heid,aeid,'unlabelled_retained_direct_match_header_tid_v126'):
                added+=1;diagnostics['direct_header_fixture_matches']+=1
                diagnostics['direct_header_namespace_'+mode]+=1
        return added

    def single_side_bridge_pass():
'''
if 'def direct_binary_header_fixture_pass():' not in py:
    if pass_anchor not in py:raise RuntimeError('v126 pass insertion anchor missing')
    py=py.replace(pass_anchor,pass_code,1)

# Header evidence is static and stronger than player-club propagation. Run it once before the
# identity fixed-point so any accepted matches immediately seed the existing confirmed cohorts.
loop_anchor="    for _round in range(8):\n"
loop_new="    _v126_direct=direct_binary_header_fixture_pass()\n    if _v126_direct:\n        diagnostics['propagation_matches']+=_v126_direct\n\n    for _round in range(8):\n"
if '_v126_direct=direct_binary_header_fixture_pass()' not in py:
    if loop_anchor not in py:raise RuntimeError('v126 fixed-point anchor missing')
    py=py.replace(loop_anchor,loop_new,1)

# Export diagnostics alongside the existing unlabelled retained-history metrics.
handoff_anchor="'unlabelled_rich_unmatched_cached_pairs':member_rich_diag.get('unmatched_cached_pairs',0),"
handoff_extra=(handoff_anchor+
    "'unlabelled_rich_direct_header_candidates_scanned':member_rich_diag.get('direct_header_candidates_scanned',0),"
    "'unlabelled_rich_direct_header_pairs_found':member_rich_diag.get('direct_header_pairs_found',0),"
    "'unlabelled_rich_direct_header_fixture_matches':member_rich_diag.get('direct_header_fixture_matches',0),"
    "'unlabelled_rich_direct_header_ambiguous_rejected':member_rich_diag.get('direct_header_ambiguous_rejected',0),"
    "'unlabelled_rich_direct_header_namespace_fixture_tid':member_rich_diag.get('direct_header_namespace_fixture_tid',0),"
    "'unlabelled_rich_direct_header_namespace_club_eid':member_rich_diag.get('direct_header_namespace_club_eid',0),"
    "'unlabelled_rich_direct_header_namespace_club_eid_plus1':member_rich_diag.get('direct_header_namespace_club_eid_plus1',0),")
if 'unlabelled_rich_direct_header_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v126 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_extra,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v126_header_pairs(raw,start):',
    "raw.find(b'\\x03\\x02',q,hi)",
    "raw.find(b'\\x00\\x03\\x02',q+11,min(hi,q+96))",
    'def _v126_fixture_modes(home_id,away_id,hs,as_):',
    "modes.append('fixture_tid')",
    "modes.append('club_eid')",
    "modes.append('club_eid_plus1')",
    'def direct_binary_header_fixture_pass():',
    "len(by_fixture)!=1",
    "register_match(ci,f,False,heid,aeid,'unlabelled_retained_direct_match_header_tid_v126')",
    '_v126_direct=direct_binary_header_fixture_pass()',
    'unlabelled_rich_direct_header_fixture_matches',
]:
    if token not in py:raise RuntimeError('v126 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'unlabelled_retained_direct_match_header_tid_v126' in cpy
print('v126 direct retained match-header team-ID recovery applied')
