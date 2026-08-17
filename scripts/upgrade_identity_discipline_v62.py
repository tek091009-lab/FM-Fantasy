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
    # Preserve FM name components at the point where their pool IDs are still available.
    # Do not alter display_name here: existing canonical football-name normalization remains authoritative.
    old="        out[eid]=Person(eid,uid,pat,name,cname,positions,ca,pa)"
    new="""        person_obj=Person(eid,uid,pat,name,cname,positions,ca,pa)
        person_obj.first_name=fore.get(first)
        person_obj.surname_name=sur.get(surname)
        person_obj.common_name_id=None if com==0xFFFFFFFF else com
        person_obj.first_name_id=first
        person_obj.surname_name_id=surname
        out[eid]=person_obj"""
    if old in py:
        py=py.replace(old,new,1)
    elif 'person_obj.first_name=fore.get(first)' not in py:
        raise RuntimeError('bind_target_people identity anchor not found')

    # Carry legal and component identities alongside the existing public/display name.
    # This gives future schema-specific naming decoders evidence without another save scan.
    anchor="'name':person.display_name,'display_name':person.display_name,'public_name':person.display_name,"
    addition=("'name':person.display_name,'display_name':person.display_name,'public_name':person.display_name,"
              "'legal_name':person.name,'first_name':getattr(person,'first_name',None),"
              "'surname_name':getattr(person,'surname_name',None),'common_name':person.common_name,"
              "'first_name_id':getattr(person,'first_name_id',None),'surname_name_id':getattr(person,'surname_name_id',None),"
              "'common_name_id':getattr(person,'common_name_id',None),'identity_components_preserved':True,")
    if anchor in py:
        py=py.replace(anchor,addition,1)
    elif "'legal_name':person.name" not in py:
        raise RuntimeError('build_players name payload anchor not found')

    # Export exact discipline evidence already present in decoded rich match history.
    # This deliberately does NOT infer a ban: competition rules and served-match state remain separate.
    anchor2="        p['points']=p['fantasy_points'];p['form']=p['form_points']"
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
    if anchor2 in py:
        py=py.replace(anchor2,addition2,1)
    elif "'discipline_evidence'" not in py:
        raise RuntimeError('aggregate discipline anchor not found')

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
