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
    if "'same_lineup_distinct_regions_preserved':0" not in s:
        needle="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0,'sub40_stat_members':0\n"
        repl="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0,'sub40_stat_members':0,\n        'same_lineup_distinct_regions_preserved':0\n"
        if needle not in s:raise RuntimeError('diagnostics marker missing')
        s=s.replace(needle,repl,1)

    s=s.replace("    cached=[];seen_pairs=set();seen_side_pair_signatures=set()\n","    cached=[];seen_pairs=set()\n",1)
    old=("            sig=(name,tuple(int(x['player_id']) for x in left),tuple(int(x['player_id']) for x in right))\n"
         "            if sig in seen_side_pair_signatures:continue\n"
         "            seen_side_pair_signatures.add(sig)\n"
         "            cached.append({'name':name,'left':left,'right':right,'pk':pk})\n")
    new="            cached.append({'name':name,'left':left,'right':right,'pk':pk})\n"
    if old in s:
        s=s.replace(old,new,1)
    elif 'if sig in seen_side_pair_signatures:continue' in s:
        raise RuntimeError('lineup-only suppression marker changed unexpectedly')

    marker="        cached=compact\n    diagnostics['cached_candidate_pairs']=len(cached)\n"
    if "same_lineup_distinct_regions_preserved']=" not in s:
        extra=("        cached=compact\n"
               "        # Exact/adjacent scanner duplicates are already removed by byte locality.\n"
               "        # Repeated lineup signatures which survive are distinct retained regions.\n"
               "        _lineup_counts=collections.Counter()\n"
               "        for _c in cached:\n"
               "            _l=tuple(sorted(ids_of_row for ids_of_row in (int(x.get('player_id') or 0) for x in _c['left']) if ids_of_row>0))\n"
               "            _r=tuple(sorted(ids_of_row for ids_of_row in (int(x.get('player_id') or 0) for x in _c['right']) if ids_of_row>0))\n"
               "            _lineup_counts[(_c['name'],tuple(sorted((_l,_r))))]+=1\n"
               "        diagnostics['same_lineup_distinct_regions_preserved']=sum(max(0,n-1) for n in _lineup_counts.values())\n"
               "    diagnostics['cached_candidate_pairs']=len(cached)\n")
        if marker not in s:raise RuntimeError('post-normalization marker missing')
        s=s.replace(marker,extra,1)

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

    if 'unlabelled_rich_same_lineup_distinct_regions_preserved' not in py:
        export="'unlabelled_rich_same_lineup_distinct_regions_preserved':member_rich_diag.get('same_lineup_distinct_regions_preserved',0),"
        candidates=[
            "'unlabelled_rich_sub40_stat_members':member_rich_diag.get('sub40_stat_members',0),",
            "'unlabelled_rich_variable_squad_size_candidate_pairs':member_rich_diag.get('variable_squad_size_candidate_pairs',0),",
            "'unlabelled_rich_temporal_transfer_fixture_evidence':member_rich_diag.get('temporal_transfer_fixture_evidence',0),",
            "'unlabelled_rich_near_duplicate_candidate_pairs_soft_collapsed':member_rich_diag.get('near_duplicate_candidate_pairs_soft_collapsed',0),"
        ]
        inserted=False
        for needle in candidates:
            if needle in py:
                py=py.replace(needle,needle+export,1)
                inserted=True
                break
        if not inserted:
            print('v66 warning: legacy payload has no compatible rich-history debug export marker; core decoder patch will still apply')

    assert 'seen_side_pair_signatures' not in py
    assert 'same_lineup_distinct_regions_preserved' in py
    assert 'near_duplicate_candidate_pairs_soft_collapsed' in py
    assert 'if len(stats)<36:continue' in py
    compile(py,'fm_importer.py','exec')
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v66: lineup-only global dedupe removed; byte-local duplicate normalization remains authoritative')


if __name__=='__main__':main()
