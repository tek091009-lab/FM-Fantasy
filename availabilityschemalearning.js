(()=>{
 'use strict';
 const VERSION='availability-schema-learning-v1';
 const clean=v=>String(v??'').trim();
 const stablePid=p=>clean(p?.pid||p?.player_id||p?.person_id||p?.uid||String(p?.id||'').split('|')[0]);
 const keys=o=>o&&typeof o==='object'&&!Array.isArray(o)?Object.keys(o).sort():[];
 const signature=o=>keys(o).join('|')||'(none)';
 const sourceOf=(kind,p,raw)=>{
   if(kind==='injury')return clean(raw?.injury_evidence?.source||p?.injury_evidence?.source||'');
   return clean(raw?.suspension_evidence_structural?.source||raw?.suspension_evidence?.source||p?.suspension_evidence_structural?.source||p?.suspension_evidence?.source||'');
 };
 function add(map,key,row){
   const k=key||'(unknown)';
   const x=map.get(k)||{signature:k,count:0,reasons:{},sources:{},examples:[]};
   x.count++;
   x.reasons[row.reason]=(x.reasons[row.reason]||0)+1;
   x.sources[row.source||'(none)']=(x.sources[row.source||'(none)']||0)+1;
   if(x.examples.length<5)x.examples.push(row.example);
   map.set(k,x);
 }
 function nameProbe(p){
   const ev=p?.name_component_evidence||{};
   const legal=clean(ev.legal_full??p?.legal_full??p?.legal_name);
   const first=clean(ev.first??p?.first??p?.first_name);
   const surname=clean(ev.surname_family??p?.surname_family??p?.surname_name??p?.surname);
   const common=clean(ev.common_known_as??p?.common_known_as??p?.common_name??p?.known_as);
   const display=clean(p?.display_name??p?.public_name??p?.name);
   const candidate=clean([common,surname].filter(Boolean).join(' '));
   return {legal,first,surname,common,display,candidate,common_plus_surname_matches_display:!!candidate&&candidate.toLowerCase()===display.toLowerCase()};
 }
 function learn(payload){
   if(!payload||!Array.isArray(payload.players))return payload;
   const injury=new Map(),suspension=new Map();
   const nameRelations={records_with_common_and_surname:0,common_plus_surname_matches_display:0,common_plus_surname_mismatches_display:0,taty:null};
   let rejectedInjury=0,rejectedSuspension=0;
   for(const p of payload.players){
     const rejected=p?.availability_rejected_evidence||{};
     for(const kind of ['injury','suspension']){
       const r=rejected[kind]; if(!r)continue;
       const raw=r.raw&&typeof r.raw==='object'?r.raw:{};
       const nested=kind==='injury'?(raw.injury_evidence||{}):(raw.suspension_evidence_structural||raw.suspension_evidence||{});
       const sig=[`raw:${signature(raw)}`,`nested:${signature(nested)}`].join('::');
       const row={reason:clean(r.reason)||'(unknown)',source:sourceOf(kind,p,raw),example:{pid:stablePid(p)||null,name:clean(p?.display_name||p?.name)||null,club:clean(p?.club)||null,raw_fields:keys(raw),nested_fields:keys(nested)}};
       add(kind==='injury'?injury:suspension,sig,row);
       if(kind==='injury')rejectedInjury++; else rejectedSuspension++;
     }
     const np=nameProbe(p);
     if(np.common&&np.surname){
       nameRelations.records_with_common_and_surname++;
       if(np.common_plus_surname_matches_display)nameRelations.common_plus_surname_matches_display++;
       else nameRelations.common_plus_surname_mismatches_display++;
     }
     if(stablePid(p)==='24517')nameRelations.taty={pid:'24517',...np,validation_probe_only_no_display_override:true};
   }
   payload.meta=payload.meta||{};
   payload.meta.availability_schema_learning={version:VERSION,rejected_injury_records:rejectedInjury,rejected_suspension_records:rejectedSuspension,injury_schema_signatures:[...injury.values()].sort((a,b)=>b.count-a.count),suspension_schema_signatures:[...suspension.values()].sort((a,b)=>b.count-a.count),policy:'Rejected availability evidence is grouped for decoder research only; it never promotes a player to injured or suspended.'};
   payload.meta.naming_schema_learning=Object.assign({},payload.meta.naming_schema_learning||{},nameRelations,{version:VERSION,policy:'Component relationships are observational only. common+surname is not promoted unless the independently resolved football display agrees.'});
   return payload;
 }
 function install(){
   const payload=window.FMCloud?.getWorld?.()?.payload||null;
   if(payload)learn(payload);
   try{if(typeof PLAYERS!=='undefined'&&Array.isArray(PLAYERS)){const m=typeof META!=='undefined'?META:{};learn({players:PLAYERS,meta:m})}}catch(_){ }
 }
 window.FMAvailabilitySchemaLearning={version:VERSION,learn};
 window.addEventListener('fmcloudready',()=>setTimeout(install,0));
 window.addEventListener('focus',()=>setTimeout(install,0));
 setTimeout(install,1200);
})();
