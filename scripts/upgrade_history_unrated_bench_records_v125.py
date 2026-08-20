from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]


def reconstruct()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v125: the old retained GAME_MATCH_PLAYER_STATS validator required rating_raw 400..1000 for
# EVERY 214-byte row. That contradicts the downstream decoder, which explicitly supports unused
# substitutes with no rating. FM can therefore retain a real bench player record with rating_raw=0,
# which the scanner discards before any side reconstruction happens. Preserve the strict rated-row
# path, and additionally accept rating==0 ONLY for a strongly inactive record (no goals/cards/sub
# minutes or match activity). This restores the PID needed to reconstruct the complete historical
# side without allowing active zero-rated garbage through the scanner.
old="""    if not (1<=c[5]<=99 and c[7]==2 and c[20]<=12 and c[21]<=20 and c[50]<=30 and c[51]<=30 and c[52]<=30 and c[56]<=12 and c[63]<=5 and c[64]<=2 and c[67]<=130 and c[71]<=130 and 400<=rating<=1000):
        return None
"""
new="""    base_ok=(1<=c[5]<=99 and c[7]==2 and c[20]<=12 and c[21]<=20 and c[50]<=30 and c[51]<=30 and c[52]<=30 and c[56]<=12 and c[63]<=5 and c[64]<=2 and c[67]<=130 and c[71]<=130)
    rated_ok=400<=rating<=1000
    # Unused retained bench rows can legitimately have no match rating. Require a positive stable
    # player id and a zero-activity signature before accepting rating_raw==0 as that representation.
    inactive_fields=(20,22,23,24,42,43,50,51,52,55,56,63,64,67,71,74,86,87,92,93,94,95,96,97,98,145,146,151,152,157)
    unrated_inactive=(rating==0 and u32(c,1)>0 and all(c[i]==0 for i in inactive_fields))
    if not (base_ok and (rated_ok or unrated_inactive)):
        return None
"""
if old not in py:
    if 'unrated_inactive=(rating==0' not in py:raise RuntimeError('v125 strict rating validator anchor missing')
else:
    py=py.replace(old,new,1)

# Mark the alternate representation so later decoration can never award a phantom 90-minute
# appearance merely because an overlapping candidate window placed an inactive bench row among the
# first eleven positions.
out_anchor="""        'rating_raw':rating,'rating':round(rating/100,1),'offset':p,
    }
"""
out_repl="""        'rating_raw':rating,'rating':round(rating/100,1),'offset':p,
        'unrated_inactive_candidate':bool(unrated_inactive),
    }
"""
if "'unrated_inactive_candidate':bool(unrated_inactive)" not in py:
    if out_anchor not in py:raise RuntimeError('v125 stat output anchor missing')
    py=py.replace(out_anchor,out_repl,1)

# The existing decorator already marks unused post-XI rows as zero minutes. Extend that invariant to
# an explicitly inactive/unrated representation wherever it lands: never turn it into a starter.
dec_anchor="""    for idx,r0 in enumerate(rows):
        r=dict(r0);starter=idx<11
        if starter:
"""
dec_repl="""    for idx,r0 in enumerate(rows):
        r=dict(r0);starter=idx<11
        if r.get('unrated_inactive_candidate'):
            r['appearance']='Unused';r['minutes']=0;r['rating']=None
        elif starter:
"""
if "if r.get('unrated_inactive_candidate'):" not in py:
    if dec_anchor not in py:raise RuntimeError('v125 decorate anchor missing')
    py=py.replace(dec_anchor,dec_repl,1)

# Diagnostics: quantify whether this representation actually exists on the next hard-save rerun.
# Count at scan time so we can distinguish "representation absent" from "found but still unmatched".
scan_anchor="""            if r:
                out.append(r);p+=140;continue
"""
scan_repl="""            if r:
                out.append(r)
                if r.get('unrated_inactive_candidate'):
                    globals()['_RICH_UNRATED_INACTIVE_ROWS']=int(globals().get('_RICH_UNRATED_INACTIVE_ROWS',0))+1
                p+=140;continue
"""
if "_RICH_UNRATED_INACTIVE_ROWS" not in py:
    if scan_anchor not in py:raise RuntimeError('v125 scan anchor missing')
    py=py.replace(scan_anchor,scan_repl,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'unrated_inactive=(rating==0',
    "'unrated_inactive_candidate':bool(unrated_inactive)",
    "if r.get('unrated_inactive_candidate'):",
    "globals()['_RICH_UNRATED_INACTIVE_ROWS']",
]:assert token in cpy,token
print('v125 accepts only zero-rating zero-activity retained bench rows alongside the existing strict rated 214-byte records')
