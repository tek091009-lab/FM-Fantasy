from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct_html()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed: raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

def patch_python(py:str)->str:
    # Preserve FM name components where their pool IDs still exist. Match the current
    # Person constructor structurally so this layers beside newer canonical naming logic.
    if 'person_obj.first_name=fore.get(first)' not in py:
        rx=re.compile(r'(?m)^(\s*)out\[eid\]=Person\(([^\n]+)\)\s*$')
        m=rx.search(py)
        if not m: raise RuntimeError('bind_target_people Person constructor not found')
        ind,args=m.group(1),m.group(2)
        replacement=(f"{ind}person_obj=Person({args})\n"
                     f"{ind}person_obj.first_name=fore.get(first)\n"
                     f"{ind}person_obj.surname_name=sur.get(surname)\n"
                     f"{ind}person_obj.common_name_id=None if com==0xFFFFFFFF else com\n"
                     f"{ind}person_obj.first_name_id=first\n"
                     f"{ind}person_obj.surname_name_id=surname\n"
                     f"{ind}out[eid]=person_obj")
        py=py[:m.start()]+replacement+py[m.end():]

    # Carry legal/component identity alongside whichever public/display string the current
    # production naming strategy already selected. Do not replace or recalculate it.
    if "'legal_name':person.name" not in py:
        candidates=[
            "'name':person.display_name,'display_name':person.display_name,'public_name':person.display_name,",
            "'name':display_name,'display_name':display_name,'public_name':display_name,",
            "'name':public_name,'display_name':public_name,'public_name':public_name,"
        ]
        anchor=next((a for a in candidates if a in py),None)
        if not anchor: raise RuntimeError('build_players public-name payload anchor not found')
        addition=(anchor+"'legal_name':person.name,'first_name':getattr(person,'first_name',None),"
                  "'surname_name':getattr(person,'surname_name',None),'common_name':person.common_name,"
                  "'first_name_id':getattr(person,'first_name_id',None),'surname_name_id':getattr(person,'surname_name_id',None),"
                  "'common_name_id':getattr(person,'common_name_id',None),'identity_components_preserved':True,")
        py=py.replace(anchor,addition,1)

    # Export exact discipline evidence already present in decoded match history. No ban is
    # inferred here: competition-specific thresholds and served-match state remain separate.
    if "'discipline_evidence'" not in py:
        anchor2="        p['points']=p['fantasy_points'];p['form']=p['form_points']"
        if anchor2 not in py: raise RuntimeError('aggregate discipline anchor not found')
        addition2="""        p['points']=p['fantasy_points'];p['form']=p['form_points']
        card_rows=[h for h in p['history'] if int(h.get('yc',0) or 0)>0 or int(h.get('rc',0) or 0)>0]
        card_rows.sort(key=lambda h:(str(h.get('date') or ''),int(h.get('gameweek') or 0)))
        p['discipline_evidence']={
            'yellow_cards':int(p.get('yc',0) or 0),'red_cards':int(p.get('rc',0) or 0),
            'history_rows':len(p.get('history') or []),
            'last_card_date':(card_rows[-1].get('date') if card_rows else None),
            'last_card_gameweek':(card_rows[-1].get('gameweek') if card_rows else None),
            'source':'decoded_rich_history'
        }"""
        py=py.replace(anchor2,addition2,1)

    for needle in ["'legal_name':person.name","'first_name':getattr(person,'first_name',None)","'surname_name':getattr(person,'surname_name',None)","'common_name':person.common_name","discipline_evidence","last_card_date","identity_components_preserved"]:
        if needle not in py: raise RuntimeError(f'missing invariant {needle}')
    compile(py,'fm_importer.py','exec')
    return py

def main():
    html=reconstruct_html()
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m: raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    py2=patch_python(py)
    html2=html[:m.start(1)]+base64.b64encode(py2.encode()).decode()+html[m.end(1):]
    repack(html2)
    if reconstruct_html()!=html2: raise RuntimeError('repack round-trip mismatch')
    print('v62: preserved FM identity components and exported non-speculative discipline evidence')

if __name__=='__main__': main()
