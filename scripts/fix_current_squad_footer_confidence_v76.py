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

start=py.find('def read_squad_list(')
end=py.find('\ndef _rich_members_by_club',start)
if start<0 or end<0: raise RuntimeError('current squad reader anchors missing')
legacy=py[start:end]
if 'consistent(cap) and consistent(vice)' not in legacy:
    raise RuntimeError('unexpected current squad reader shape')

strong='''def read_squad_list_legacy(db: bytes, head: int, next_head: int|None=None) -> list[int]:
    """Original squad-list reader retained as a weak fallback for schema compatibility."""
    end=min(next_head or len(db), head+6000)
    at=head+26
    while at+6<end:
        p=db.find(b'\\xff\\xff\\xff\\xff',at,end)
        if p<0:return []
        cnt=u16(db,p+4)
        if 1<=cnt<=80:
            list_at=p+6; list_end=list_at+cnt*4
            if list_end+8<=end:
                vals=[u32(db,list_at+i*4) for i in range(cnt)]
                if all(0<v<3_000_000 for v in vals) and len(set(vals))==cnt:
                    cap=u32(db,list_end); vice=u32(db,list_end+4)
                    consistent=lambda v: v in (0,0xFFFFFFFF) or v in vals
                    asc=sum(1 for a,b in zip(vals[:7],vals[1:8]) if a<b)
                    if (asc>=min(6,max(0,len(vals)-1)) or cap in vals or vice in vals or (consistent(cap) and consistent(vice))):
                        return vals
        at=p+1
    return []


def read_squad_list(db: bytes, head: int, next_head: int|None=None) -> list[int]:
    """Prefer squad blocks with positive structural support.

    v76: a footer where captain and vice are both sentinel values (0/FFFFFFFF) is not,
    by itself, evidence that an arbitrary integer array is a current first-team squad.
    The original permissive decoder is retained separately and may only be used later
    when repeated current-DB blocks independently agree on exactly the same membership.
    """
    end=min(next_head or len(db), head+6000)
    at=head+26
    sentinels=(0,0xFFFFFFFF)
    while at+6<end:
        p=db.find(b'\\xff\\xff\\xff\\xff',at,end)
        if p<0:return []
        cnt=u16(db,p+4)
        if 1<=cnt<=80:
            list_at=p+6; list_end=list_at+cnt*4
            if list_end+8<=end:
                vals=[u32(db,list_at+i*4) for i in range(cnt)]
                if all(0<v<3_000_000 for v in vals) and len(set(vals))==cnt:
                    cap=u32(db,list_end); vice=u32(db,list_end+4)
                    consistent=lambda v: v in sentinels or v in vals
                    asc=sum(1 for a,b in zip(vals[:7],vals[1:8]) if a<b)
                    ordered=asc>=min(6,max(0,len(vals)-1))
                    linked=(cap in vals) or (vice in vals)
                    non_sentinel_footer=(cap not in sentinels) or (vice not in sentinels)
                    coherent_footer=non_sentinel_footer and consistent(cap) and consistent(vice)
                    if ordered or linked or coherent_footer:
                        return vals
        at=p+1
    return []

'''
py=py[:start]+strong+py[end+1:]

old="priority=2 if kind=='strict' else 1"
new="priority={'strict':3,'relaxed_uid':2,'legacy_weak':1}.get(kind,1)"
if old not in py: raise RuntimeError('choose_options priority anchor missing')
py=py.replace(old,new,1)

old_diag="'ambiguous_squad_blocks':[],'consensus_squad_blocks':0}"
new_diag="'ambiguous_squad_blocks':[],'consensus_squad_blocks':0,'weak_sentinel_blocks_seen':0,'weak_sentinel_consensus_accepted':0,'weak_sentinel_singletons_rejected':0}"
if old_diag not in py: raise RuntimeError('squad diag anchor missing')
py=py.replace(old_diag,new_diag,1)

old_byset="""        byset=collections.defaultdict(list)\n        for priority,p,vals,kind in peers:byset[tuple(sorted(set(vals)))].append((p,vals,kind))\n        if len(byset)==1:\n            group=next(iter(byset.values()))\n            if len(group)>1:diag['consensus_squad_blocks']+=1\n            group.sort(key=lambda x:(abs(len(x[1])-28),x[0]))\n            return group[0]\n"""
new_byset="""        byset=collections.defaultdict(list)\n        for priority,p,vals,kind in peers:byset[tuple(sorted(set(vals)))].append((p,vals,kind))\n        if best_priority==1:\n            diag['weak_sentinel_blocks_seen']+=len(peers)\n            # Preserve the original permissive decoder, but never trust one weak block alone.\n            # Two or more separate current-DB blocks must independently agree on membership.\n            if len(byset)!=1 or len(peers)<2:\n                diag['weak_sentinel_singletons_rejected']+=1\n                return None\n        if len(byset)==1:\n            group=next(iter(byset.values()))\n            if len(group)>1:diag['consensus_squad_blocks']+=1\n            if best_priority==1:diag['weak_sentinel_consensus_accepted']+=1\n            group.sort(key=lambda x:(abs(len(x[1])-28),x[0]))\n            return group[0]\n"""
if old_byset not in py: raise RuntimeError('choose_options byset anchor missing')
py=py.replace(old_byset,new_byset,1)

old_strict="""            vals=read_squad_list(db,p,nxt)\n            if vals:options.append((p,vals,kind))\n"""
new_strict="""            vals=read_squad_list(db,p,nxt)\n            if vals:options.append((p,vals,kind))\n            else:\n                weak=read_squad_list_legacy(db,p,nxt)\n                if weak:options.append((p,weak,'legacy_weak'))\n"""
if old_strict not in py: raise RuntimeError('strict squad call anchor missing')
py=py.replace(old_strict,new_strict,1)

old_relaxed="""            vals=read_squad_list(db,p,None)\n            if vals:options.append((p,vals,'relaxed_uid'))\n"""
new_relaxed="""            vals=read_squad_list(db,p,None)\n            if vals:options.append((p,vals,'relaxed_uid'))\n            else:\n                weak=read_squad_list_legacy(db,p,None)\n                if weak:options.append((p,weak,'legacy_weak'))\n"""
if old_relaxed not in py: raise RuntimeError('relaxed squad call anchor missing')
py=py.replace(old_relaxed,new_relaxed,1)

py=py.replace("'policy':'strict_current_db_membership_only_v68'","'policy':'strict_current_db_membership_with_consensus_only_legacy_footer_v76'",1)
marker="CURRENT_SQUAD_FOOTER_POLICY='positive-structure-first-consensus-only-legacy-v76'"
if marker not in py:
    future='from __future__ import annotations\n'
    if future not in py: raise RuntimeError('future import anchor missing')
    py=py.replace(future,future+marker+'\n',1)

compile(py,'fm_importer_v76.py','exec')
tree=ast.parse(py)
fn={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
assert 'read_squad_list' in fn and 'read_squad_list_legacy' in fn and 'scan_first_team_squads' in fn
assert marker in py
assert "weak_sentinel_consensus_accepted" in py
assert "priority={'strict':3,'relaxed_uid':2,'legacy_weak':1}.get(kind,1)" in py

new_b64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('v76: current squad reader now requires positive structural support; original sentinel-footer decoder retained as repeated-consensus-only fallback')
