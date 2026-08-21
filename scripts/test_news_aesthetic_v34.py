from pathlib import Path
from html.parser import HTMLParser
import base64,gzip

STATIC_IDS=['newsTransfers','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']
ALL_IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']

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
missing=[i for i in STATIC_IDS if i not in p.by_id]
assert not missing,f'missing static News cards in production bundle: {missing}'
static=[p.by_id[i] for i in STATIC_IDS]
parents={id(n.parent):n.parent for n in static}
assert len(parents)==1,[(n.id,n.parent.tag,n.parent.id,n.parent.attrs.get('class')) for n in static]
for n in static:
    assert any('newsHead' in d.classes for d in n.descendants()),f'{n.id} missing .newsHead'

reg=Path('registrationnewsguard.js').read_text()
assert "card.id='newsRegistrations'" in reg
assert "transfers.insertAdjacentElement('afterend',card)" in reg
assert "card.innerHTML='<div class=\"newsHead\"" in reg

js=Path('newsaestheticv34.js').read_text()
assert "const IDS=['newsTransfers','newsRegistrations','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']" in js
assert "grid-template-columns:repeat(2,minmax(0,1fr))" in js
assert "grid-template-rows:repeat(3,minmax(0,1fr))" in js
assert "btn.dataset.newsToggle=card.id+'Full'" in js
assert "head.appendChild(btn)" in js
assert "if(cs.length!==IDS.length)return null" in js
assert "commonParent(cs)" in js
for forbidden in ['FMCloud','queueManagerSave','publishWorld','localStorage','sessionStorage','supabase','managerState','freeTransfers','totalPoints']:
    assert forbidden not in js,f'presentation patch must not touch system state: {forbidden}'
idx=Path('index.html').read_text()
assert './registrationnewsguard.js?v=5' in idx
assert './newsview.js?v=6' in idx and './newsaestheticv34.js?v=1' in idx
assert idx.index('./registrationnewsguard.js?v=5') < idx.index('./newsaestheticv34.js?v=1')
assert idx.index('./newsview.js?v=6') < idx.index('./newsaestheticv34.js?v=1')
assert 'fm-deploy-v34-news-six-card-layout' in idx
print('News v34 presentation-only regression passed: five packed cards + dynamic registrations form six-card layout')
