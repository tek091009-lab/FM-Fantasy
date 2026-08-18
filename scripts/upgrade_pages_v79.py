from pathlib import Path
p=Path(__file__).resolve().parents[1]/'.github/workflows/pages.yml'
s=p.read_text()
s=s.replace('Preflight V76 clean-rebuild safety','Preflight V79 strict current-roster safety')
s=s.replace('Deep-verify live V76 build','Deep-verify live V79 build')
s=s.replace('Record verified V76 deployment','Record verified V79 deployment')
s=s.replace("python scripts/assert_v76_snapshot_boundary.py\n", "python scripts/assert_v76_snapshot_boundary.py\n          python scripts/assert_v79_strict_extended_roster.py\n",1)
s=s.replace("for k in ['header_pat_runtime_object','name_pool_runtime_probe','league_selector_v72','fixture_mapping_v73_runtime','update_guard_v4']:","for k in ['header_pat_runtime_object','name_pool_runtime_probe','league_selector_v72','fixture_mapping_v73_runtime','update_guard_v5']:")
s=s.replace('deterministic V76 clean-rebuild preflight passed','deterministic V79 strict-roster preflight passed')
s=s.replace('updateguard.js?v=4','updateguard.js?v=5')
s=s.replace('Live index did not expose V76 safety scripts','Live index did not expose V79 safety scripts')
s=s.replace('world-update-guard-v4-fixture-club-proof','world-update-guard-v5-strict-current-roster')
ugcheck="          printf '%s' \"$updateguard\" | grep -q 'current-squad-validated-shift-v73'\n"
if "strict-current-db-extended-12-60-v79" not in s.split(': > /tmp/live_parts.b64')[0]:
    s=s.replace(ugcheck,ugcheck+"          printf '%s' \"$updateguard\" | grep -q 'strict-current-db-extended-12-60-v79'\n",1)
liveassert="          python scripts/assert_v76_snapshot_boundary.py /tmp/live_app.html\n"
if 'assert_v79_strict_extended_roster.py /tmp/live_app.html' not in s:
    s=s.replace(liveassert,liveassert+"          python scripts/assert_v79_strict_extended_roster.py /tmp/live_app.html\n",1)
req="            'v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75',\n"
if "CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'" not in s:
    s=s.replace(req,req+"            \"CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'\",'CURRENT_SQUAD_STRICT_MAX=60','current-db-roster-proof-v79',\n            \"'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY\",\n",1)
s=s.replace("code=compile(py,'fm_importer_live_v76.py','exec'); name='fm_importer_live_v76'; mod=types.ModuleType(name); mod.__file__='fm_importer_live_v76.py';", "code=compile(py,'fm_importer_live_v79.py','exec'); name='fm_importer_live_v79'; mod=types.ModuleType(name); mod.__file__='fm_importer_live_v79.py';")
s=s.replace('deep live V76 verification passed','deep live V79 verification passed')
s=s.replace('v76-dated-append-only-snapshot-live','v79-real-save-strict-roster-live')
s=s.replace('v75-current-db-structural-senior-resolution-no-history','v79-strict-current-db-extended-roster')
s=s.replace('v4-fixture-club-proof','v5-strict-current-roster')
s=s.replace('Record verified V76 Pages deployment','Record verified V79 Pages deployment')
# Add explicit marker fields after fixture db handoff.
needle='  \\"fixture_db_handoff\\": \\"v74-loaded-game-db-bytes\\",\\n'
if 'current_squad_size_policy' not in s[s.find('json="$(printf'):]:
    s=s.replace(needle,needle+'  \\"current_squad_size_policy\\": \\"strict-current-db-extended-12-60-v79\\",\\n  \\"real_save_roster_probe\\": \\"shift132=24/24; strict Portsmouth roster=46; shift131=22/24\\",\\n',1)
p.write_text(s)
# Hard assertions stop a partial upgrader from being committed.
for t in ['updateguard.js?v=5','world-update-guard-v5-strict-current-roster','assert_v79_strict_extended_roster.py /tmp/live_app.html',"CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'",'v79-real-save-strict-roster-live','update_guard_v5']:
    assert t in s,t
assert 'updateguard.js?v=4' not in s
print('Pages V79 verifier upgraded')
