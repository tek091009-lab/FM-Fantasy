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
for req in [
    'def confirmed_id_edge_transfer_pair_pass():',
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_transfer_v119')",
    'repaired_left=list(lkeep)+list(rtol)',
    'repaired_right=list(rkeep)+list(ltor)',
]:
    if req not in py:raise RuntimeError('v120 prerequisite missing: '+req)

# v119 moves a boundary row to the opposite retained team when its stable PID is already
# uniquely confirmed for that opposite club. The initial implementation appended the moved
# row to the end of the destination array. FM match-player arrays carry lineup order: downstream
# materialisation treats the first 11 rows as starters. Appending a genuinely misplaced starter
# can therefore recover the fixture but corrupt that player's appearance/minutes. v120 preserves
# the original binary row ordering by the stat-record offset whenever rows are moved across sides.
old="""                    repaired_left=list(lkeep)+list(rtol)
                    repaired_right=list(rkeep)+list(ltor)
                    if len(repaired_left)<9 or len(repaired_right)<9:continue
"""
new="""                    def binary_order(rows):
                        indexed=list(enumerate(rows))
                        def k(item):
                            i,row=item
                            try:
                                if isinstance(row,dict) and row.get('offset') is not None:
                                    return (0,int(row.get('offset')),i)
                            except Exception:
                                pass
                            # Unknown offsets retain stable pre-repair ordering and sort after
                            # rows with real binary offsets. No inferred starter/bench order.
                            return (1,i,i)
                        return [row for _i,row in sorted(indexed,key=k)]
                    repaired_left=binary_order(list(lkeep)+list(rtol))
                    repaired_right=binary_order(list(rkeep)+list(ltor))
                    if len(repaired_left)<9 or len(repaired_right)<9:continue
"""
if old not in py:raise RuntimeError('v120 v119 repair-order block missing')
py=py.replace(old,new,1)

# Record how many accepted transferred-boundary matches used real binary offsets to preserve
# the destination lineup order. This is a correctness diagnostic for player-level stats.
diag="    diagnostics.setdefault('confirmed_id_edge_transfer_rows_moved',0)\n"
extra=(diag+"    diagnostics.setdefault('confirmed_id_edge_transfer_binary_order_matches',0)\n")
if "diagnostics.setdefault('confirmed_id_edge_transfer_binary_order_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v120 diagnostic anchor missing')
    py=py.replace(diag,extra,1)

old_accept="""                diagnostics['confirmed_id_edge_transfer_rows_moved']+=state[9]
                diagnostics['confirmed_id_edge_transfer_rows_trimmed']+=state[0]
"""
new_accept="""                diagnostics['confirmed_id_edge_transfer_rows_moved']+=state[9]
                moved_rows=list(state[7])+list(state[8])
                if any(isinstance(r,dict) and r.get('offset') is not None for r in moved_rows):
                    diagnostics['confirmed_id_edge_transfer_binary_order_matches']+=1
                diagnostics['confirmed_id_edge_transfer_rows_trimmed']+=state[0]
"""
if old_accept not in py:raise RuntimeError('v120 acceptance diagnostic block missing')
py=py.replace(old_accept,new_accept,1)

handoff="'unlabelled_rich_confirmed_id_edge_transfer_rows_moved':member_rich_diag.get('confirmed_id_edge_transfer_rows_moved',0),"
extra=(handoff+"'unlabelled_rich_confirmed_id_edge_transfer_binary_order_matches':member_rich_diag.get('confirmed_id_edge_transfer_binary_order_matches',0),")
if 'unlabelled_rich_confirmed_id_edge_transfer_binary_order_matches' not in py:
    if handoff not in py:raise RuntimeError('v120 handoff anchor missing')
    py=py.replace(handoff,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'def binary_order(rows):',
    "row.get('offset') is not None",
    'repaired_left=binary_order(list(lkeep)+list(rtol))',
    'repaired_right=binary_order(list(rkeep)+list(ltor))',
    'confirmed_id_edge_transfer_binary_order_matches',
    'unlabelled_rich_confirmed_id_edge_transfer_binary_order_matches',
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_transfer_v119')",
]:assert s in cpy,s
assert 'repaired_left=list(lkeep)+list(rtol)' not in cpy
assert 'repaired_right=list(rkeep)+list(ltor)' not in cpy
print('v120 edge-transfer recovery now preserves FM binary lineup order for moved player rows')
