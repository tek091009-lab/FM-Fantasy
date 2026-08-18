from pathlib import Path
p=Path('.github/workflows/pages.yml')
s=p.read_text()
repls={
'Preflight V76 clean-rebuild safety':'Preflight V77 clean-rebuild safety',
"          python scripts/assert_v76_snapshot_boundary.py\n":"          python scripts/assert_v76_snapshot_boundary.py\n          python scripts/assert_v77_single_missing_current_squad.py\n",
"          print('deterministic V76 clean-rebuild preflight passed')":"          print('deterministic V77 clean-rebuild preflight passed')",
'Deep-verify live V76 build':'Deep-verify live V77 build',
"Live index did not expose V76 safety scripts":"Live index did not expose V77 safety scripts",
"            'v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75',":"            'v75-current-db-structural-senior-resolution-no-history','_choose_current_squad_option_v75','paired_uid_v75','current_person_senior_quality_v75',\n            \"CURRENT_SQUAD_SINGLE_MISSING_POLICY='23-of-24-strong-plus-current-person-proof-v77'\",'single_missing_current_db_completion_v77','legacy_exact_uid_header_v77','overlap-with-accepted-current-squad','insufficient-current-person-proof',",
"          print('deep live V76 verification passed')":"          print('deep live V77 verification passed')",
'Record verified V76 deployment':'Record verified V77 deployment',
'\\"verification\\": \\"v76-dated-append-only-snapshot-live\\"':'\\"verification\\": \\"v77-single-missing-current-squad-plus-dated-snapshot-live\\"',
'\\"current_squad_decoder\\": \\"v75-current-db-structural-senior-resolution-no-history\\"':'\\"current_squad_decoder\\": \\"v77-v75-structural-plus-23of24-current-person-proof\\"',
'\\"snapshot_boundary\\": \\"append-only-by-snapshot-date-v1\\"':'\\"current_squad_completion\\": \\"23-of-24-strong-plus-current-person-proof-v77\\",\\n  \\"snapshot_boundary\\": \\"append-only-by-snapshot-date-v1\\"',
'Record verified V76 Pages deployment':'Record verified V77 Pages deployment',
}
for a,b in repls.items():
    if a not in s:raise RuntimeError('pages v77 anchor missing: '+a[:100])
    s=s.replace(a,b,1)
p.write_text(s)
print('Pages gate upgraded to V77')
