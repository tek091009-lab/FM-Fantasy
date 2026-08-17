from pathlib import Path
import subprocess,sys

p=Path(__file__).with_name('history_recovery_v53.pyfrag')
s=p.read_text()

# v54 introduced schema-safe fixture identity, but later history-decoder upgrades rebuilt the
# canonical fragment from an older variant and silently reintroduced int(fixture_id or 0).
# Re-apply the structural fallback at the canonical fragment level so future upgrades inherit it.
marker="""    used_fixtures=set();used_candidates=set();out=[]\n\n    def candidate_fixture_options(ci,leid=None,reid=None):\n"""
replacement="""    used_fixtures=set();used_candidates=set();out=[]\n\n    def fixture_identity(f):\n        raw=int(f.get('fixture_id') or 0)\n        if raw>0:return ('id',raw)\n        # Alternate FM schema generations may omit/zero fixture_id. Calendar structure is\n        # already authoritative at this point, so use a composite identity rather than\n        # collapsing every such fixture onto key 0. Include score because this recovery\n        # operates only on played fixtures and include GW/date when available to separate\n        # repeated opponents/doubles.\n        return ('struct',int(f.get('home_tid') or 0),int(f.get('away_tid') or 0),\n                str(f.get('date') or ''),int(f.get('gameweek') or f.get('round') or 0),\n                int(f.get('home_score') or 0),int(f.get('away_score') or 0))\n\n    def candidate_fixture_options(ci,leid=None,reid=None):\n"""
if 'def fixture_identity(f):' not in s:
    if marker not in s: raise RuntimeError('fixture identity insertion marker not found')
    s=s.replace(marker,replacement,1)

old="fid=int(f.get('fixture_id') or 0)"
count=s.count(old)
if count<2:
    raise RuntimeError(f'expected at least two raw fixture-id uses, found {count}')
s=s.replace(old,"fid=fixture_identity(f)")

p.write_text(s)
subprocess.check_call([sys.executable,str(Path(__file__).with_name('upgrade_history_decoder.py'))])
print(f'v57: restored schema-safe fixture identity in canonical fragment ({count} uses replaced)')
