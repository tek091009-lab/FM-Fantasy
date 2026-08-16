from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name=='scripts' else Path.cwd()
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
FRAG=Path(__file__).with_name('history_recovery_v53.pyfrag')


def reconstruct_html()->str:
    b64=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(b64)).decode('utf-8')


def patch_importer(html:str)->str:
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m: raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    start=py.find('def recover_unlabelled_rich_members(')
    end=py.find('def recover_game_db_rich_matches(',start)
    if start<0 or end<0: raise RuntimeError('history recovery function markers not found')
    frag=FRAG.read_text().rstrip()+'\n\n'
    py2=py[:start]+frag+py[end:]
    # Expose the new decoder paths in Export Debug without making them required by old builds.
    needle="'unlabelled_rich_propagation_matches':member_rich_diag.get('propagation_matches',0),"
    extra=(needle+"'unlabelled_rich_cohort_side_labels':member_rich_diag.get('cohort_side_labels',0),"
           "'unlabelled_rich_fixture_identity_matches':member_rich_diag.get('fixture_identity_matches',0),"
           "'unlabelled_rich_single_side_bridge_matches':member_rich_diag.get('single_side_bridge_matches',0),"
           "'unlabelled_rich_identity_rounds':member_rich_diag.get('identity_rounds',0),")
    if needle in py2 and 'unlabelled_rich_fixture_identity_matches' not in py2:
        py2=py2.replace(needle,extra)
    compile(py2,'fm_importer.py','exec')
    new_b64=base64.b64encode(py2.encode()).decode()
    html2=html[:m.start(1)]+new_b64+html[m.end(1):]
    if 'unlabelled_retained_fixture_identity' not in py2: raise RuntimeError('new decoder marker missing')
    return html2


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    n=len(PARTS);step=(len(packed)+n-1)//n
    chunks=[packed[i*step:(i+1)*step] for i in range(n)]
    if len(chunks)<n:chunks += ['']*(n-len(chunks))
    if ''.join(chunks)!=packed: raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


def main():
    html=reconstruct_html();patched=patch_importer(html);repack(patched)
    # Round-trip production validation.
    check=reconstruct_html()
    if check!=patched:raise RuntimeError('repack round-trip mismatch')
    print('History decoder upgraded: strict + cluster + cohort + fixture identity + single-side bridge')

if __name__=='__main__':main()
