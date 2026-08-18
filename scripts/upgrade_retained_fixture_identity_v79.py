from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
def reconstruct(): return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode();step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))];chunks+=['']*(len(PARTS)-len(chunks));assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')
html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode()

# V79-A: the labelled retained-member decoder used to collapse every identical
# team/score/lineup signature inside a member, even when the objects lived in
# distant byte regions.  Keep the generic-label duplicate protection, but make
# it byte-local so two genuine matches that reused the same XI survive.
old="""    # De-duplicate if a generic label appears inside a longer label.\n    out=[];seen=set()\n    for m in matches:\n        k=(m['competition'],m['home_tid'],m['away_tid'],m['home_score'],m['away_score'],\n           tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))\n        if k in seen:continue\n        seen.add(k);out.append(m)\n    return out\n"""
new="""    # V79: de-duplicate only byte-local duplicate label representations.\n    # A repeated XI/score in a materially different retained region is a real\n    # candidate and must reach the fixture-binding safeguards downstream.\n    out=[];seen_by_signature=collections.defaultdict(list)\n    for m in matches:\n        k=(m['competition'],m['home_tid'],m['away_tid'],m['home_score'],m['away_score'],\n           tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))\n        off=int(m.get('offset') or 0)\n        if any(abs(off-prev)<=4096 for prev in seen_by_signature[k]):continue\n        seen_by_signature[k].append(off);out.append(m)\n    return out\n"""
if old in py: py=py.replace(old,new,1)
elif 'V79: de-duplicate only byte-local duplicate label representations.' not in py: raise RuntimeError('labelled retained dedupe anchor missing')

# V79-B: browser-level first-pass de-dupe had the same global-lineup issue.
old2="""    rich_raw=[]; seen=set()\n    for m in raw:\n        key=(m['home'],m['away'],m['home_score'],m['away_score'],tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))\n        if key in seen: continue\n        seen.add(key); rich_raw.append(m)\n"""
new2="""    rich_raw=[]; seen_by_signature=collections.defaultdict(list)\n    for m in raw:\n        key=(m.get('competition'),m['home'],m['away'],m['home_score'],m['away_score'],tuple(x['player_id'] for x in m['home_players']),tuple(x['player_id'] for x in m['away_players']))\n        loc=(str(m.get('source_member') or ''),int(m.get('offset') or 0))\n        # Only collapse the same representation when it is byte-local inside the\n        # same archive member. Cross-member candidates are preserved until exact\n        # authoritative fixture binding can determine whether they duplicate.\n        if any(prev[0]==loc[0] and abs(prev[1]-loc[1])<=4096 for prev in seen_by_signature[key]): continue\n        seen_by_signature[key].append(loc); rich_raw.append(m)\n"""
if old2 in py: py=py.replace(old2,new2,1)
elif 'Cross-member candidates are preserved until exact' not in py: raise RuntimeError('browser retained dedupe anchor missing')

# V79-C: exact fixture binding is the final authority.  Multiple byte/archive
# representations of one fixture must never double a player's fantasy history.
# Identical core player-stat signatures collapse; materially conflicting ones
# quarantine that fixture rather than guessing which representation is right.
old3="""    out=[]\n    for mid,m in enumerate(rich,1):\n"""
new3="""    out=[];fixture_seen={};fixture_conflicts=set();exact_fixture_duplicates=0\n    for mid,m in enumerate(rich,1):\n"""
if old3 in py: py=py.replace(old3,new3,1)
elif 'exact_fixture_duplicates=0' not in py: raise RuntimeError('join init anchor missing')
old4="""        # bonus/fpl point fields are shared row dicts referenced in arrays.\n        out.append(mm)\n    return out\n"""
new4="""        # bonus/fpl point fields are shared row dicts referenced in arrays.\n        # V79: one authoritative fixture may have several retained representations.\n        # Collapse only exact core-stat agreement; quarantine conflicting versions.\n        def _side_sig(arr):\n            return tuple((str(x.get('player_id')),int(x.get('goals') or 0),int(x.get('assists') or 0),\n                          int(x.get('yellow_cards') or 0),int(x.get('red_cards') or 0),\n                          int(x.get('sub_off') or 0),int(x.get('sub_on') or 0),int(x.get('rating_raw') or 0)) for x in arr)\n        fsig=(_side_sig(mm.get('home_players',[])),_side_sig(mm.get('away_players',[])))\n        fid=int(fix['fixture_id'])\n        if fid in fixture_conflicts:continue\n        if fid not in fixture_seen:\n            fixture_seen[fid]=(fsig,len(out));out.append(mm)\n        elif fixture_seen[fid][0]==fsig:\n            exact_fixture_duplicates+=1\n        else:\n            fixture_conflicts.add(fid);idx=fixture_seen[fid][1];out[idx]=None\n    out=[x for x in out if x is not None]\n    join_rich_matches.last_diag={'exact_fixture_duplicates_collapsed':exact_fixture_duplicates,\n                                 'conflicting_fixture_representations_quarantined':len(fixture_conflicts),\n                                 'conflicting_fixture_ids':sorted(fixture_conflicts)[:40]}\n    return out\n"""
if old4 in py: py=py.replace(old4,new4,1)
elif 'conflicting_fixture_representations_quarantined' not in py: raise RuntimeError('join append anchor missing')

# Expose the correctness diagnostics in browser payload metadata.
meta_anchor="'rich_matches':len(rich_matches),"
meta_insert="'rich_fixture_exact_duplicates_collapsed':getattr(join_rich_matches,'last_diag',{}).get('exact_fixture_duplicates_collapsed',0),'rich_fixture_conflicting_representations_quarantined':getattr(join_rich_matches,'last_diag',{}).get('conflicting_fixture_representations_quarantined',0),'rich_fixture_conflicting_ids':getattr(join_rich_matches,'last_diag',{}).get('conflicting_fixture_ids',[]),"+meta_anchor
if meta_insert not in py:
    if py.count(meta_anchor)<1: raise RuntimeError('meta anchor missing')
    # browser payload is the last occurrence and is the path under test here.
    pos=py.rfind(meta_anchor);py=py[:pos]+meta_insert+py[pos+len(meta_anchor):]

for token in ['V79: de-duplicate only byte-local duplicate label representations.','exact_fixture_duplicates=0','conflicting_fixture_representations_quarantined','rich_fixture_conflicting_representations_quarantined']:
    assert token in py,token
compile(py,'fm_importer_v79.py','exec')
html=html[:m.start(1)]+base64.b64encode(py.encode()).decode()+html[m.end(1):];repack(html);assert reconstruct()==html
print('V79 retained representation identity safeguards applied')
