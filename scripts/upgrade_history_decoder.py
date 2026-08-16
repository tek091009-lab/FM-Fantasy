from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name=='scripts' else Path.cwd()
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
FRAG=Path(__file__).with_name('history_recovery_v53.pyfrag')


def reconstruct_html()->str:
    b64=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(b64)).decode('utf-8')


def safe_fragment()->str:
    frag=FRAG.read_text()
    # A speculative side may teach club identity only once. Re-running the in-memory
    # recovery loop must not let the same unconfirmed side recursively strengthen itself.
    frag=frag.replace(
        "    def propagate_side_identities(max_rounds=8):\n        accepted=0\n        labelled_side=set()\n",
        "    learned_side_label={}\n    def propagate_side_identities(max_rounds=8):\n        accepted=0\n"
    )
    frag=frag.replace("                if si in labelled_side:continue\n","                if si in learned_side_label:continue\n")
    frag=frag.replace("                labelled_side.add(si);progress+=1;accepted+=1\n","                learned_side_label[si]=eid;progress+=1;accepted+=1\n")
    frag=frag.replace("        diagnostics['cohort_side_labels']=max(diagnostics['cohort_side_labels'],accepted)\n","        diagnostics['cohort_side_labels']=len(learned_side_label)\n")
    if 'learned_side_label={}' not in frag or 'labelled_side=set()' in frag:
        raise RuntimeError('cohort single-vote safety patch not applied')

    # Some FM schema generations expose no useful fixture_id (or zero for many rows).
    # The old matcher used fixture_id as the uniqueness key everywhere, so several valid
    # fixtures could collapse onto key 0. Worse, the single-side bridge could mistake that
    # collapse for a unique fixture. Use a structural key fallback instead: current fixture
    # id when present, otherwise the calendar identity already decoded from FM.
    marker="    used_fixtures=set();used_candidates=set();out=[]\n\n"
    helper=(
        "    used_fixtures=set();used_candidates=set();out=[]\n\n"
        "    def fixture_key(f):\n"
        "        fid=int(f.get('fixture_id') or 0)\n"
        "        if fid>0:return ('id',fid)\n"
        "        return ('struct',int(f.get('home_tid') or 0),int(f.get('away_tid') or 0),\n"
        "                str(f.get('date') or ''),int(f.get('gameweek') or 0),\n"
        "                int(f.get('home_score') or 0),int(f.get('away_score') or 0))\n\n"
    )
    if marker not in frag:raise RuntimeError('fixture identity insertion marker not found')
    frag=frag.replace(marker,helper,1)
    frag=frag.replace("fid=int(f.get('fixture_id') or 0)","fid=fixture_key(f)")
    frag=frag.replace("uniq={int(o[0].get('fixture_id') or 0):(o) for o in options}","uniq={fixture_key(o[0]):o for o in options}")
    frag=frag.replace("if int(f.get('fixture_id') or 0) in used_fixtures:continue","if fixture_key(f) in used_fixtures:continue")
    if "def fixture_key(f):" not in frag or "uniq={fixture_key(o[0]):o for o in options}" not in frag:
        raise RuntimeError('schema-safe fixture key patch not applied')
    # It is unsafe for the bridge/global matcher to collapse missing fixture ids onto 0.
    if "int(o[0].get('fixture_id') or 0)" in frag:
        raise RuntimeError('unsafe zero fixture-id uniqueness remains')
    return frag.rstrip()+'\n\n'


def patch_importer(html:str)->str:
    m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
    if not m: raise RuntimeError('FM_PY_SOURCE_B64 not found')
    py=base64.b64decode(m.group(1)).decode('utf-8')
    start=py.find('def recover_unlabelled_rich_members(')
    end=py.find('def recover_game_db_rich_matches(',start)
    if start<0 or end<0: raise RuntimeError('history recovery function markers not found')
    frag=safe_fragment()
    py2=py[:start]+frag+py[end:]
    # Expose the decoder paths in Export Debug without making them required by old builds.
    needle="'unlabelled_rich_propagation_matches':member_rich_diag.get('propagation_matches',0),"
    extra=(needle+"'unlabelled_rich_cohort_side_labels':member_rich_diag.get('cohort_side_labels',0),"
           "'unlabelled_rich_fixture_identity_matches':member_rich_diag.get('fixture_identity_matches',0),"
           "'unlabelled_rich_single_side_bridge_matches':member_rich_diag.get('single_side_bridge_matches',0),"
           "'unlabelled_rich_identity_rounds':member_rich_diag.get('identity_rounds',0),")
    if needle in py2 and 'unlabelled_rich_fixture_identity_matches' not in py2:
        py2=py2.replace(needle,extra)
    compile(py2,'fm_importer.py','exec')
    new_b64=base64.b64encode(py2.encode()).decode()
    html2=html[:m.start(1)]+new_b64+html[m.end(1):]
    if 'unlabelled_retained_fixture_identity' not in py2: raise RuntimeError('new decoder marker missing')
    if "def fixture_key(f):" not in py2: raise RuntimeError('schema-safe fixture key missing from importer')
    return html2


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    n=len(PARTS);step=(len(packed)+n-1)//n
    chunks=[packed[i*step:(i+1)*step] for i in range(n)]
    if len(chunks)<n:chunks += ['']*(n-len(chunks))
    if ''.join(chunks)!=packed: raise RuntimeError('chunk split failed')
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')


def main():
    html=reconstruct_html();patched=patch_importer(html);repack(patched)
    # Round-trip production validation.
    check=reconstruct_html()
    if check!=patched:raise RuntimeError('repack round-trip mismatch')
    print('History decoder upgraded: strict + cluster + cohort + fixture identity + single-side bridge + schema-safe fixture key')

if __name__=='__main__':main()
