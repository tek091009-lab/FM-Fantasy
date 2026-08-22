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

# v175 source scope: measured gw6 decomposition shows the historical candidate explosion was
# aggregate-source noise: 612 total = 54 retained + 524 news.dat + 34 play_fixture_manager.dat.
# Keep unlabelled rich recovery on isolated retained-match member types only. No .dat filename
# receives authority merely because it contains bytes resembling GAME_MATCH_PLAYER_STATS.
fn = '_rich_is_retained_match_member'
pos = py.find('def ' + fn)
if pos < 0:
    raise RuntimeError('retained-member predicate missing')
end = py.find('\ndef ', pos + 4)
end = len(py) if end < 0 else end
old_block = py[pos:end]
sig = old_block.splitlines()[0]
new_block = sig + "\n    return Path(str(name or '')).suffix.lower() in ('.scm','.apm','.pkm')\n"
py = py[:pos] + new_block + py[end:]

# v175 scanner correction: once a 214-byte record has passed the live structural parser, a
# second physical record cannot begin inside those same 214 bytes. Resuming at +140 re-enters
# 74 already-consumed bytes and can manufacture overlapping false player rows. Resume at the
# physical end of the accepted record; byte-by-byte scanning still resumes immediately after it.
for scan_name in ('_rich_scan_stats', '_rich_scan_stats_fast'):
    spos = py.find('def ' + scan_name)
    if spos < 0:
        raise RuntimeError(f'{scan_name} missing')
    send = py.find('\ndef ', spos + 4)
    send = len(py) if send < 0 else send
    block = py[spos:send]
    if 'p+=140' not in block:
        if 'p += 140' not in block:
            raise RuntimeError(f'{scan_name} no +140 accepted-record advance found')
        block = block.replace('p += 140', 'p += 214')
    else:
        block = block.replace('p+=140', 'p+=214')
    py = py[:spos] + block + py[send:]

marker = (
    "_RICH_NONOVERLAP_V175=1\n"
    "_RICH_NONOVERLAP_POLICY_V175='validated-214-byte-record-resume-at-physical-end'\n"
    "_RICH_SOURCE_SCOPE_V175='retained-match-members-only-scm-apm-pkm'\n"
)
insert = py.find('def ' + fn)
py = py[:insert] + marker + py[insert:]

compile(py, 'fm_importer.py', 'exec')
new_b64 = base64.b64encode(py.encode()).decode('ascii')
html = html[:m.start(1)] + new_b64 + html[m.end(1):]
repack(html)

# Reconstruct and verify the packed artifact, not just the patch source.
chk = reconstruct()
mm = re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"', chk)
assert mm
cpy = base64.b64decode(mm.group(1)).decode('utf-8')
compile(cpy, 'fm_importer.py', 'exec')

pos = cpy.find('def ' + fn); assert pos >= 0
end = cpy.find('\ndef ', pos + 4); end = len(cpy) if end < 0 else end
scope = cpy[pos:end]
assert "('.scm','.apm','.pkm')" in scope
for forbidden in ('news.dat', 'play_fixture_manager.dat', 'player_stats.dat'):
    assert forbidden not in scope, forbidden

for scan_name in ('_rich_scan_stats', '_rich_scan_stats_fast'):
    spos = cpy.find('def ' + scan_name); assert spos >= 0
    send = cpy.find('\ndef ', spos + 4); send = len(cpy) if send < 0 else send
    block = cpy[spos:send]
    assert 'p+=140' not in block and 'p += 140' not in block
    assert ('p+=214' in block) or ('p += 214' in block)

for tok in (
    '_RICH_NONOVERLAP_V175',
    'validated-214-byte-record-resume-at-physical-end',
    'def _rich_stat_record_at',
    'def _rich_candidate_squad_pairs',
    'register_match',
    'fixture_identity',
):
    assert tok in cpy, tok

print('v175 packed importer verified: retained-source scope restored and accepted 214-byte stat records cannot overlap subsequent scans')
