from __future__ import annotations
import base64, gzip, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = [ROOT/'app'/f'part{i:02d}' for i in range(17)] + [ROOT/'app'/f'fix{i}' for i in range(17, 21)]
TARGETS = ('player_stats.dat', 'play_fixture_manager.dat', 'news.dat')


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

# v174 is a focused correction for a measured same-save history regression.
# Older imports of the same Championship saves scanned 2-3 more archive members and found
# ~10x more retained player-stat evidence. Newer imports explicitly blanket-skip
# player_stats.dat / play_fixture_manager.dat / news.dat before the structural history parser.
# Source names grant ZERO trust here: this patch only makes their bytes eligible for the
# existing GAME_MATCH_PLAYER_STATS -> side -> exact score -> unique authoritative fixture ->
# register_match() chain. Any noisy/non-match source naturally contributes zero accepted games.
key = 'unlabelled_rich_non_retained_member_names'
pos = py.find(key)
if pos < 0:
    raise RuntimeError('v174 non-retained diagnostic anchor missing')
fs = py.rfind('\ndef ', 0, pos)
fs = fs + 1 if fs >= 0 else py.rfind('def ', 0, pos)
fe = py.find('\ndef ', pos)
fe = len(py) if fe < 0 else fe
block = py[fs:fe]

missing = [name for name in TARGETS if name not in block]
if missing:
    raise RuntimeError(f'v174 expected skip-policy names missing: {missing}')
if 'register_match' not in py or 'def _rich_stat_record_at' not in py:
    raise RuntimeError('v174 authoritative historical validation anchors missing')

orig = block
for name in TARGETS:
    esc = re.escape(name)
    for a, b in [
        (f"'{name}',", ''), (f",'{name}'", ''),
        (f'"{name}",', ''), (f',"{name}"', ''),
    ]:
        block = block.replace(a, b)
    block = re.sub(rf"\s*or\s+[^\n;]*?==\s*['\"]{esc}['\"]", '', block)
    block = re.sub(rf"[^\n;]*?==\s*['\"]{esc}['\"]\s+or\s+", '', block)

remaining = [name for name in TARGETS if name in block]
if block == orig or remaining:
    raise RuntimeError(f'v174 could not safely remove all target members from skip policy: {remaining}')

lines = block.splitlines(True)
indent = '    '
if lines and lines[0].lstrip().startswith('def '):
    mm = re.match(r'(\s*)', lines[0])
    indent = (mm.group(1) if mm else '') + '    '
marker = (
    indent + "globals()['_RICH_SOURCE_RESTORATION_V174']=1\n" +
    indent + "globals()['_RICH_SOURCE_RESTORATION_POLICY_V174']='structural-scan-only-no-source-trust'\n" +
    indent + "globals()['_RICH_SOURCE_RESTORATION_MEMBERS_V174']=['player_stats.dat','play_fixture_manager.dat','news.dat']\n"
)
if "_RICH_SOURCE_RESTORATION_V174" not in block:
    lines.insert(1, marker)
    block = ''.join(lines)

py = py[:fs] + block + py[fe:]

# Export a compact audit marker next to the existing retained-history diagnostics.
if 'unlabelled_rich_source_restoration_v174' not in py:
    anchors = ["'unlabelled_rich_non_retained_members_skipped':", "'unlabelled_rich_members_scanned':"]
    ap = next((py.find(a) for a in anchors if py.find(a) >= 0), -1)
    if ap >= 0:
        ls = py.rfind('\n', 0, ap) + 1
        le = py.find('\n', ap)
        le = len(py) if le < 0 else le
        line = py[ls:le]
        ind = re.match(r'\s*', line).group(0)
        extra = (
            ind + "'unlabelled_rich_source_restoration_v174':bool(globals().get('_RICH_SOURCE_RESTORATION_V174',0)),\n" +
            ind + "'unlabelled_rich_source_restoration_policy_v174':globals().get('_RICH_SOURCE_RESTORATION_POLICY_V174'),\n" +
            ind + "'unlabelled_rich_source_restoration_members_v174':globals().get('_RICH_SOURCE_RESTORATION_MEMBERS_V174',[]),\n"
        )
        py = py[:ls] + extra + py[ls:]

compile(py, 'fm_importer.py', 'exec')
new_b64 = base64.b64encode(py.encode()).decode('ascii')
html = html[:m.start(1)] + new_b64 + html[m.end(1):]
repack(html)

# Reconstruct and verify the actual packed importer, not just the patch source.
chk = reconstruct()
mm = re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"', chk)
assert mm
cpy = base64.b64decode(mm.group(1)).decode('utf-8')
compile(cpy, 'fm_importer.py', 'exec')
pos = cpy.find(key)
assert pos >= 0
fs = cpy.rfind('\ndef ', 0, pos)
fs = fs + 1 if fs >= 0 else cpy.rfind('def ', 0, pos)
fe = cpy.find('\ndef ', pos)
fe = len(cpy) if fe < 0 else fe
cblock = cpy[fs:fe]
for name in TARGETS:
    assert name not in cblock, name
for tok in [
    "_RICH_SOURCE_RESTORATION_V174",
    "structural-scan-only-no-source-trust",
    'def _rich_stat_record_at',
    'register_match',
    'fixture_identity',
]:
    assert tok in cpy, tok
print('v174 restores all three measured lost history sources to structural decoding; source names grant no fixture authority')
# retrigger packed build
