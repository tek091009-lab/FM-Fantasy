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

# v134: v133 protects header-anchored scans from a false 03 02 / 00 03 02 marker only when
# that marker lies physically inside a validated 214-byte player-stat record. A header-looking
# sequence in ordinary retained-match metadata can still terminate the current payload early.
# Require a delimiter candidate to carry an ordered HOME/AWAY numeric pair compatible with at
# least one authoritative played league fixture. Compatibility deliberately supports arbitrary
# constant entity-namespace deltas (same delta on HOME and AWAY), so this does not hard-code a
# particular FM schema shift. It changes payload delimiting only; fixture attachment remains under
# the existing exact-score/unique-fixture/register_match gates.

for prereq in [
    'def _v133_header_embedded_in_stat(raw,hq):',
    'def _v133_next_safe_header(raw,headers,hi):',
    'for hj in range(int(hi)+1,len(headers)):',
    'nq=int(headers[hj][0])',
    "'header_anchored_embedded_false_delimiters_skipped':0",
    'for heid,aeid,fhs,fas,f in played:',
]:
    if prereq not in py:raise RuntimeError('v134 prerequisite missing: '+prereq)

diag_anchor="        'header_anchored_extended_after_false_delimiter_scans':0\n"
diag_new=("        'header_anchored_extended_after_false_delimiter_scans':0,\n"
          "        'header_anchored_nonfixture_false_delimiters_skipped':0,\n"
          "        'header_anchored_fixture_validated_delimiters':0\n")
if "'header_anchored_nonfixture_false_delimiters_skipped':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v134 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=r'''    def _v133_next_safe_header(raw,headers,hi):
        skipped=0
        for hj in range(int(hi)+1,len(headers)):
            nq=int(headers[hj][0])
            if _v133_header_embedded_in_stat(raw,nq):
                skipped+=1;continue
            return nq,skipped
        return len(raw),skipped
'''
new=r'''    def _v134_header_pair_matches_fixture_namespace(home_id,away_id):
        # A genuine retained match header should name two teams that form an ordered fixture in
        # this competition. FM schemas can put those teams in different integer namespaces, so
        # accept direct fixture IDs, direct club EIDs, or any equal HOME/AWAY constant delta to
        # one authoritative fixture pair. One arbitrary ID fitting independently is not enough.
        hid=int(home_id);aid=int(away_id)
        if hid<=0 or aid<=0 or hid==aid:return False
        for heid,aeid,_fhs,_fas,f in played:
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            pairs=((fh,fa),(int(heid),int(aeid)))
            for ph,pa in pairs:
                if ph<=0 or pa<=0:continue
                if (hid,aid)==(ph,pa):return True
                if hid-ph==aid-pa:return True
        return False

    def _v133_next_safe_header(raw,headers,hi):
        skipped=0
        for hj in range(int(hi)+1,len(headers)):
            nq=int(headers[hj][0]);home_id=int(headers[hj][1]);away_id=int(headers[hj][2])
            if _v133_header_embedded_in_stat(raw,nq):
                skipped+=1;continue
            if not _v134_header_pair_matches_fixture_namespace(home_id,away_id):
                skipped+=1
                diagnostics['header_anchored_nonfixture_false_delimiters_skipped']+=1
                continue
            diagnostics['header_anchored_fixture_validated_delimiters']+=1
            return nq,skipped
        return len(raw),skipped
'''
if 'def _v134_header_pair_matches_fixture_namespace(home_id,away_id):' not in py:
    if old not in py:raise RuntimeError('v134 v133 delimiter helper anchor missing')
    py=py.replace(old,new,1)

handoff_anchor="'unlabelled_rich_header_anchored_extended_after_false_delimiter_scans':member_rich_diag.get('header_anchored_extended_after_false_delimiter_scans',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_nonfixture_false_delimiters_skipped':member_rich_diag.get('header_anchored_nonfixture_false_delimiters_skipped',0),"+
    "'unlabelled_rich_header_anchored_fixture_validated_delimiters':member_rich_diag.get('header_anchored_fixture_validated_delimiters',0),")
if 'unlabelled_rich_header_anchored_nonfixture_false_delimiters_skipped' not in py:
    if handoff_anchor not in py:raise RuntimeError('v134 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v134_header_pair_matches_fixture_namespace(home_id,away_id):',
    'if hid-ph==aid-pa:return True',
    "diagnostics['header_anchored_nonfixture_false_delimiters_skipped']+=1",
    "diagnostics['header_anchored_fixture_validated_delimiters']+=1",
    'unlabelled_rich_header_anchored_nonfixture_false_delimiters_skipped',
    'def direct_header_anchored_candidate_pass_v131():',
    'register_match(ci,f,rev,leid,reid,source)',
]:
    if token not in py:raise RuntimeError('v134 token missing: '+token)

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'def _v134_header_pair_matches_fixture_namespace(home_id,away_id):' in cpy
assert 'header_anchored_nonfixture_false_delimiters_skipped' in cpy
print('v134 requires retained next-header delimiters to encode an authoritative fixture-compatible team pair')
