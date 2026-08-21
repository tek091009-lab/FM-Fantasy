from pathlib import Path
from html.parser import HTMLParser
import base64,gzip,re

IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']

class Node:
    def __init__(self,tag,attrs,parent=None):
        self.tag=tag; self.attrs=dict(attrs); self.parent=parent; self.children=[]
        if parent: parent.children.append(self)
    @property
    def id(self): return self.attrs.get('id')
    @property
    def classes(self): return set(self.attrs.get('class','').split())
    def descendants(self):
        for c in self.children:
            yield c
            yield from c.descendants()

class Parser(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(); self.root=Node('root',[]); self.stack=[self.root]; self.by_id={}
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs,self.stack[-1]);
        if n.id:self.by_id[n.id]=n
        if tag not in self.VOID:self.stack.append(n)
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs); self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                del self.stack[i:]; return

parts=[Path('app')/f'part{i:02d}' for i in range(17)]+[Path('app')/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts))).decode('utf-8')
p=Parser(); p.feed(html)
missing=[i for i in IDS if i not in p.by_id]
if missing:
    print('production News ids:',sorted(i for i in p.by_id if i.lower().startswith('news')))
    needle='New registrations'; pos=html.find(needle)
    if pos<0: pos=html.lower().find('registrations')
    print('New registrations packed snippet:',html[max(0,pos-900):pos+1500] if pos>=0 else 'NOT FOUND')
assert not missing,f'missing News cards in production bundle: {missing}'
nodes=[p.by_id[i] for i in IDS]
parents={id(n.parent):n.parent for n in nodes}
assert len(parents)==1,[(n.id,n.parent.tag,n.parent.id,n.parent.attrs.get('class')) for n in nodes]
for n in nodes:
    assert any('newsHead' in d.classes for d in n.descendants()),f'{n.id} missing .newsHead'

js=Path('newsaestheticv34.js').read_text()
assert "const IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']" in js
assert "grid-template-columns:repeat(2,minmax(0,1fr))" in js
assert "grid-template-rows:repeat(3,minmax(0,1fr))" in js
assert "head.appendChild(btn)" in js
for forbidden in ['FMCloud','queueManagerSave','publishWorld','localStorage','sessionStorage','supabase','managerState','freeTransfers','totalPoints']:
    assert forbidden not in js,f'presentation patch must not touch system state: {forbidden}'
idx=Path('index.html').read_text()
assert './newsview.js?v=6' in idx and './newsaestheticv34.js?v=1' in idx
assert idx.index('./newsview.js?v=6') < idx.index('./newsaestheticv34.js?v=1')
assert 'fm-deploy-v34-news-six-card-layout' in idx
print('News v34 presentation-only regression passed; six production cards share one parent')
