from __future__ import annotations
import base64,gzip
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct()->str:
    raw=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(raw)).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed:
        raise RuntimeError('bundle split failed')
    for p,c in zip(PARTS,chunks):
        p.write_text(c+'\n')

def one(s:str,old:str,new:str,label:str)->str:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected one anchor, found {n}')
    return s.replace(old,new,1)

def patch(html:str)->str:
    html=one(html,
"function rulesActive(){return state.teamConfirmed&&(state.firstGameweekPlayed||(state.pointsHistory||[]).length>0)}\nfunction transferChanges()",
"function rulesActive(){return state.teamConfirmed&&(state.firstGameweekPlayed||(state.pointsHistory||[]).length>0)}\nfunction fmMoney(v){return Math.round(Number(v||0)*10)/10}\nfunction fmCurrentPrice(id){return Number(pby(id)?.price||0)}\nfunction fmRecalculateBank(){\n const now=new Set(state.squad||[]);\n if(!state.teamConfirmed){state.bank=fmMoney(100-(state.squad||[]).reduce((s,id)=>s+fmCurrentPrice(id),0));return state.bank}\n const locked=[...(state.lockedSquad||[])],lockedSet=new Set(locked),base=Number(state.lockedBank??state.bank??0);\n const outs=locked.filter(id=>!now.has(id)).reduce((s,id)=>s+fmCurrentPrice(id),0);\n const ins=(state.squad||[]).filter(id=>!lockedSet.has(id)).reduce((s,id)=>s+fmCurrentPrice(id),0);\n state.bank=fmMoney(base+outs-ins);return state.bank\n}\nfunction transferChanges()",
'insert deterministic bank helper')

    html=one(html,
"function addPlayer(id){const p=pby(id);if(p&&canAdd(p)){state.squad.push(id);state.bank=Math.round((Number(state.bank||0)-Number(p.price||0))*10)/10;save();renderAll()}}",
"function addPlayer(id){fmRecalculateBank();const p=pby(id);if(p&&canAdd(p)){state.squad.push(id);fmRecalculateBank();save();renderAll()}}",
'add player')

    html=one(html,
"function removePlayer(id){const p=pby(id);if(!state.squad.includes(id))return;state.squad=state.squad.filter(x=>x!==id);if(p)state.bank=Math.round((Number(state.bank||0)+Number(p.price||0))*10)/10;state.starters=state.starters.filter(x=>x!==id);state.bench=state.bench.filter(x=>x!==id);if(state.captain===id)state.captain=null;if(state.vice===id)state.vice=null;save();closeDrawer();renderAll()}",
"function removePlayer(id){const p=pby(id);if(!state.squad.includes(id))return;state.squad=state.squad.filter(x=>x!==id);fmRecalculateBank();state.starters=state.starters.filter(x=>x!==id);state.bench=state.bench.filter(x=>x!==id);if(state.captain===id)state.captain=null;if(state.vice===id)state.vice=null;save();closeDrawer();renderAll()}",
'remove player')

    html=one(html,
"function renderTransferSummary(){\n const v=validateSquad(),t=transferChanges(),bank=Number(state.bank||0),value=v.spend+bank;",
"function renderTransferSummary(){\n fmRecalculateBank();const v=validateSquad(),t=transferChanges(),bank=Number(state.bank||0),value=v.spend+bank;",
'render-time repair')

    html=one(html,
"if(canAdd(p)){state.squad.push(id);state.bank=Math.round((Number(state.bank||0)-Number(p.price||0))*10)/10;restored.push(id);need--}",
"if(canAdd(p)){state.squad.push(id);fmRecalculateBank();restored.push(id);need--}",
'restore slot accounting')

    html=one(html,
"const original=transferSessionBase();state.squad=[...original.squad];state.bank=Number(original.bank||0);state.starters=[...original.starters];state.bench=[...original.bench];state.captain=original.captain;state.vice=original.vice;save();renderAll()",
"const original=transferSessionBase();state.squad=[...original.squad];fmRecalculateBank();state.starters=[...original.starters];state.bench=[...original.bench];state.captain=original.captain;state.vice=original.vice;save();renderAll()",
'revert accounting')

    html=one(html,
"state.squad=answer.ids;state.bank=Math.round((budget-answer.cost)*10)/10;if(validateSquad().ok)autoXI();save();renderAll()",
"state.squad=answer.ids;fmRecalculateBank();if(validateSquad().ok)autoXI();save();renderAll()",
'autofill accounting')

    html=one(html,
"$('clearDraft').onclick=()=>{for(const id of [...state.squad]){const p=pby(id);if(p)state.bank=Math.round((Number(state.bank||0)+Number(p.price||0))*10)/10}state.squad=[];state.starters=[];state.bench=[];state.captain=null;state.vice=null;save();renderAll()};",
"$('clearDraft').onclick=()=>{state.squad=[];state.starters=[];state.bench=[];state.captain=null;state.vice=null;fmRecalculateBank();save();renderAll()};",
'clear draft accounting')

    html=one(html,
"function confirmEntry(){const name=$('teamNameInput').value.trim();if(!name)return alert('Give your team a name.');const v=validateSquad();",
"function confirmEntry(){const name=$('teamNameInput').value.trim();if(!name)return alert('Give your team a name.');fmRecalculateBank();const v=validateSquad();",
'entry accounting')

    html=one(html,
"function confirmTransfers(){if(!state.teamConfirmed)return;const v=validateSquad(),t=transferChanges();",
"function confirmTransfers(){if(!state.teamConfirmed)return;fmRecalculateBank();const v=validateSquad(),t=transferChanges();",
'confirm accounting')

    html=one(html,
"state.lockedSquad=[...state.squad];if(Number(state.lastTransferRollGW||0)<gw)",
"state.lockedSquad=[...state.squad];state.lockedBank=Number(state.bank||0);if(Number(state.lastTransferRollGW||0)<gw)",
'gameweek bank lock')

    html=one(html,
"fixtureViewGW=(state.teamConfirmed?state.currentGameweek:META.current_gameweek)||1;starViewGW=Math.max(1,META.completed_gameweek||1);teamViewGW=state.teamConfirmed?state.currentGameweek:(META.current_gameweek||1);\n refreshCompetitionUI();refreshClubFilters();save();renderAll();",
"fixtureViewGW=(state.teamConfirmed?state.currentGameweek:META.current_gameweek)||1;starViewGW=Math.max(1,META.completed_gameweek||1);teamViewGW=state.teamConfirmed?state.currentGameweek:(META.current_gameweek||1);\n fmRecalculateBank();refreshCompetitionUI();refreshClubFilters();save();renderAll();",
'import/load accounting repair')

    return html

def main()->None:
    html=reconstruct()
    patched=patch(html)
    if patched==html:
        raise RuntimeError('no changes made')
    repack(patched)
    print('patched transfer bank to deterministic current-price accounting')

if __name__=='__main__':
    main()
