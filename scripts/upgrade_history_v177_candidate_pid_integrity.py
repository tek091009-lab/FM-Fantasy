from __future__ import annotations
import base64, gzip, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = [ROOT/'app'/f'part{i:02d}' for i in range(17)] + [ROOT/'app'/f'fix{i}' for i in range(17, 21)]


def reconstruct() -> str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')


def repack(html: str) -> None:
    packed = base64.b64encode(gzip.compress(html.encode('utf-8'), compresslevel=9, mtime=0)).decode()
    step = (len(packed) + len(PARTS) - 1) // len(PARTS)
    chunks = [packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks) == packed
    for p, c in zip(PARTS, chunks):
        p.write_text(c + '\n')


html = reconstruct()
m = re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"', html)
if not m:
    raise RuntimeError('FM_PY_SOURCE_B64 not found')
py = base64.b64decode(m.group(1)).decode('utf-8')

fn = '_rich_candidate_squad_pairs'
pos = py.find('def ' + fn)
if pos < 0:
    raise RuntimeError('candidate squad-pair builder missing')
end = py.find('\ndef ', pos + 4)
end = len(py) if end < 0 else end
block = py[pos:end]

# v177: stable player identity gives us a hard structural invariant that is stronger than
# score/club heuristics. A genuine historical match cannot contain the same player twice on
# one team, nor can the same stable player ID appear for both teams. Previously a byte-window
# satisfying only gap/size rules could enter side clustering even when it violated this
# invariant, poisoning the player/cohort graph used by the hard 16/91 case.
prologue_old = """        diagnostics.setdefault('strict_score_impossible_pairs_quarantined_v176',0)\n    if len(stats)<36:return pairs\n"""
prologue_new = """        diagnostics.setdefault('strict_score_impossible_pairs_quarantined_v176',0)\n        diagnostics.setdefault('candidate_nonpositive_pid_quarantined_v177',0)\n        diagnostics.setdefault('candidate_duplicate_pid_within_side_quarantined_v177',0)\n        diagnostics.setdefault('candidate_cross_side_pid_quarantined_v177',0)\n        diagnostics.setdefault('candidate_pid_integrity_pass_v177',0)\n    if len(stats)<36:return pairs\n"""
if prologue_new not in block:
    if prologue_old not in block:
        raise RuntimeError('v176 diagnostic prologue not found; apply v176 first')
    block = block.replace(prologue_old, prologue_new, 1)

agg_end = """    def agg(pair):\n        left,right=pair\n        return (\n            sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right),\n            sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left)\n        )\n\n"""
helper = agg_end + """    def pid_integrity(pair):\n        left,right=pair\n        lp=[int(x.get('player_id') or 0) for x in left]\n        rp=[int(x.get('player_id') or 0) for x in right]\n        if any(x<=0 for x in lp) or any(x<=0 for x in rp):\n            if diagnostics is not None: diagnostics['candidate_nonpositive_pid_quarantined_v177']+=1\n            return False\n        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp):\n            if diagnostics is not None: diagnostics['candidate_duplicate_pid_within_side_quarantined_v177']+=1\n            return False\n        if set(lp)&set(rp):\n            if diagnostics is not None: diagnostics['candidate_cross_side_pid_quarantined_v177']+=1\n            return False\n        if diagnostics is not None: diagnostics['candidate_pid_integrity_pass_v177']+=1\n        return True\n\n"""
if 'def pid_integrity(pair):' not in block:
    if agg_end not in block:
        raise RuntimeError('aggregate score helper not found')
    block = block.replace(agg_end, helper, 1)

strict_old = """        strict=window(j,20,20)\n        if strict:\n            strict_score=agg(strict)\n"""
strict_new = """        strict=window(j,20,20)\n        if strict and not pid_integrity(strict):\n            # Do not let an impossible 20+20 player identity window suppress alternate\n            # 18..22 interpretations at the same physical team boundary.\n            strict=None\n        if strict:\n            strict_score=agg(strict)\n"""
if strict_new not in block:
    if strict_old not in block:
        raise RuntimeError('v176 strict branch not found')
    block = block.replace(strict_old, strict_new, 1)

alt_old = """                pair=window(j,left_n,right_n)\n                if not pair:continue\n                if played_score_pairs and agg(pair) not in played_score_pairs:continue\n                viable.append((left_n+right_n,-abs(left_n-right_n),-abs(left_n-20)-abs(right_n-20),pair))\n"""
alt_new = """                pair=window(j,left_n,right_n)\n                if not pair:continue\n                if not pid_integrity(pair):continue\n                if played_score_pairs and agg(pair) not in played_score_pairs:continue\n                viable.append((left_n+right_n,-abs(left_n-right_n),-abs(left_n-20)-abs(right_n-20),pair))\n"""
if alt_new not in block:
    if alt_old not in block:
        raise RuntimeError('alternate squad-size branch not found')
    block = block.replace(alt_old, alt_new, 1)

py = py[:pos] + block + py[end:]
marker = (
    "_RICH_CANDIDATE_PID_INTEGRITY_V177=1\n"
    "_RICH_CANDIDATE_PID_INTEGRITY_POLICY_V177='positive-unique-within-side-disjoint-across-sides-before-identity'\n"
)
insert = py.find('def ' + fn)
if '_RICH_CANDIDATE_PID_INTEGRITY_V177=1' not in py:
    py = py[:insert] + marker + py[insert:]

compile(py, 'fm_importer.py', 'exec')
new_b64 = base64.b64encode(py.encode()).decode('ascii')
html = html[:m.start(1)] + new_b64 + html[m.end(1):]
repack(html)

# Verify the actual packed artifact.
chk = reconstruct()
mm = re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"', chk)
assert mm
cpy = base64.b64decode(mm.group(1)).decode('utf-8')
compile(cpy, 'fm_importer.py', 'exec')
assert '_RICH_CANDIDATE_PID_INTEGRITY_V177=1' in cpy
assert "positive-unique-within-side-disjoint-across-sides-before-identity" in cpy
p = cpy.find('def _rich_candidate_squad_pairs'); assert p >= 0
q = cpy.find('\ndef ', p + 4); q = len(cpy) if q < 0 else q
cb = cpy[p:q]
for tok in (
    'def pid_integrity(pair):',
    "candidate_duplicate_pid_within_side_quarantined_v177",
    "candidate_cross_side_pid_quarantined_v177",
    "candidate_nonpositive_pid_quarantined_v177",
    'if strict and not pid_integrity(strict):',
    'if not pid_integrity(pair):continue',
):
    assert tok in cb, tok
# v175/v176 and final fixture authority must remain.
for tok in (
    '_RICH_NONOVERLAP_V175=1',
    '_RICH_SCORE_FEASIBILITY_V176=1',
    'strict_score_impossible_pairs_quarantined_v176',
    'register_match',
    'fixture_identity',
):
    assert tok in cpy, tok

# Pure structural sanity checks for the invariant itself.
def integrity(lp, rp):
    if any(x<=0 for x in lp+rp): return False
    if len(set(lp))!=len(lp) or len(set(rp))!=len(rp): return False
    if set(lp)&set(rp): return False
    return True
assert integrity(list(range(1,21)), list(range(21,41)))
assert not integrity(list(range(1,20))+[5], list(range(21,41)))
assert not integrity(list(range(1,21)), list(range(20,40)))
assert not integrity([0]+list(range(2,21)), list(range(21,41)))

print('v177 packed importer verified: impossible stable-PID candidate windows cannot teach historical side identity')
