from __future__ import annotations
import base64,gzip,re,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def load_html():
    if len(sys.argv)>1:
        return Path(sys.argv[1]).read_text(encoding='utf-8')
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
html=load_html();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
for t in ["CURRENT_SQUAD_SIZE_POLICY='strict-current-db-extended-12-60-v79'",'CURRENT_SQUAD_STRICT_MAX=60','current-db-roster-proof-v79',"'current_squad_size_policy':CURRENT_SQUAD_SIZE_POLICY"]:assert t in py,t
name='fm_importer_v79_roster_test';mod=types.ModuleType(name);mod.__file__=name+'.py';sys.modules[name]=mod
exec(compile(py,name+'.py','exec'),mod.__dict__,mod.__dict__)
choose=mod.__dict__['_choose_current_squad_option_v75']
def diag():return {'rejected_options':0,'consensus_squad_blocks':0,'overlap_union_squad_blocks':0,'resolved_squad_blocks':[],'current_person_resolution_errors':[],'ambiguous_squad_blocks':[]}
vals46=list(range(10001,10047))
a=choose(b'',388,[(100,vals46,'strict')],diag());assert a and len(a[1])==46,a
b=choose(b'',388,[(100,vals46,'paired_uid_v75')],diag());assert b is None,b
c=choose(b'',388,[(100,list(range(10001,10062)),'strict')],diag());assert c is None,c
Club=mod.__dict__['Club'];evidence=mod.__dict__['_fixture_shift_current_squad_evidence']
correct=[299,302,304,309,312,315,318,335,364,374,375,380,388,389,390,397,402,410,413,420,422,423,428,429]
team_ids={eid+132 for eid in correct};allids=set(correct+[x+1 for x in correct]);clubs={eid:Club(eid,eid+1000,f'C{eid}',f'C{eid}',139) for eid in allids}
orig=mod.__dict__['scan_first_team_squads']
def fake(_db,selected,_rich=None):
    is_correct=set(selected)==set(correct);out={}
    for i,eid in enumerate(selected):
        if is_correct:n=46 if eid==388 else 28
        else:n=28 if i>=2 else 1
        out[eid]=list(range(eid*1000,eid*1000+n))
    return out,{'policy':'strict_current_db_membership_only_v68','missing_club_eids':[]}
mod.__dict__['scan_first_team_squads']=fake
x=evidence(team_ids,clubs,132,b'x');y=evidence(team_ids,clubs,131,b'x')
mod.__dict__['scan_first_team_squads']=orig
assert x['safe_squad_clubs']==24,x
assert x['squad_sizes']['C388']==46,x
assert x['current_squad_size_policy']=='strict-current-db-extended-12-60-v79',x
assert y['safe_squad_clubs']==22,y
print('V79 strict-roster regression passed: real-save shape 46 accepted only via strict current DB; shift132=24/24, shift131=22/24')
