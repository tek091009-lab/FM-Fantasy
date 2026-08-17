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
    # Layer evidence alongside v62's preserved identity fields. We intentionally do not
    # recalculate the visible football name here; the current naming strategy remains authoritative.
    if "'name_component_evidence'" not in py:
        anchor="'common_name_id':getattr(person,'common_name_id',None),'identity_components_preserved':True,"
        if anchor not in py: raise RuntimeError('v62 identity payload anchor not found')
        addition=(anchor+
          "'name_component_evidence':{" 
          "'legal_full':person.name,'first':getattr(person,'first_name',None),"
          "'surname_family':getattr(person,'surname_name',None),'common_known_as':person.common_name,"
          "'first_pool_id':getattr(person,'first_name_id',None),'surname_pool_id':getattr(person,'surname_name_id',None),"
          "'common_pool_id':getattr(person,'common_name_id',None),"
          "'nickname':None,'shirt_name':None,'preferred_short_name':None,"
          "'schema':'person_string_pools_v1'},"
          "'name_resolution_evidence':{"
          "'resolved_display':getattr(person,'display_name',None),"
          "'display_equals_legal':bool(getattr(person,'display_name',None) and getattr(person,'display_name',None)==person.name),"
          "'display_equals_common':bool(getattr(person,'display_name',None) and person.common_name and getattr(person,'display_name',None)==person.common_name),"
          "'display_contains_common':bool(getattr(person,'display_name',None) and person.common_name and person.common_name.casefold() in getattr(person,'display_name',None).casefold()),"
          "'display_contains_surname':bool(getattr(person,'display_name',None) and getattr(person,'surname_name',None) and getattr(person,'surname_name',None).casefold() in getattr(person,'display_name',None).casefold()),"
          "'source':'preserved_components_plus_current_resolver'},")
        py=py.replace(anchor,addition,1)

    # Export what historical player data was genuinely observed. This prevents consumers from
    # treating missing retained history as a real zero and lets future decoder work compare saves
    # without another full archive scan.
    if "'retained_history_evidence'" not in py:
        anchor2="        p['discipline_evidence']={\n"
        pos=py.find(anchor2)
        if pos<0: raise RuntimeError('v62 discipline block anchor not found')
        # Insert immediately before the discipline block so history evidence and card evidence
        # are generated from the same already-decoded in-memory rows.
        block="""        _hist_rows=list(p.get('history') or [])
        _hist_gws=sorted({int(h.get('gameweek') or 0) for h in _hist_rows if int(h.get('gameweek') or 0)>0})
        _hist_dates=sorted({str(h.get('date')) for h in _hist_rows if h.get('date')})
        p['retained_history_evidence']={
            'decoded_rows':len(_hist_rows),
            'decoded_gameweeks':_hist_gws,
            'first_decoded_date':(_hist_dates[0] if _hist_dates else None),
            'last_decoded_date':(_hist_dates[-1] if _hist_dates else None),
            'history_is_partial_or_unknown':True,
            'zero_stats_are_observed_only_within_decoded_rows':True,
            'source':'decoded_rich_history'
        }
"""
        py=py[:pos]+block+py[pos:]

    for needle in ["name_component_evidence","name_resolution_evidence","retained_history_evidence","decoded_gameweeks","history_is_partial_or_unknown","identity_components_preserved","discipline_evidence"]:
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
    print('v63: preserved naming provenance and retained-history coverage evidence')

if __name__=='__main__': main()
