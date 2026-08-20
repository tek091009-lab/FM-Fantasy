(()=>{
'use strict';
const VERSION='undo-last-import-v2-dbcontrols-owned';
function run(){
  if(window.FMCloudDatabase?.undoLastImport)return window.FMCloudDatabase.undoLastImport();
  alert('Undo service is not ready yet. Log in as the Creator and try again.');
}
window.FMUndoLastImport={version:VERSION,run};
})();
