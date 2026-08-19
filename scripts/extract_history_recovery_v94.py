from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')
start=py.find('def recover_unlabelled_rich_members(')
if start<0: raise RuntimeError('history function missing')
next_def=re.search(r'\n(?=def [A-Za-z_][A-Za-z0-9_]*\()',py[start+1:])
end=(start+1+next_def.start()) if next_def else len(py)
out=ROOT/'diagnostics'/'history_recovery_v94.txt'
out.parent.mkdir(exist_ok=True)
out.write_text(py[start:end])
print(f'wrote {out} bytes={out.stat().st_size}')
