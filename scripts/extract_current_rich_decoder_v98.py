from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html); assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
lines=py.splitlines()
blocks=[]
for name in ['_rich_stat_record_at','_rich_scan_stats','_rich_scan_stats_fast','_rich_candidate_squad_pairs','recover_unlabelled_rich_members','recover_game_db_rich_matches','join_rich_matches']:
    start=next(i for i,l in enumerate(lines) if l.startswith('def '+name))
    end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('def ')),len(lines))
    blocks.append(f'===== {name} =====\n'+'\n'.join(lines[start:end]))
Path('_current_rich_decoder_v98.txt').write_text('\n\n'.join(blocks)+'\n',encoding='utf-8')
print('wrote _current_rich_decoder_v98.txt')
