from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# v57 made fixture identity schema-safe, but two later proposal-application guards still
# compared raw integer fixture_id values against used_fixtures, whose members are now
# ('id', n) / ('struct', ...) tuples. That mismatch can let already-consumed fixtures
# survive proposal ordering and reduce recovery on unknown schemas. Use the canonical
# fixture_identity helper everywhere fixture consumption is checked.
old="int(f.get('fixture_id') or 0) in used_fixtures"
count=s.count(old)
if count != 2:
    raise RuntimeError(f'expected exactly two raw used-fixture guards, found {count}')
s=s.replace(old,"fixture_identity(f) in used_fixtures")

# Protect the invariant so future decoder upgrades cannot silently mix key types again.
if old in s:
    raise RuntimeError('raw fixture-id used_fixtures guard remains')
if s.count('fixture_identity(f) in used_fixtures') != 2:
    raise RuntimeError('proposal guards were not converted to canonical fixture identity')
if s.count('fid=fixture_identity(f)') < 2:
    raise RuntimeError('loop-level canonical fixture identity checks are missing')

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print(f'v58: unified consumed-fixture guards on schema-safe fixture identity ({count} guards replaced)')
