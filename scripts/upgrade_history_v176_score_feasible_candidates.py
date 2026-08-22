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

# v176: a retained 20+20 scanner window whose aggregate score is impossible for EVERY
# authoritative played league fixture cannot be the target historical league match.  The
# alternate 18..22 path already enforces this score feasibility rule; the legacy 20+20 path
# did not, so impossible windows were still fed into side clustering/player identity and could
# pollute the very evidence used to identify the real retained blocks.  Quarantine them before
# identity inference, but continue trying alternate squad sizes at the same boundary.
old_sig = "def _rich_candidate_squad_pairs(stats:list[dict[str,Any]], played_score_pairs:set[tuple[int,int]]|None=None):"
new_sig = "def _rich_candidate_squad_pairs(stats:list[dict[str,Any]], played_score_pairs:set[tuple[int,int]]|None=None, diagnostics:dict[str,Any]|None=None):"
if old_sig not in block:
    if new_sig not in block:
        raise RuntimeError('candidate function signature not recognised')
else:
    block = block.replace(old_sig, new_sig, 1)

needle = """    pairs=[]\n    if len(stats)<36:return pairs\n    played_score_pairs=set(played_score_pairs or ())\n"""
replacement = """    pairs=[]\n    if diagnostics is not None:\n        diagnostics.setdefault('strict_20x20_windows_seen_v176',0)\n        diagnostics.setdefault('strict_score_feasible_pairs_v176',0)\n        diagnostics.setdefault('strict_score_impossible_pairs_quarantined_v176',0)\n    if len(stats)<36:return pairs\n    played_score_pairs=set(played_score_pairs or ())\n"""
if replacement not in block:
    if needle not in block:
        raise RuntimeError('candidate function prologue not recognised')
    block = block.replace(needle, replacement, 1)

old_strict = """        strict=window(j,20,20)\n        if strict:\n            pairs.append(strict)\n            # If the legacy representation already produces a score that exists in the\n            # authoritative league calendar, do not manufacture alternative sizes here.\n            if not played_score_pairs or agg(strict) in played_score_pairs:continue\n"""
new_strict = """        strict=window(j,20,20)\n        if strict:\n            strict_score=agg(strict)\n            if diagnostics is not None:\n                diagnostics['strict_20x20_windows_seen_v176']+=1\n            # A target-league historical match must have a score that exists in the already\n            # authoritative played calendar (both orientations are supplied by the caller).\n            # Keep feasible legacy 20+20 blocks exactly as before. Impossible-score blocks are\n            # retained only as a diagnostic count and MUST NOT teach side/player identity.\n            if not played_score_pairs or strict_score in played_score_pairs:\n                pairs.append(strict)\n                if diagnostics is not None:\n                    diagnostics['strict_score_feasible_pairs_v176']+=1\n                continue\n            if diagnostics is not None:\n                diagnostics['strict_score_impossible_pairs_quarantined_v176']+=1\n"""
if new_strict not in block:
    if old_strict not in block:
        raise RuntimeError('legacy strict 20+20 branch not recognised')
    block = block.replace(old_strict, new_strict, 1)

py = py[:pos] + block + py[end:]

# Wire diagnostics into the one production recovery call. Backwards-compatible optional arg
# means any other helper/test callers keep working without modification.
call_old = "pairs=_rich_candidate_squad_pairs(stats,played_score_pairs)"
call_new = "pairs=_rich_candidate_squad_pairs(stats,played_score_pairs,diagnostics)"
if call_new not in py:
    if call_old not in py:
        raise RuntimeError('production candidate builder call not found')
    py = py.replace(call_old, call_new, 1)

marker = (
    "_RICH_SCORE_FEASIBILITY_V176=1\n"
    "_RICH_SCORE_FEASIBILITY_POLICY_V176='impossible-target-league-score-quarantined-before-side-identity'\n"
)
insert = py.find('def ' + fn)
if '_RICH_SCORE_FEASIBILITY_V176=1' not in py:
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

assert '_RICH_SCORE_FEASIBILITY_V176=1' in cpy
assert "impossible-target-league-score-quarantined-before-side-identity" in cpy
assert "pairs=_rich_candidate_squad_pairs(stats,played_score_pairs,diagnostics)" in cpy

p = cpy.find('def _rich_candidate_squad_pairs'); assert p >= 0
q = cpy.find('\ndef ', p + 4); q = len(cpy) if q < 0 else q
cb = cpy[p:q]
for tok in (
    "strict_score=agg(strict)",
    "strict_score in played_score_pairs",
    "strict_score_impossible_pairs_quarantined_v176",
    "strict_score_feasible_pairs_v176",
):
    assert tok in cb, tok
# The old unsafe order must be gone: strict 20+20 cannot be appended before its score check.
unsafe = "if strict:\n            pairs.append(strict)"
assert unsafe not in cb

# v175 non-overlap/source scoping and final authoritative match gate must survive.
for tok in (
    '_RICH_NONOVERLAP_V175=1',
    "_RICH_SOURCE_SCOPE_V175='retained-match-members-only-scm-apm-pkm'",
    'register_match',
    'fixture_identity',
):
    assert tok in cpy, tok

print('v176 packed importer verified: impossible-score strict 20+20 windows cannot pollute historical side identity')
