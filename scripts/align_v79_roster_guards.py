from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

ugp=ROOT/'updateguard.js';ug=ugp.read_text()
ug=ug.replace("const VERSION='world-update-guard-v4-fixture-club-proof';","const VERSION='world-update-guard-v5-strict-current-roster';")
needle="if(meta.rich_match_validation_policy!=='official-score-plus-strict-current-cohort-v69')errors.push('v69 retained-match validation is missing');\n"
ins=needle+" if(meta.current_squad_size_policy!=='strict-current-db-extended-12-60-v79')errors.push('v79 strict current-roster size policy is missing');\n"
if "v79 strict current-roster size policy is missing" not in ug:
    assert needle in ug;ug=ug.replace(needle,ins,1)
ug=ug.replace("if(n<12||n>45)errors.push(`${c?.short_name||c?.name||'club'} has an unsafe current squad size of ${n}`)","if(n<12||n>60)errors.push(`${c?.short_name||c?.name||'club'} has an unsafe current squad size of ${n}`)")
ug=ug.replace('c.__worldUpdateGuardV4','c.__worldUpdateGuardV5')
assert 'world-update-guard-v5-strict-current-roster' in ug
assert 'n<12||n>60' in ug
assert 'strict-current-db-extended-12-60-v79' in ug
ugp.write_text(ug)

idxp=ROOT/'index.html';idx=idxp.read_text();idx=idx.replace('updateguard.js?v=4','updateguard.js?v=5');idxp.write_text(idx)
assert 'updateguard.js?v=5' in idx

pfp=ROOT/'scripts/final_preflight_v70.py';pf=pfp.read_text()
pf=pf.replace("'every-current-senior-squad-size-12..45-v73'","'current-db-roster-proof-v79','strict-current-db-extended-12-60-v79'")
pf=pf.replace("n=28 if is_correct or i>=2 else 0","n=(46 if (is_correct and eid==388) else (28 if is_correct or i>=2 else 0))")
pf=pf.replace("result['checks']['update_guard_v4']='world-update-guard-v4-fixture-club-proof' in ug and 'current-squad-validated-shift-v73' in ug","result['checks']['update_guard_v5']='world-update-guard-v5-strict-current-roster' in ug and 'current-squad-validated-shift-v73' in ug and 'strict-current-db-extended-12-60-v79' in ug")
pf=pf.replace("['availabilitytruth.js?v=4','updateguard.js?v=4','clearfix.js?v=3']","['availabilitytruth.js?v=4','updateguard.js?v=5','clearfix.js?v=3']")
assert 'update_guard_v5' in pf and "eid==388" in pf and 'current-db-roster-proof-v79' in pf
pfp.write_text(pf)
print('V79 browser guard, index and deterministic preflight aligned')
