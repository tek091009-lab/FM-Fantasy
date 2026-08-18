from __future__ import annotations
import ast,base64,gzip,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def get_html():
    if len(sys.argv)>1:
        return Path(sys.argv[1]).read_text(encoding='utf-8')
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

html=get_html()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
assert m,'embedded importer missing'
py=base64.b64decode(m.group(1)).decode('utf-8')
assert "FIXTURE_DB_HANDOFF_POLICY='loaded-game-db-bytes-v74'" in py,'V74 loaded DB handoff marker missing'
assert not re.search(r'select_championship_fixtures\(\s*fix\s*,\s*all_clubs\s*,\s*expected_names\s*,\s*requested_league\s*\)',py),'legacy 4-argument browser selector call remains'
tree=ast.parse(py)
defs=[x for x in ast.walk(tree) if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name=='browser_build_payload_from_fs']
assert defs,'browser_build_payload_from_fs missing'
calls=[]
for fn in defs:
    fn_calls=[]
    for node in ast.walk(fn):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='select_championship_fixtures':
            fn_calls.append(node)
            positional_ok=len(node.args)>=5 and isinstance(node.args[4],ast.Name) and node.args[4].id=='db'
            keyword_ok=any(k.arg=='db' and isinstance(k.value,ast.Name) and k.value.id=='db' for k in node.keywords)
            assert positional_ok or keyword_ok,f'fixture selector does not receive loaded db bytes: {ast.unparse(node)}'
    assert fn_calls,f'browser importer definition at line {fn.lineno} has no fixture selector call'
    calls.extend(fn_calls)
lines=py.splitlines()
for fn in defs:
    block='\n'.join(lines[fn.lineno-1:getattr(fn,'end_lineno',fn.lineno)]).replace(' ','')
    assert 'db=dbp.read_bytes()' in block,'browser importer does not read game_db.dat into db'
    assert 'dbp.unlink(' in block,'expected early game_db temp cleanup missing; handoff assertion invalid'
compile(py,'fm_importer_fixture_db_handoff_v74.py','exec')
print(f'fixture_db_handoff_v74_ok=1 browser_defs={len(defs)} selector_calls={len(calls)}')
