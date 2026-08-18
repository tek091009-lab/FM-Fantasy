from __future__ import annotations
import base64,gzip,re,struct,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
req=["CURRENT_SQUAD_SINGLE_MISSING_POLICY='23-of-24-strong-plus-current-person-proof-v77'",'single_missing_current_db_completion_v77','legacy_exact_uid_header_v77']
for t in req:assert t in py,t
name='fm_importer_v77_test';mod=types.ModuleType(name);mod.__file__=name+'.py';sys.modules[name]=mod
exec(compile(py,name+'.py','exec'),mod.__dict__,mod.__dict__)
Club=mod.__dict__['Club']
clubs={eid:Club(eid,10000+eid,f'C{eid}',f'C{eid}',139) for eid in range(100,124)}
# Build 24 exact current club/team headers; the list decoder itself is monkey-patched so
# this test isolates the V77 decision policy rather than a byte-offset fixture.
db=bytearray(24*128+512);heads={}
for i,(eid,c) in enumerate(clubs.items()):
    p=i*128+16;heads[eid]=p
    db[p:p+4]=struct.pack('<I',eid);db[p+4:p+14]=b'\x00'*10
    db[p+18:p+22]=struct.pack('<I',c.uid);db[p+22:p+26]=struct.pack('<I',c.uid)
db=bytes(db)

def eid_at(head):return struct.unpack_from('<I',db,head)[0]

def strong_reader(_db,head,next_head=None):
    eid=eid_at(head)
    if eid==123:return []
    return [eid*1000+j for j in range(1,29)]

def weak_reader(_db,head,next_head=None):
    eid=eid_at(head)
    if eid!=123:return []
    return [eid*1000+j for j in range(1,29)]
class FakePerson:
    def __init__(self,eid):
        self.eid=eid;self.positions=[0,0,0,0,0,0,0,0,0,0,0,0,20,0];self.current_ability=112

def bind_people(_db,targets):return {int(e):FakePerson(int(e)) for e in targets}
orig_strong=mod.__dict__['read_squad_list'];orig_weak=mod.__dict__['read_squad_list_legacy'];orig_bind=mod.__dict__['bind_target_people']
mod.__dict__['read_squad_list']=strong_reader;mod.__dict__['read_squad_list_legacy']=weak_reader;mod.__dict__['bind_target_people']=bind_people
out,diag=mod.__dict__['scan_first_team_squads'](db,clubs,None)
assert len(out)==24 and all(12<=len(v)<=45 for v in out.values()),(len(out),diag)
assert diag.get('single_missing_completion_attempted') is True,diag
assert diag.get('single_missing_completion_accepted') is True,diag
assert diag.get('missing_club_eids')==[],diag
assert diag.get('single_missing_completion_evidence',{}).get('club_eid')==123,diag
# Safety regression: when TWO clubs lack strong proof, V77 must not complete either one.
def strong_two_missing(_db,head,next_head=None):
    eid=eid_at(head)
    if eid in (122,123):return []
    return [eid*1000+j for j in range(1,29)]
def weak_two(_db,head,next_head=None):
    eid=eid_at(head)
    if eid in (122,123):return [eid*1000+j for j in range(1,29)]
    return []
mod.__dict__['read_squad_list']=strong_two_missing;mod.__dict__['read_squad_list_legacy']=weak_two
out2,diag2=mod.__dict__['scan_first_team_squads'](db,clubs,None)
assert diag2.get('single_missing_completion_attempted') is False,diag2
assert set(diag2.get('missing_club_eids',[]))=={122,123},diag2
# Safety regression: a one-missing weak candidate overlapping an accepted club must be rejected.
mod.__dict__['read_squad_list']=strong_reader
def weak_overlap(_db,head,next_head=None):
    eid=eid_at(head)
    if eid!=123:return []
    return [100*1000+j for j in range(1,29)]
mod.__dict__['read_squad_list_legacy']=weak_overlap
out3,diag3=mod.__dict__['scan_first_team_squads'](db,clubs,None)
assert diag3.get('single_missing_completion_attempted') is True,diag3
assert diag3.get('single_missing_completion_accepted') is False,diag3
assert 123 in diag3.get('missing_club_eids',[]),diag3
rej=diag3.get('single_missing_completion_evidence',{}).get('rejected_candidates',[])
assert any(x.get('reason')=='overlap-with-accepted-current-squad' for x in rej),diag3
mod.__dict__['read_squad_list']=orig_strong;mod.__dict__['read_squad_list_legacy']=orig_weak;mod.__dict__['bind_target_people']=orig_bind
print('V77 regression passed: 23+1 completes, 22+2 blocks, overlapping weak candidate blocks')
