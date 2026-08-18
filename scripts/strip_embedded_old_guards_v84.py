from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')
before=html
patterns=[
    r'<script\s+src=["\']\.?/?updateguard\.js\?v=[^"\']+["\']\s*>\s*</script>',
    r'<script\s+src=["\']\.?/?importcompat\.js\?v=[^"\']+["\']\s*>\s*</script>'
]
removed=0
for pat in patterns:
    html,n=re.subn(pat,'',html,flags=re.I)
    removed+=n
# Also reject any literal old guard source accidentally embedded in the packed app.
if 'world-update-guard-v5-strict-current-roster' in html:
    raise RuntimeError('packed app still embeds world-update-guard-v5 source')
if removed==0:
    print('no embedded guard tags found; packed app already clean')
else:
    print('removed',removed,'embedded guard/importcompat tags')
packed2=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(packed2)+len(PARTS)-1)//len(PARTS)
chunks=[packed2[i*step:(i+1)*step] for i in range(len(PARTS))]
chunks += ['']*(len(PARTS)-len(chunks))
assert ''.join(chunks)==packed2
for p,c in zip(PARTS,chunks): p.write_text(c+'\n')
roundtrip=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
assert roundtrip==html
assert 'world-update-guard-v5-strict-current-roster' not in roundtrip
print('packed app cleaned of legacy publish guards')
