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

# v174: restore the exact .dat sources whose exclusion correlates with a measured collapse
# in retained historical evidence on the same saves.  Current production does not blacklist
# the names individually; it admits only .scm/.apm/.pkm in _rich_is_retained_match_member(),
# which excludes every .dat file before the structural parser ever sees its bytes.
# The three restored filenames receive ZERO match authority. They merely become eligible for
# the existing GAME_MATCH_PLAYER_STATS -> side -> exact score -> unique fixture ->
# register_match() validation chain.
fn = '_rich_is_retained_match_member'
pos = py.find('def ' + fn)
if pos < 0:
    raise RuntimeError('v174 retained-member predicate missing')
end = py.find('\ndef ', pos + 4)
end = len(py) if end < 0 else end
block = py[pos:end]
if "('.scm','.apm','.pkm')" not in block and '(\'.scm\',\'.apm\',\'.pkm\')' not in block:
    raise RuntimeError('v174 expected retained extension policy missing')
if any(name in block for name in TARGETS):
    raise RuntimeError('v174 target already present in retained-member predicate')

old_return = "return Path(str(name or '')).suffix.lower() in ('.scm','.apm','.pkm')"
if old_return not in block:
    raise RuntimeError('v174 exact retained-member return line missing')
new_return = (
    "n=str(name or '').replace('\\\\','/').rsplit('/',1)[-1].lower()\n"
    "    if n in ('player_stats.dat','play_fixture_manager.dat','news.dat'):\n"
    "        return True\n"
    "    return Path(n).suffix.lower() in ('.scm','.apm','.pkm')"
)
block = block.replace(old_return, new_return, 1)
py = py[:pos] + block + py[end:]

# Machine-readable debug policy.  This is intentionally evidence metadata only.
marker = "_RICH_SOURCE_RESTORATION_V174=1\n_RICH_SOURCE_RESTORATION_POLICY_V174='exact-dat-admission-structural-validation-no-source-trust'\n_RICH_SOURCE_RESTORATION_MEMBERS_V174=['player_stats.dat','play_fixture_manager.dat','news.dat']\n"
insert = py.find('def ' + fn)
py = py[:insert] + marker + py[insert:]

# Add debug export beside the existing unlabelled-rich scan counters when possible.
if 'unlabelled_rich_source_restoration_v174' not in py:
    anchors = ["'unlabelled_rich_non_retained_members_skipped':", "'unlabelled_rich_members_scanned':"]
    ap = next((py.find(a) for a in anchors if py.find(a) >= 0), -1)
    if ap >= 0:
        ls = py.rfind('\n', 0, ap) + 1
        line = py[ls:py.find('\n', ap)]
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

# Verify the actual packed importer, not merely the source patch.
chk = reconstruct()
mm = re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"', chk)
assert mm
cpy = base64.b64decode(mm.group(1)).decode('utf-8')
compile(cpy, 'fm_importer.py', 'exec')
pos = cpy.find('def ' + fn); assert pos >= 0
end = cpy.find('\ndef ', pos + 4); end = len(cpy) if end < 0 else end
cblock = cpy[pos:end]
for name in TARGETS:
    assert name in cblock, name
for tok in [
    '_RICH_SOURCE_RESTORATION_V174',
    'exact-dat-admission-structural-validation-no-source-trust',
    'def _rich_stat_record_at',
    'register_match',
    'fixture_identity',
]:
    assert tok in cpy, tok
print('v174 admits the three measured lost .dat sources to structural history decoding; filenames grant no fixture authority')
