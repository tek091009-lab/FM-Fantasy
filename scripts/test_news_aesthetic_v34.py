from pathlib import Path
from html.parser import HTMLParser
import base64,gzip

STATIC_IDS=['newsTransfers','newsPriceUp','newsPriceDown','newsInjuries','newsSuspensions']

class Node:
    def __init__(self,tag,attrs,parent=None):
        self.tag=tag; self.attrs=dict(attrs); self.parent=parent; self.children=[]
        if parent: parent.children.append(self)
    @property
    def id(self): return self.attrs.get('id')

class Parser(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(); self.root=Node('root',[]); self.stack=[self.root]; self.by_id={}
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs,self.stack[-1])
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

reg=Path('registrationnewsguard.js').read_text()
assert "card.id='newsRegistrations'" in reg
assert "transfers.insertAdjacentElement('afterend',card)" in reg

js=Path('newsaestheticv34.js').read_text()
assert "news-aesthetic-v36-stable-empty-state" in js
assert "const EMPTY_TEXT='No changes this import.'" in js
assert "fmNewsEmptyStateV36" in js
assert "fmNewsEmptyV36" in js
assert "syncEmptyState(card)" in js
assert "grid-template-columns:repeat(2,minmax(0,1fr))" in js
assert "grid-template-rows:repeat(3,minmax(0,1fr)) auto" in js
assert "parent.id=GRID_ID" in js
assert "btn.dataset.newsToggle=card.id+'Full'" in js
assert "grid=document.createElement('div')" not in js
assert "parent.insertBefore(grid,cs[0])" not in js
assert "grid.appendChild(card)" not in js
for forbidden in ['FMCloud','queueManagerSave','publishWorld','localStorage','sessionStorage','supabase','managerState','freeTransfers','totalPoints']:
    assert forbidden not in js,f'presentation patch must not touch system state: {forbidden}'
idx=Path('index.html').read_text()
assert './registrationnewsguard.js?v=5' in idx
assert './newsview.js?v=6' in idx and './newsaestheticv34.js?v=3' in idx
assert './newstransferstabilityv40.js?v=2' in idx
assert './newspersistencev5.js?v=8' in idx
assert idx.index('./registrationnewsguard.js?v=5') < idx.index('./newsaestheticv34.js?v=3')
assert idx.index('./newsview.js?v=6') < idx.index('./newsaestheticv34.js?v=3')
assert idx.index('./newspersistencev5.js?v=8') < idx.index('./newstransferstabilityv40.js?v=2')
assert 'fm-deploy-v41-canonical-news-dom-authority' in idx
print('News v36 presentation regression retained under V41 canonical transfer DOM authority')
