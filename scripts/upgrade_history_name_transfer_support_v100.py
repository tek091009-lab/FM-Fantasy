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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

old="""    def confirmed_name_club(rows,ids):
        # Exact aliases only. A name seen for more than one confirmed club is neutralised
        # (transfer, collision or schema ambiguity). Require broad agreement across the side.
        votes=collections.Counter();usable=0;seen=set()
        for row in rows:
            key=_retained_name_key(row)
            if not key or key in seen:continue
            seen.add(key)
            owners=confirmed_retained_name_clubs.get(key,set())
            if len(owners)!=1:
                if len(owners)>1:diagnostics['confirmed_name_ambiguous_aliases']+=1
                continue
            usable+=1;votes[next(iter(owners))]+=1
        if not votes:return None
        ranked=votes.most_common(2);top_eid,top_n=ranked[0];second_n=ranked[1][1] if len(ranked)>1 else 0
        # Seven exact independently confirmed names is intentionally stricter than the
        # ordinary player-ID seed. Also demand >=80% of usable aliases and a four-name margin.
        if top_n<7 or usable<7:return None
        if top_n/max(1,usable)<0.80:return None
        if top_n-second_n<4:return None
        if top_n/max(1,len(rows))<0.32:return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top_eid:
            diagnostics['confirmed_name_conflicts_rejected']+=1;return None
        return top_eid,top_n,usable
"""
new="""    def confirmed_name_club(rows,ids):
        # v100: exact retained names remain a separate representation, but transfers must not
        # erase useful evidence. Names confirmed for multiple clubs are NEVER allowed to choose
        # a club. First establish the club from uniquely-owned exact aliases; only then may a
        # multi-club alias that includes that already-established club reinforce side coverage.
        decisive=collections.Counter();ambiguous=[];seen=set();decisive_usable=0
        for row in rows:
            key=_retained_name_key(row)
            if not key or key in seen:continue
            seen.add(key)
            owners=confirmed_retained_name_clubs.get(key,set())
            if len(owners)==1:
                decisive_usable+=1;decisive[next(iter(owners))]+=1
            elif len(owners)>1:
                ambiguous.append(owners);diagnostics['confirmed_name_ambiguous_aliases']+=1
        if not decisive:return None
        ranked=decisive.most_common(2);top_eid,decisive_top=ranked[0];second_n=ranked[1][1] if len(ranked)>1 else 0
        # Ambiguous/transfer names cannot establish identity. Require a strong independent seed
        # from five unique exact aliases, >=80% agreement and a three-name lead first.
        if decisive_top<5 or decisive_usable<5:return None
        if decisive_top/max(1,decisive_usable)<0.80:return None
        if decisive_top-second_n<3:return None
        transfer_support=sum(1 for owners in ambiguous if top_eid in owners)
        total_support=decisive_top+transfer_support
        # Preserve v99's final seven-name / 32% side-coverage floor. Transfer-compatible aliases
        # can only help satisfy the floor after the club has already been proven independently.
        if total_support<7:return None
        if total_support/max(1,len(rows))<0.32:return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top_eid:
            diagnostics['confirmed_name_conflicts_rejected']+=1;return None
        if transfer_support:diagnostics['confirmed_name_transfer_support_uses']+=transfer_support
        return top_eid,total_support,decisive_usable+len(ambiguous)
"""
if 'confirmed_name_transfer_support_uses' not in py:
    if old not in py:raise RuntimeError('v100 v99 confirmed-name helper anchor missing')
    py=py.replace(old,new,1)

diag="    diagnostics.setdefault('confirmed_name_ambiguous_aliases',0)\n"
if "diagnostics.setdefault('confirmed_name_transfer_support_uses',0)" not in py:
    if diag not in py:raise RuntimeError('v100 diagnostic anchor missing')
    py=py.replace(diag,diag+"    diagnostics.setdefault('confirmed_name_transfer_support_uses',0)\n",1)

handoff="'unlabelled_rich_confirmed_name_ambiguous_aliases':member_rich_diag.get('confirmed_name_ambiguous_aliases',0),"
if 'unlabelled_rich_confirmed_name_transfer_support_uses' not in py:
    if handoff not in py:raise RuntimeError('v100 handoff anchor missing')
    py=py.replace(handoff,handoff+"'unlabelled_rich_confirmed_name_transfer_support_uses':member_rich_diag.get('confirmed_name_transfer_support_uses',0),",1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'decisive=collections.Counter();ambiguous=[]',
    'if decisive_top<5 or decisive_usable<5:return None',
    'if decisive_top/max(1,decisive_usable)<0.80:return None',
    'if decisive_top-second_n<3:return None',
    'transfer_support=sum(1 for owners in ambiguous if top_eid in owners)',
    'if total_support<7:return None',
    "diagnostics['confirmed_name_transfer_support_uses']+=transfer_support",
    'unlabelled_rich_confirmed_name_transfer_support_uses',
    'def confirmed_name_fixture_pass():',
    "'unlabelled_retained_confirmed_exact_name_fixture'"
]:assert s in cpy,s
print('v100 transfer-safe retained exact-name support applied')
