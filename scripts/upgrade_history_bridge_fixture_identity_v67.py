from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
FRAG=Path(__file__).with_name('history_recovery_v53.pyfrag')
OLD="uniq={int(o[0].get('fixture_id') or 0):(o) for o in options}"
NEW="uniq={fixture_identity(o[0]):o for o in options}"


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


def patch_source(s:str)->str:
    if OLD in s:
        s=s.replace(OLD,NEW,1)
    elif NEW not in s:
        raise RuntimeError('single-side bridge uniqueness marker missing')
    # All fixture-consumption/uniqueness paths must use the canonical schema-safe identity.
    if OLD in s:raise RuntimeError('raw fixture-id bridge dedupe remains')
    return s


def main():
    frag=patch_source(FRAG.read_text())
    FRAG.write_text(frag)

    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    rs=py.find('def recover_unlabelled_rich_members(')
    re_=py.find('def recover_game_db_rich_matches(',rs)
    if rs<0 or re_<0:raise RuntimeError('history recovery markers missing')
    py=py[:rs]+frag.rstrip()+'\n\n'+py[re_:]

    assert NEW in py
    assert OLD not in py
    assert "def fixture_identity(f):" in py
    assert "if fixture_identity(f) in used_fixtures" in py
    compile(py,'fm_importer.py','exec')

    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v67: single-side bridge now uses canonical schema-safe fixture identity')


if __name__=='__main__':main()
