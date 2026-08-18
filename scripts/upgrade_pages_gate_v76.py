from pathlib import Path
p=Path('.github/workflows/pages.yml')
s=p.read_text()

def once(old,new):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError(f'expected one anchor, got {n}: {old[:80]!r}')
    s=s.replace(old,new,1)

if 'python scripts/assert_v76_snapshot_boundary.py\n' not in s:
    once('          python scripts/assert_fixture_db_handoff_v74.py\n', '          python scripts/assert_fixture_db_handoff_v74.py\n          python scripts/assert_v76_snapshot_boundary.py\n')
if "snapshotdate.js?v=1" not in s:
    once("              && printf '%s' \"$body\" | grep -q 'worldscorefix.js?v=5'; then", "              && printf '%s' \"$body\" | grep -q 'worldscorefix.js?v=5' \\\n              && printf '%s' \"$body\" | grep -q 'snapshotdate.js?v=1'; then")
if 'snapshotbadge=' not in s:
    once('          identity="$(curl -fsSL --max-time 20 "$base/identityguard.js?v=3&sha=${GITHUB_SHA}")"\n', '          identity="$(curl -fsSL --max-time 20 "$base/identityguard.js?v=3&sha=${GITHUB_SHA}")"\n          snapshotbadge="$(curl -fsSL --max-time 20 "$base/snapshotdate.js?v=1&sha=${GITHUB_SHA}")"\n')
    once("          printf '%s' \"$identity\" | grep -q 'diagnostic-only'\n", "          printf '%s' \"$identity\" | grep -q 'diagnostic-only'\n          printf '%s' \"$snapshotbadge\" | grep -q 'snapshot-date-v1'\n")
if 'assert_v76_snapshot_boundary.py /tmp/live_app.html' not in s:
    once('          python scripts/assert_fixture_db_handoff_v74.py /tmp/live_app.html\n', '          python scripts/assert_fixture_db_handoff_v74.py /tmp/live_app.html\n          python scripts/assert_v76_snapshot_boundary.py /tmp/live_app.html\n')
s=s.replace("print('deterministic V73/V74 clean-rebuild preflight passed')","print('deterministic V75/V76 dated-snapshot preflight passed')")
s=s.replace("Live index did not expose V73/V74 clean-rebuild scripts","Live index did not expose V75/V76 dated-snapshot scripts")
s=s.replace("deep live V73/V74 fixture-club and DB-handoff verification passed","deep live V75/V76 fixture-club, DB-handoff and snapshot verification passed")
s=s.replace('"verification": "v74-fixture-db-handoff-live",','"verification": "v76-dated-append-only-snapshot-live",')
# The marker is inside a shell printf string with escaped quotes.
s=s.replace('\\"verification\\": \\"v74-fixture-db-handoff-live\\",','\\"verification\\": \\"v76-dated-append-only-snapshot-live\\",')
needle='\\"fixture_db_handoff\\": \\"v74-loaded-game-db-bytes-to-every-browser-selector-call\\",'
if needle in s and '\\"snapshot_boundary\\"' not in s:
    s=s.replace(needle, needle+'\\n  \\"current_squad_decoder\\": \\"v75-current-db-structural-senior-resolution-no-history\\",\\n  \\"snapshot_boundary\\": \\"append-only-by-snapshot-date-v1\\",\\n  \\"snapshot_badge\\": \\"snapshot-date-v1\\",\\n  \\"server_history_authority\\": \\"supabase-dated-canonical-merge\\",')
s=s.replace('Record verified v74 Pages deployment','Record verified V76 Pages deployment')
# hard assertions
for t in ['assert_v76_snapshot_boundary.py','snapshotdate.js?v=1','snapshot-date-v1','v76-dated-append-only-snapshot-live','append-only-by-snapshot-date-v1']:
    if t not in s: raise RuntimeError('V76 Pages gate missing '+t)
p.write_text(s)
print('Pages workflow upgraded to V76')
