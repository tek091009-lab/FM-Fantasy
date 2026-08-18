from pathlib import Path
p=Path('.github/workflows/pages.yml');s=p.read_text()
repls={
'Preflight V76 clean-rebuild safety':'Preflight V78 clean-rebuild safety',
"          python scripts/assert_v76_snapshot_boundary.py\n":"          python scripts/assert_v76_snapshot_boundary.py\n          python scripts/assert_v78_uid_pair_current_squad.py\n",
"          print('deterministic V76 clean-rebuild preflight passed')":"          print('deterministic V78 clean-rebuild preflight passed')",
'Deep-verify live V76 build':'Deep-verify live V78 build',
'Live index did not expose V76 safety scripts':'Live index did not expose V78 safety scripts',
"          python scripts/assert_v76_snapshot_boundary.py /tmp/live_app.html\n":"          python scripts/assert_v76_snapshot_boundary.py /tmp/live_app.html\n          python scripts/assert_v78_uid_pair_current_squad.py /tmp/live_app.html\n",
"            'v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75',":"            'v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75',\n            \"CURRENT_SQUAD_UID_PAIR_POLICY='duplicate-club-uid-team-header-v78'\",'uid_pair_header_v78','single_missing_uid_pair_current_db_completion_v78',",
"          print('deep live V76 verification passed')":"          print('deep live V78 verification passed')",
'Record verified V76 deployment':'Record verified V78 deployment',
'\\"verification\\": \\"v76-dated-append-only-snapshot-live\\"':'\\"verification\\": \\"v78-current-team-uid-pair-plus-dated-snapshot-live\\"',
'\\"current_squad_decoder\\": \\"v75-current-db-structural-senior-resolution-no-history\\"':'\\"current_squad_decoder\\": \\"v78-v75-structural-plus-uid-pair-current-team-fallback\\"',
'\\"snapshot_boundary\\": \\"append-only-by-snapshot-date-v1\\"':'\\"current_squad_uid_pair\\": \\"duplicate-club-uid-team-header-v78\\",\\n  \\"snapshot_boundary\\": \\"append-only-by-snapshot-date-v1\\"',
'Record verified V76 Pages deployment':'Record verified V78 Pages deployment',
}
for a,b in repls.items():
    if a not in s: raise RuntimeError('V78 pages anchor missing: '+a[:100])
    s=s.replace(a,b,1)
p.write_text(s)
print('Pages gate upgraded to V78')
