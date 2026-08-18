from __future__ import annotations
import base64,gzip,re,sys,types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
HEADER_LINE="HEADER_PAT=re.compile(rb'.{3}[\\x00-\\x4c][\\x00-\\xfa]\\x00\\x00\\x00', re.S)"


def reconstruct_html()->str:
    packed=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(packed)).decode('utf-8')


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    if len(chunks)<len(PARTS):chunks+=['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed:raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


def runtime_probe(py:str)->None:
    code=compile(py,'fm_importer_v71.py','exec')
    name='fm_importer_v71_probe'
    mod=types.ModuleType(name);mod.__file__='fm_importer_v71.py';sys.modules[name]=mod
    exec(code,mod.__dict__,mod.__dict__)
    hp=mod.__dict__.get('HEADER_PAT')
    if hp is None or not hasattr(hp,'finditer'):raise RuntimeError('HEADER_PAT runtime object missing')
    fn=mod.__dict__.get('find_name_pool_index')
    if not callable(fn):raise RuntimeError('find_name_pool_index missing')
    try:
        fn(b'\x00'*4096)
    except RuntimeError as e:
        if 'FM name string table not found' not in str(e):raise
    except NameError as e:
        raise RuntimeError('name-pool runtime dependency unresolved') from e
    else:
        raise RuntimeError('synthetic empty DB unexpectedly resolved a name pool')


def main():
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    if HEADER_LINE not in py:
        marker='def _read_string_entry(db:bytes,at:int):'
        pos=py.find(marker)
        if pos<0:raise RuntimeError('_read_string_entry marker missing')
        py=py[:pos]+HEADER_LINE+'\n\n'+py[pos:]
    if py.count('HEADER_PAT=')!=1:raise RuntimeError(f'expected exactly one HEADER_PAT definition, got {py.count("HEADER_PAT=")}')
    if 'for m in HEADER_PAT.finditer(db,pos,search_end):' not in py:raise RuntimeError('name pool scanner no longer uses HEADER_PAT')
    runtime_probe(py)
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v71: restored historical HEADER_PAT and passed real find_name_pool_index runtime dependency probe')

if __name__=='__main__':main()
