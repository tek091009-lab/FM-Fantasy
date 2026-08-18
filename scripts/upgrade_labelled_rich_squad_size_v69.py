from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

NEW_FUNC='''def _rich_pick_two_squads(stats:list[dict[str,Any]]):
    # Preserve the original 20+20 representation as the first/preferred path.
    # Some FM save/schema generations retain 18-22 matchday rows per side; only
    # try those bounded alternatives when the strict 20+20 split cannot be found.
    if len(stats)<36:return None

    def compact(rows):
        if len(rows)<2:return False
        return max((rows[k+1]['offset']-rows[k]['offset'] for k in range(len(rows)-1)),default=0)<1200

    strict=[]
    if len(stats)>=40:
        for j in range(19,len(stats)-20):
            gap=stats[j+1]['offset']-stats[j]['offset']
            left=stats[j-19:j+1];right=stats[j+1:j+21]
            if gap>800 and compact(left) and compact(right):strict.append((gap,j,left,right))
    if strict:
        _,_,left,right=min(strict,key=lambda x:x[2][0]['offset'])
        return left,right

    # Fallback: bounded 18-22 rows per side. Keep the same large inter-team gap
    # and compact-within-team requirements, and prefer shapes closest to 20+20.
    adaptive=[]
    for nl in range(18,23):
        for nr in range(18,23):
            if len(stats)<nl+nr:continue
            for j in range(nl-1,len(stats)-nr):
                gap=stats[j+1]['offset']-stats[j]['offset']
                if gap<=800:continue
                left=stats[j-nl+1:j+1];right=stats[j+1:j+1+nr]
                if not compact(left) or not compact(right):continue
                shape_penalty=abs(nl-20)+abs(nr-20)
                adaptive.append((shape_penalty,left[0]['offset'],gap,nl,nr,left,right))
    if not adaptive:return None
    _pen,_off,_gap,_nl,_nr,left,right=min(adaptive,key=lambda x:(x[0],x[1],-x[2]))
    return left,right
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


def patch_python(py:str)->str:
    pat=r"def _rich_pick_two_squads\(stats:list\[dict\[str,Any\]\]\):\n.*?(?=^def _rich_decorate\()"
    m=re.search(pat,py,re.M|re.S)
    if not m:raise RuntimeError('_rich_pick_two_squads block not found')
    old=m.group(0)
    if 'bounded 18-22 rows per side' in old:return py
    py=py[:m.start()]+NEW_FUNC+'\n\n'+py[m.end():]
    return py


def main():
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    py=patch_python(py)
    assert 'if len(stats)<36:return None' in py
    assert 'for nl in range(18,23):' in py
    assert 'Preserve the original 20+20 representation as the first/preferred path.' in py
    compile(py,'fm_importer_v69.py','exec')
    new_b64=base64.b64encode(py.encode()).decode()
    patched=html[:m.start(1)]+new_b64+html[m.end(1):]
    repack(patched)
    if reconstruct_html()!=patched:raise RuntimeError('repack round-trip mismatch')
    print('v69: labelled rich-match extraction keeps 20+20 first and adds bounded 18-22 side-size fallback')

if __name__=='__main__':main()
