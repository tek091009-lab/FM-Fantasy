from __future__ import annotations
import ast,base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

# game_db.dat is intentionally read into memory and unlinked early. The fixture selector must
# consume those already-loaded bytes. Patch EVERY browser call, not merely the first matching
# string in the module.
legacy=re.compile(r'select_championship_fixtures\(\s*fix\s*,\s*all_clubs\s*,\s*expected_names\s*,\s*requested_league\s*\)')
py,n=legacy.subn('select_championship_fixtures(fix,all_clubs,expected_names,requested_league,db)',py)

marker="FIXTURE_DB_HANDOFF_POLICY='loaded-game-db-bytes-v74'"
if marker not in py:
    future='from __future__ import annotations\n'
    if future not in py: raise RuntimeError('future import anchor missing')
    py=py.replace(future,future+marker+'\n',1)

def verify_runtime_path(src:str):
    tree=ast.parse(src)
    defs=[x for x in ast.walk(tree) if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name=='browser_build_payload_from_fs']
    if not defs: raise RuntimeError('browser_build_payload_from_fs missing')
    checked=0
    bad=[]
    for fn in defs:
        for node in ast.walk(fn):
            if not isinstance(node,ast.Call): continue
            if not isinstance(node.func,ast.Name) or node.func.id!='select_championship_fixtures': continue
            checked+=1
            positional_ok=(len(node.args)>=5 and isinstance(node.args[4],ast.Name) and node.args[4].id=='db')
            keyword_ok=any(k.arg=='db' and isinstance(k.value,ast.Name) and k.value.id=='db' for k in node.keywords)
            if not (positional_ok or keyword_ok): bad.append((fn.lineno,node.lineno,ast.unparse(node)))
    if checked==0: raise RuntimeError('browser importer never calls select_championship_fixtures')
    if bad: raise RuntimeError('browser fixture selector does not receive loaded db bytes: '+repr(bad))
    lines=src.splitlines()
    text='\n'.join('\n'.join(lines[fn.lineno-1:getattr(fn,'end_lineno',fn.lineno)]) for fn in defs)
    if 'db=dbp.read_bytes()' not in text.replace(' ',''):
        raise RuntimeError('browser importer no longer loads game_db.dat bytes into db')
    if 'dbp.unlink(' not in text.replace(' ',''):
        raise RuntimeError('expected early temp-file cleanup path missing; handoff regression test is no longer meaningful')
    return len(defs),checked

defs,calls=verify_runtime_path(py)
compile(py,'fm_importer_v74.py','exec')
if legacy.search(py): raise RuntimeError('legacy 4-argument browser selector call remains')
if marker not in py: raise RuntimeError('V74 marker missing')

new_b64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print(f'v74: patched_legacy_calls={n}; browser_defs={defs}; selector_calls_verified={calls}; loaded db bytes are handed to every browser selector call')
