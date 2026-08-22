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

# v135: v134 validates a would-be next retained-match delimiter by requiring its HOME/AWAY IDs
# to look like an ordered fixture in the TARGET league. That is too narrow for an archive member
# containing adjacent cup/friendly/other-competition matches: a genuine next match header can be
# non-league, so v134 skips it and lets the current league scan consume the next game's player rows.
# It also allowed an arbitrary per-fixture constant shift (hid-ph == aid-pa); without a learned
# namespace that condition can admit unrelated metadata pairs that merely have the same numeric
# spacing as one league fixture.
#
# Delimiting does not actually require identifying the NEXT match. It only needs proof that the
# CURRENT payload is already structurally complete before that marker. v135 therefore:
#   1) keeps direct target-league team/club-ID delimiters;
#   2) otherwise accepts a marker only when bytes from this header's proven payload_start up to the
#      marker already produce at least one valid retained squad pair under the live v122-v125
#      structural decoders and an authoritative played score;
#   3) skips markers that occur before a complete current payload;
#   4) removes v134's unlearned arbitrary-delta delimiter shortcut.
# This lets a real cup/friendly header safely stop a league payload without ever attaching that
# other-competition match. No .fm/archive rescan is introduced; all work stays inside cached members.

for prereq in [
    'def _v134_header_pair_matches_fixture_namespace(home_id,away_id):',
    'def _v133_header_embedded_in_stat(raw,hq):',
    'def _v131_scan_stats(raw,start,end):',
    'def _rich_candidate_squad_pairs(stats,played_score_pairs):',
    '_v133_next_safe_header(raw,headers,hi)',
    'payload_start=q+span+12',
    "'header_anchored_fixture_validated_delimiters':0",
]:
    if prereq not in py:raise RuntimeError('v135 prerequisite missing: '+prereq)

diag_anchor="        'header_anchored_fixture_validated_delimiters':0\n"
diag_new=("        'header_anchored_fixture_validated_delimiters':0,\n"
          "        'header_anchored_payload_complete_delimiters':0,\n"
          "        'header_anchored_prepayload_false_delimiters_skipped':0\n")
if "'header_anchored_payload_complete_delimiters':0" not in py:
    if diag_anchor not in py:raise RuntimeError('v135 diagnostics anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

old=r'''    def _v134_header_pair_matches_fixture_namespace(home_id,away_id):
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
new=r'''    _v135_segment_pair_cache={}

    def _v135_header_pair_direct_target(home_id,away_id):
        # Direct target-calendar namespaces are safe delimiter evidence. Deliberately do NOT infer
        # an arbitrary one-match integer shift here: learned namespace transforms belong to v130's
        # fixture attachment logic, not to the weaker question of where one binary payload ends.
        hid=int(home_id);aid=int(away_id)
        if hid<=0 or aid<=0 or hid==aid:return False
        for heid,aeid,_fhs,_fas,f in played:
            fh=int(f.get('home_tid') or 0);fa=int(f.get('away_tid') or 0)
            if (hid,aid)==(fh,fa) and fh>0 and fa>0:return True
            if (hid,aid)==(int(heid),int(aeid)) and int(heid)>0 and int(aeid)>0:return True
        return False

    def _v135_segment_has_complete_pair(raw,start,end):
        # A non-target next header (cup/friendly/other competition or unknown namespace) is still
        # a safe delimiter once the CURRENT segment already contains a structurally valid match
        # payload. Cache by bytes-object identity and bounds to avoid repeating local scans.
        start=max(0,int(start));end=min(len(raw),int(end))
        if end-start<22*140:return False
        key=(id(raw),start,end)
        if key in _v135_segment_pair_cache:return _v135_segment_pair_cache[key]
        try:stats=_v131_scan_stats(raw,start,end)
        except Exception:stats=[]
        ok=False
        if len(stats)>=22:
            try:ok=bool(_rich_candidate_squad_pairs(stats,played_score_pairs))
            except Exception:ok=False
        _v135_segment_pair_cache[key]=ok
        return ok

    def _v135_next_safe_header(raw,headers,hi,payload_start):
        skipped=0
        for hj in range(int(hi)+1,len(headers)):
            nq=int(headers[hj][0]);home_id=int(headers[hj][1]);away_id=int(headers[hj][2])
            if _v133_header_embedded_in_stat(raw,nq):
                skipped+=1;continue
            if _v135_header_pair_direct_target(home_id,away_id):
                diagnostics['header_anchored_fixture_validated_delimiters']+=1
                return nq,skipped
            # The next header does not need to belong to this league. If the current bytes already
            # form a valid old-match squad pair, stopping here cannot truncate that current game.
            if _v135_segment_has_complete_pair(raw,payload_start,nq):
                diagnostics['header_anchored_payload_complete_delimiters']+=1
                return nq,skipped
            skipped+=1
            diagnostics['header_anchored_nonfixture_false_delimiters_skipped']+=1
            diagnostics['header_anchored_prepayload_false_delimiters_skipped']+=1
        return len(raw),skipped
'''
if 'def _v135_next_safe_header(raw,headers,hi,payload_start):' not in py:
    if old not in py:raise RuntimeError('v135 v134 delimiter helper anchor missing')
    py=py.replace(old,new,1)

old_call="                next_q,_v133_skipped=_v133_next_safe_header(raw,headers,hi)\n"
new_call="                next_q,_v133_skipped=_v135_next_safe_header(raw,headers,hi,q+span+12)\n"
if '_v135_next_safe_header(raw,headers,hi,q+span+12)' not in py:
    if old_call not in py:raise RuntimeError('v135 delimiter call anchor missing')
    py=py.replace(old_call,new_call,1)

handoff_anchor="'unlabelled_rich_header_anchored_fixture_validated_delimiters':member_rich_diag.get('header_anchored_fixture_validated_delimiters',0),"
handoff_new=(handoff_anchor+
    "'unlabelled_rich_header_anchored_payload_complete_delimiters':member_rich_diag.get('header_anchored_payload_complete_delimiters',0),"+
    "'unlabelled_rich_header_anchored_prepayload_false_delimiters_skipped':member_rich_diag.get('header_anchored_prepayload_false_delimiters_skipped',0),")
if 'unlabelled_rich_header_anchored_payload_complete_delimiters' not in py:
    if handoff_anchor not in py:raise RuntimeError('v135 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
for token in [
    'def _v135_header_pair_direct_target(home_id,away_id):',
    'def _v135_segment_has_complete_pair(raw,start,end):',
    'def _v135_next_safe_header(raw,headers,hi,payload_start):',
    '_v135_next_safe_header(raw,headers,hi,q+span+12)',
    'header_anchored_payload_complete_delimiters',
    'header_anchored_prepayload_false_delimiters_skipped',
    'def direct_header_anchored_candidate_pass_v131():',
    'register_match(ci,f,rev,leid,reid,source)',
]:
    if token not in py:raise RuntimeError('v135 token missing: '+token)
if 'if hid-ph==aid-pa:return True' in py:
    raise RuntimeError('v135 unsafe unlearned arbitrary-delta delimiter shortcut still present')
if '_v133_next_safe_header(raw,headers,hi)' in py:
    raise RuntimeError('v135 old v134 delimiter call still present')

new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'def _v135_next_safe_header(raw,headers,hi,payload_start):' in cpy
assert 'if hid-ph==aid-pa:return True' not in cpy
assert 'header_anchored_payload_complete_delimiters' in cpy
print('v135 delimits completed retained payloads safely even when the following match is outside the target league')
