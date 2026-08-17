from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
FRAG=Path(__file__).with_name('history_recovery_v53.pyfrag')

NEW_HELPER=r'''def _rich_candidate_squad_pairs(stats:list[dict[str,Any]], played_score_pairs:set[tuple[int,int]]|None=None):
    """Return plausible retained home/away stat blocks without assuming one fixed squad size.

    Keep the legacy 20+20 path first. When that exact window is unavailable or its aggregate
    score cannot exist in the already-decoded played calendar, try a bounded 18..22 rows per
    side fallback. The fallback must satisfy the same byte-compactness rules AND an authoritative
    played-score constraint, so it expands schema coverage without creating free-form matches.
    """
    pairs=[]
    if len(stats)<36:return pairs
    played_score_pairs=set(played_score_pairs or ())

    def window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        max_l=max((left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)),default=0)
        max_r=max((right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)),default=0)
        if gap<=500 or max_l>=1500 or max_r>=1500:return None
        return left,right

    def agg(pair):
        left,right=pair
        return (
            sum(int(x.get('goals',0) or 0) for x in left)+sum(int(x.get('own_goals',0) or 0) for x in right),
            sum(int(x.get('goals',0) or 0) for x in right)+sum(int(x.get('own_goals',0) or 0) for x in left)
        )

    for j in range(17,len(stats)-18):
        strict=window(j,20,20)
        if strict:
            pairs.append(strict)
            # If the legacy representation already produces a score that exists in the
            # authoritative league calendar, do not manufacture alternative sizes here.
            if not played_score_pairs or agg(strict) in played_score_pairs:continue

        # Alternate FM schema / competition matchday-list sizes. Only candidates whose score
        # is already known to exist in the decoded played calendar are eligible.
        viable=[]
        for left_n in range(18,23):
            for right_n in range(18,23):
                if left_n==20 and right_n==20:continue
                pair=window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
                viable.append((left_n+right_n,-abs(left_n-right_n),-abs(left_n-20)-abs(right_n-20),pair))
        if viable:
            # Prefer the fullest compact representation, then balanced sides, then sizes nearest
            # the legacy 20. Downstream fixture/player identity still has to validate the match.
            viable.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
            pairs.append(viable[0][3])
    return pairs
'''

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
    if "'variable_squad_size_candidate_pairs':0" not in s:
        needle="        'temporal_transfer_fixture_evidence':0\n"
        repl="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0\n"
        if needle not in s:raise RuntimeError('diagnostics marker missing')
        s=s.replace(needle,repl,1)
    if 'played_score_pairs=' not in s:
        needle="        played.append((heid,aeid,int(f.get('home_score') or 0),int(f.get('away_score') or 0),f))\n\n    cached=[]"
        repl=("        played.append((heid,aeid,int(f.get('home_score') or 0),int(f.get('away_score') or 0),f))\n"
              "    played_score_pairs={(hs,as_) for _h,_a,hs,as_,_f in played}\n"
              "    played_score_pairs|={(as_,hs) for _h,_a,hs,as_,_f in played}\n\n    cached=[]")
        if needle not in s:raise RuntimeError('played-score insertion marker missing')
        s=s.replace(needle,repl,1)
    s=s.replace('pairs=_rich_candidate_squad_pairs(stats)','pairs=_rich_candidate_squad_pairs(stats,played_score_pairs)')
    marker="        diagnostics['candidate_pairs']+=len(pairs)\n"
    if "variable_squad_size_candidate_pairs']+=" not in s:
        if marker not in s:raise RuntimeError('candidate diagnostics marker missing')
        s=s.replace(marker,marker+"        diagnostics['variable_squad_size_candidate_pairs']+=sum(1 for left,right in pairs if len(left)!=20 or len(right)!=20)\n",1)
    FRAG.write_text(s)
    return s.rstrip()+'\n\n'

def main():
    frag=update_fragment()
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')

    hs=py.find('def _rich_candidate_squad_pairs(')
    he=py.find('def _rich_scan_stats_fast(',hs)
    if hs<0 or he<0:raise RuntimeError('rich candidate helper markers missing')
    py=py[:hs]+NEW_HELPER+'\n\n'+py[he:]

    rs=py.find('def recover_unlabelled_rich_members(')
    re_=py.find('def recover_game_db_rich_matches(',rs)
    if rs<0 or re_<0:raise RuntimeError('history recovery markers missing')
    py=py[:rs]+frag+py[re_:]

    # Export the new path count when the existing diagnostics metadata block is present.
    if 'unlabelled_rich_variable_squad_size_candidate_pairs' not in py:
        needles=[
            "'unlabelled_rich_near_duplicate_candidate_pairs_soft_collapsed':member_rich_diag.get('near_duplicate_candidate_pairs_soft_collapsed',0),",
            "'unlabelled_rich_temporal_transfer_fixture_evidence':member_rich_diag.get('temporal_transfer_fixture_evidence',0),"
        ]
        for needle in needles:
            if needle in py:
                py=py.replace(needle,needle+"'unlabelled_rich_variable_squad_size_candidate_pairs':member_rich_diag.get('variable_squad_size_candidate_pairs',0),",1)
                break

    assert 'range(18,23)' in py
    assert '_rich_candidate_squad_pairs(stats,played_score_pairs)' in py
    assert "variable_squad_size_candidate_pairs" in py
    compile(py,'fm_importer.py','exec')
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v64: retained history keeps strict 20+20 and adds score-constrained 18..22 side-size fallback')

if __name__=='__main__':main()
