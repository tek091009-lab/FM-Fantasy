from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')
compile(py,'fm_importer_live_v81.py','exec')
(ROOT/'_current_importer_live_v81.py').write_text(py,encoding='utf-8')
# Keep the exact archive-selection/import JS around the FM runtime for diagnosis.
js_start=html.find('const FM_RUNTIME')
if js_start<0: js_start=max(0,m.start()-20000)
js_end=html.find('</script>',m.end())
if js_end<0: js_end=min(len(html),m.end()+40000)
(ROOT/'_current_import_runtime_live_v81.txt').write_text(html[js_start:js_end],encoding='utf-8')
print('extracted live importer',len(py),'chars; runtime',js_end-js_start,'chars')
