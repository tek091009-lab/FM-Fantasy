from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
FRAG=Path(__file__).with_name('history_recovery_v53.pyfrag')


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


def update_fragment()->str:
    s=FRAG.read_text()
    # v64 supports 18..22 rows per side, so the enclosing retained-member gate must allow
    # the smallest valid 18+18 representation through to candidate construction.
    if "'sub40_stat_members':0" not in s:
        needle="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0\n"
        repl="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0,'sub40_stat_members':0\n"
        if needle not in s:raise RuntimeError('diagnostics marker missing')
        s=s.replace(needle,repl,1)
    old="        if len(stats)<40:continue\n        diagnostics['members_with_stats']+=1\n"
    new=("        if len(stats)<36:continue\n"
         "        if len(stats)<40:diagnostics['sub40_stat_members']+=1\n"
         "        diagnostics['members_with_stats']+=1\n")
    if old in s:
        s=s.replace(old,new,1)
    elif "if len(stats)<36:continue" not in s:
        raise RuntimeError('retained-member gate marker missing')
    FRAG.write_text(s)
    return s.rstrip()+'\n\n'


def main():
    frag=update_fragment()
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    rs=py.find('def recover_unlabelled_rich_members(')
    re_=py.find('def recover_game_db_rich_matches(',rs)
    if rs<0 or re_<0:raise RuntimeError('history recovery markers missing')
    py=py[:rs]+frag+py[re_:]

    if 'unlabelled_rich_sub40_stat_members' not in py:
        needles=[
            "'unlabelled_rich_variable_squad_size_candidate_pairs':member_rich_diag.get('variable_squad_size_candidate_pairs',0),",
            "'unlabelled_rich_temporal_transfer_fixture_evidence':member_rich_diag.get('temporal_transfer_fixture_evidence',0),"
        ]
        for needle in needles:
            if needle in py:
                py=py.replace(needle,needle+"'unlabelled_rich_sub40_stat_members':member_rich_diag.get('sub40_stat_members',0),",1)
                break

    assert 'if len(stats)<36:continue' in py
    assert "sub40_stat_members" in py
    assert 'range(18,23)' in py
    compile(py,'fm_importer.py','exec')
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v65: retained member gate now admits valid 18+18 through 19+20 variable-side representations')


if __name__=='__main__':main()
