from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
for req in ['def confirmed_id_edge_transfer_pair_pass():','def binary_order(rows):','confirmed_id_edge_transfer_rows_moved']:
    if req not in py:raise RuntimeError('v121 prerequisite missing: '+req)

# v119/v120 can repair at most two rows from either edge of a side. A scanner split may be
# displaced by three or four rows. v121 extends the search only within the same global four-row
# repair budget, and any repair deeper than two rows is accepted only when every removed row is
# independently explained by confirmed historical PID ownership (own-side duplicate or opposite-
# side transfer). Unknown/multi-club rows cannot be discarded in a deep repair.
old="""        cuts=((0,0),(1,0),(0,1),(2,0),(1,1),(0,2))
"""
new="""        cuts=((0,0),(1,0),(0,1),(2,0),(1,1),(0,2),(3,0),(2,1),(1,2),(0,3),(4,0),(3,1),(2,2),(1,3),(0,4))
"""
if old not in py:raise RuntimeError('v121 cuts anchor missing')
py=py.replace(old,new,1)

old="""        def classify_removed(removed,kept,own_eid,opposite_eid):
            kept_ids={row_pid(r) for r in kept};kept_ids.discard(None)
            transfer=[];dropped=0
            for rr in removed:
                pid=row_pid(rr)
                if not pid:
                    dropped+=1;continue
                owners=pid_clubs.get(pid,set())
                if len(owners)==1 and own_eid in owners:
                    # Own-club rows are protected unless the exact PID remains in the kept side.
                    if pid in kept_ids:
                        dropped+=1;continue
                    return None
                if len(owners)==1 and opposite_eid in owners:
                    transfer.append(rr);continue
                # Unknown / transfer-ambiguous boundary rows may be discarded exactly as in v117,
                # but they never count as evidence that a boundary transfer happened.
                dropped+=1
            return transfer,dropped
"""
new="""        def classify_removed(removed,kept,own_eid,opposite_eid):
            kept_ids={row_pid(r) for r in kept};kept_ids.discard(None)
            transfer=[];dropped=0;unexplained=0
            for rr in removed:
                pid=row_pid(rr)
                if not pid:
                    dropped+=1;unexplained+=1;continue
                owners=pid_clubs.get(pid,set())
                if len(owners)==1 and own_eid in owners:
                    # Own-club rows are protected unless the exact PID remains in the kept side.
                    if pid in kept_ids:
                        dropped+=1;continue
                    return None
                if len(owners)==1 and opposite_eid in owners:
                    transfer.append(rr);continue
                # Legacy shallow repairs may discard an unknown edge row. Deep repairs may not.
                dropped+=1;unexplained+=1
            return transfer,dropped,unexplained
"""
if old not in py:raise RuntimeError('v121 classify anchor missing')
py=py.replace(old,new,1)

py=py.replace("                ltor,_ldrop=lclass\n", "                ltor,_ldrop,lunknown=lclass\n",1)
py=py.replace("                    rtol,_rdrop=rclass\n", "                    rtol,_rdrop,runknown=rclass\n",1)
old="""                    if not ltor and not rtol:continue
                    ldest_ids={row_pid(x) for x in lkeep};ldest_ids.discard(None)
"""
new="""                    trimmed=ll+lr+rl+rr
                    if trimmed>4:continue
                    # Beyond the previous two-row repair depth, every removed row must have an
                    # independently proven ownership explanation. Never discard unknown rows merely
                    # to make a larger split fit.
                    if trimmed>2 and (lunknown or runknown):
                        diagnostics['confirmed_id_edge_transfer_deep_unexplained_rejected']+=1;continue
                    if not ltor and not rtol and trimmed<=2:continue
                    ldest_ids={row_pid(x) for x in lkeep};ldest_ids.discard(None)
"""
if old not in py:raise RuntimeError('v121 deep guard anchor missing')
py=py.replace(old,new,1)
# The function later recomputes trimmed; preserve that assignment but do not change semantics.

diag="    diagnostics.setdefault('confirmed_id_edge_transfer_current_conflicts_rejected',0)\n"
extra=diag+"    diagnostics.setdefault('confirmed_id_edge_transfer_deep_unexplained_rejected',0)\n    diagnostics.setdefault('confirmed_id_edge_transfer_deep_matches',0)\n"
if "confirmed_id_edge_transfer_deep_matches" not in py:
    if diag not in py:raise RuntimeError('v121 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old_accept="""                diagnostics['confirmed_id_edge_transfer_rows_trimmed']+=state[0]
                if original_score!=repaired_score:diagnostics['confirmed_id_edge_transfer_score_changed_matches']+=1
"""
new_accept="""                diagnostics['confirmed_id_edge_transfer_rows_trimmed']+=state[0]
                if state[0]>2:diagnostics['confirmed_id_edge_transfer_deep_matches']+=1
                if original_score!=repaired_score:diagnostics['confirmed_id_edge_transfer_score_changed_matches']+=1
"""
if old_accept not in py:raise RuntimeError('v121 acceptance anchor missing')
py=py.replace(old_accept,new_accept,1)

handoff="'unlabelled_rich_confirmed_id_edge_transfer_current_conflicts_rejected':member_rich_diag.get('confirmed_id_edge_transfer_current_conflicts_rejected',0),"
extra=handoff+"'unlabelled_rich_confirmed_id_edge_transfer_deep_unexplained_rejected':member_rich_diag.get('confirmed_id_edge_transfer_deep_unexplained_rejected',0),'unlabelled_rich_confirmed_id_edge_transfer_deep_matches':member_rich_diag.get('confirmed_id_edge_transfer_deep_matches',0),"
if 'unlabelled_rich_confirmed_id_edge_transfer_deep_matches' not in py:
    if handoff not in py:raise RuntimeError('v121 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    '(3,0),(2,1),(1,2),(0,3),(4,0),(3,1),(2,2),(1,3),(0,4)',
    'if trimmed>4:continue',
    'if trimmed>2 and (lunknown or runknown):',
    'confirmed_id_edge_transfer_deep_unexplained_rejected',
    'confirmed_id_edge_transfer_deep_matches',
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_transfer_v119')",
]:assert s in cpy,s
print('v121 allows 3-4 row boundary shifts only within four total rows and with fully explained deep removals')