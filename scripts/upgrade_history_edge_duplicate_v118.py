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
for req in ['def confirmed_id_edge_trim_pair_pass():','def trim_options(rows,target_eid):','confirmed_id_edge_trim_score_changed_matches']:
    if req not in py:raise RuntimeError('v118 prerequisite missing: '+req)

start=py.find('    def confirmed_id_edge_trim_pair_pass():\n')
end=py.find('    def confirmed_name_transitive_graph_pass():\n',start)
if start<0 or end<0:raise RuntimeError('v118 function bounds missing')
seg=py[start:end]

# v117 deliberately refused to trim any row already proven for the target club. That is correct
# for a unique player row, but too strict for overlapping scanner windows that duplicate the SAME
# player record at an edge. A footballer cannot occupy two separate player rows on one match side;
# if the removed edge PID is still present in the kept rows, retaining both is itself invalid.
old="""                removed=rows[:cut_l]+(rows[len(rows)-cut_r:] if cut_r else [])
                safe=True
                for rr in removed:
                    pid=row_pid(rr)
                    if not pid:continue
                    owners=pid_clubs.get(pid,set())
                    # Never trim away a player uniquely proven for the proposed target club.
                    if len(owners)==1 and target_eid in owners:
                        safe=False;break
                if not safe:continue
                sup=support_ids(ids_of(kept),target_eid)
                if sup:
                    out.append({'trim':cut_l+cut_r,'left_cut':cut_l,'right_cut':cut_r,'support':sup})
"""
new="""                removed=rows[:cut_l]+(rows[len(rows)-cut_r:] if cut_r else [])
                safe=True;target_duplicate_trim=False
                kept_pids={row_pid(kk) for kk in kept};kept_pids.discard(None)
                for rr in removed:
                    pid=row_pid(rr)
                    if not pid:continue
                    owners=pid_clubs.get(pid,set())
                    # A uniquely target-owned row is normally protected. Exception: if the exact
                    # same player ID remains in the repaired side, the edge row is a duplicate
                    # representation and keeping both is structurally impossible for one match side.
                    if len(owners)==1 and target_eid in owners:
                        if pid in kept_pids:
                            target_duplicate_trim=True;continue
                        safe=False;break
                if not safe:continue
                sup=support_ids(ids_of(kept),target_eid)
                if sup:
                    out.append({'trim':cut_l+cut_r,'left_cut':cut_l,'right_cut':cut_r,'support':sup,'target_duplicate_trim':target_duplicate_trim})
"""
if old not in seg:raise RuntimeError('v118 protected-edge anchor missing')
seg=seg.replace(old,new,1)

old2="""                if original_score!=repaired_score:
                    diagnostics['confirmed_id_edge_trim_score_changed_matches']+=1
                if ls['trim'] and rs['trim']:diagnostics['confirmed_id_edge_trim_both_sides']+=1
"""
new2="""                if original_score!=repaired_score:
                    diagnostics['confirmed_id_edge_trim_score_changed_matches']+=1
                if ls.get('target_duplicate_trim') or rs.get('target_duplicate_trim'):
                    diagnostics['confirmed_id_edge_trim_target_duplicate_matches']+=1
                if ls['trim'] and rs['trim']:diagnostics['confirmed_id_edge_trim_both_sides']+=1
"""
if old2 not in seg:raise RuntimeError('v118 success diagnostic anchor missing')
seg=seg.replace(old2,new2,1)
py=py[:start]+seg+py[end:]

diag="    diagnostics.setdefault('confirmed_id_edge_trim_score_changed_matches',0)\n"
if "diagnostics.setdefault('confirmed_id_edge_trim_target_duplicate_matches',0)" not in py:
    if diag not in py:raise RuntimeError('v118 diagnostic anchor missing')
    py=py.replace(diag,diag+"    diagnostics.setdefault('confirmed_id_edge_trim_target_duplicate_matches',0)\n",1)

handoff="'unlabelled_rich_confirmed_id_edge_trim_score_changed_matches':member_rich_diag.get('confirmed_id_edge_trim_score_changed_matches',0),"
if 'unlabelled_rich_confirmed_id_edge_trim_target_duplicate_matches' not in py:
    if handoff not in py:raise RuntimeError('v118 handoff anchor missing')
    py=py.replace(handoff,handoff+"'unlabelled_rich_confirmed_id_edge_trim_target_duplicate_matches':member_rich_diag.get('confirmed_id_edge_trim_target_duplicate_matches',0),",1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
segment=cpy[cpy.index('    def confirmed_id_edge_trim_pair_pass():'):cpy.index('    def confirmed_name_transitive_graph_pass():')]
for s in [
    'kept_pids={row_pid(kk) for kk in kept}',
    'if pid in kept_pids:',
    "'target_duplicate_trim':target_duplicate_trim",
    "diagnostics['confirmed_id_edge_trim_target_duplicate_matches']+=1",
    'confirmed_id_edge_trim_score_changed_matches',
    "register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_id_edge_trim_score_v117')",
]:assert s in segment or s in cpy,s
print('v118 duplicate target-club edge-row repair applied')
