const fs=require('fs');
const js=fs.readFileSync('newsaestheticv34.js','utf8');
const idx=fs.readFileSync('index.html','utf8');
function must(x,msg){if(!x)throw new Error(msg)}
must(js.includes("news-aesthetic-v36-stable-empty-state"),'v36 version missing');
must(js.includes("parent.id=GRID_ID"),'existing parent is not promoted to grid');
must(js.includes("grid-template-columns:repeat(2,minmax(0,1fr))"),'2-column grid missing');
must(js.includes("grid-template-rows:repeat(3,minmax(0,1fr)) auto"),'3 equal rows + footer row missing');
must(!js.includes("grid=document.createElement('div')"),'regression: nested grid wrapper recreated');
must(!js.includes("grid.appendChild(card)"),'regression: cards reparented into a single grid cell');
must(idx.includes('./newsaestheticv34.js?v=3'),'V36 cache-bust missing');
must(idx.includes('fm-deploy-v38-initial-squad-draft-restore'),'V38 loader marker missing');
console.log('V35 parent-layout regression retained under V38');
