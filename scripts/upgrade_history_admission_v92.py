from __future__ import annotations
import base64,gzip
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]


def reconstruct()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')


def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):
        p.write_text(c+'\n')

html=reconstruct()

# The Python retained-match decoder supports bounded 18..22 player rows per side, so a valid
# compact match can contain only 36..39 stat rows.  The browser archive admission pass was
# still requiring >=40 before writing the member to /tmp/rich_*.bin, making those Python
# decoder paths unreachable for unlabelled members.  Keep the same single archive scan and
# same candidate-name filter; only align the admission threshold with the decoder minimum.
old="const statCount=this.richStatCount(out,40);if(labelHit||statCount>=40){const idx=richNames.length;richNames.push(m.name);richProbe.push({name:m.name,plain:m.plain,labelHit,statSignature:statCount>=40,statCount});py.FS.writeFile('/tmp/rich_'+idx+'.bin',out)}"
new="const statCount=this.richStatCount(out,40);if(labelHit||statCount>=36){const idx=richNames.length;richNames.push(m.name);richProbe.push({name:m.name,plain:m.plain,labelHit,statSignature:statCount>=36,legacy40StatSignature:statCount>=40,sub40StatBlock:statCount>=36&&statCount<40,statCount,historyAdmissionMinStats:36});py.FS.writeFile('/tmp/rich_'+idx+'.bin',out)}"

if new not in html:
    if old not in html:
        raise RuntimeError('retained-member 40-row admission anchor missing; production shape changed')
    html=html.replace(old,new,1)

# Also make the admission policy visible in the final payload/debug without a second save scan.
old_policy="payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation + grounded-fixture retention-v86';"
new_policy="payload.meta.history_recovery_policy='single-archive-scan + cached identity propagation + grounded-fixture retention-v86 + retained-member-min36-v92';payload.meta.retained_member_stat_admission_min=36;"
if new_policy not in html:
    if old_policy not in html:
        raise RuntimeError('history recovery policy anchor missing')
    html=html.replace(old_policy,new_policy,1)

repack(html)

chk=reconstruct()
assert 'statCount>=36' in chk
assert 'sub40StatBlock:statCount>=36&&statCount<40' in chk
assert 'historyAdmissionMinStats:36' in chk
assert 'retained_member_stat_admission_min=36' in chk
# The old admission condition itself must be gone. Keep legacy40StatSignature only as a diagnostic.
assert "if(labelHit||statCount>=40)" not in chk
print('v92 retained-history member admission aligned to 36-row decoder minimum')
