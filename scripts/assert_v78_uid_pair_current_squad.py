from __future__ import annotations
import base64,gzip,re,struct,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
if len(sys.argv)>1:
    html=Path(sys.argv[1]).read_text()
else:
    html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
for t in ["CURRENT_SQUAD_UID_PAIR_POLICY='duplicate-club-uid-team-header-v78'",'uid_pair_header_v78','single_missing_uid_pair_current_db_completion_v78']:
    assert t in py,t
name='fm_importer_v78_test';mod=types.ModuleType(name);mod.__file__=name+'.py';sys.modules[name]=mod
exec(compile(py,name+'.py','exec'),mod.__dict__,mod.__dict__)
Club=mod.__dict__['Club']
clubs={eid:Club(eid,10000+eid,f'C{eid}',f'C{eid}',139) for eid in range(100,124)}
# 23 clubs use the standard eid+zero+uid+uid team header. Club 123 deliberately uses
# a DIFFERENT team entity id but the same duplicated club UID pair, reproducing the schema
# hole V77 could not see.
db=bytearray(24*160+1024);heads={}
for i,(eid,c) in enumerate(clubs.items()):
    p=i*160+32;heads[eid]=p
    team_eid=eid if eid!=123 else 900123
    db[p:p+4]=struct.pack('<I',team_eid);db[p+4:p+14]=b'\x00'*10
    db[p+18:p+22]=struct.pack('<I',c.uid);db[p+22:p+26]=struct.pack('<I',c.uid)
db=bytes(db)

def club_from_uid_head(head):
    if head<0 or head+26>len(db): return None
    uid=struct.unpack_from('<I',db,head+18)[0]
    return next((eid for eid,c in clubs.items() if c.uid==uid),None)

def strong_reader(_db,head,next_head=None):
    eid=club_from_uid_head(head)
    if eid is None or eid==123:return []
    return [eid*1000+j for j in range(1,29)]

def weak_reader(_db,head,next_head=None):
    eid=club_from_uid_head(head)
    if eid!=123:return []
    return [eid*1000+j for j in range(1,29)]
class FakePerson:
    def __init__(self,eid):
        self.eid=eid;self.positions=[0,0,0,0,0,0,0,0,0,0,0,0,20,0];self.current_ability=112

def bind_people(_db,targets):return {int(e):FakePerson(int(e)) for e in targets}
orig_strong=mod.__dict__['read_squad_list'];orig_weak=mod.__dict__['read_squad_list_legacy'];orig_bind=mod.__dict__['bind_target_people']
mod.__dict__['read_squad_list']=strong_reader;mod.__dict__['read_squad_list_legacy']=weak_reader;mod.__dict__['bind_target_people']=bind_people
out,diag=mod.__dict__['scan_first_team_squads'](db,clubs,None)
assert len(out)==24 and all(12<=len(v)<=45 for v in out.values()),diag
assert diag.get('single_missing_completion_attempted') is True,diag
assert diag.get('single_missing_completion_accepted') is True,diag
assert diag.get('missing_club_eids')==[],diag
ev=diag.get('single_missing_completion_evidence') or {}
assert ev.get('method')=='single_missing_uid_pair_current_db_completion_v78',ev
assert ev.get('club_eid')==123,ev
# Safety: if two clubs use alternate team ids, the single-missing path must not activate.
db2=bytearray(db)
for eid in (122,123):
    p=heads[eid];db2[p:p+4]=struct.pack('<I',900000+eid)
db2=bytes(db2)
def strong2(_db,head,next_head=None):
    eid=club_from_uid_head(head)
    if eid in (122,123) or eid is None:return []
    return [eid*1000+j for j in range(1,29)]
mod.__dict__['read_squad_list']=strong2
out2,diag2=mod.__dict__['scan_first_team_squads'](db2,clubs,None)
assert set(diag2.get('missing_club_eids',[]))=={122,123},diag2
assert diag2.get('single_missing_completion_attempted') is False,diag2
mod.__dict__['read_squad_list']=orig_strong;mod.__dict__['read_squad_list_legacy']=orig_weak;mod.__dict__['bind_target_people']=orig_bind
print('V78 regression passed: alternate first-team entity recovered by duplicated club UID; two-missing still blocks')
