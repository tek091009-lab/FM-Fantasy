from pathlib import Path
import base64,gzip

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')

anchor="""function fmHistoryKey(h){return `${h?.date||''}|${h?.home||''}|${h?.away||''}|${h?.opponent||''}|${h?.venue||''}`}"""
if anchor not in html: raise SystemExit('pricing JS anchor missing')

helper=r'''function fmApplyPostPayloadPricingCorrections(payload){
 payload=payload||{};payload.meta=payload.meta||{};let changed=0;
 for(const p of payload.players||[]){
  const c=p.price_context||(p.price_context={});const pos=String(p.pos||'');if(!['GK','DEF','MID','FWD'].includes(pos))continue;
  let price=Number(p.price||0),q=Number(c.quality||0),d=Number(c.depth_score||0),ca=Number(p.ca||0),mins=Number(p.minutes||0),apps=Number(p.apps||0);
  const st=[p.injury_status,p.suspension_status,p.status].filter(Boolean).join(' ').toLowerCase();
  const unavailable=!!(p.injured||p.suspended||st.includes('injur')||st.includes('suspend')||p.return_date||p.injury_return_date||p.injury_evidence);
  if(mins<=0&&unavailable&&(q>=0.55||d>=0.55||ca>=130)){
   let floor={GK:4.5,DEF:5.0,MID:5.5,FWD:6.0}[pos];if(q>=0.80&&d>=0.70)floor+=0.5;
   if(price<floor){price=floor;changed++}
   c.usage_role='established_absence';c.availability_signal='Established senior role · currently unavailable';c.pricing_guardrail='v67_postpayload_established_absence';
  }
  const avail=Number(c.available_matches||0),late=!!c.late_arrival;
  if(late&&avail<=1&&apps<=1&&q>=0.60&&d>=0.45){
   let proj=pos==='GK'?4.0+0.60*q+0.40*d:pos==='DEF'?4.5+0.80*q+0.50*d:pos==='MID'?5.0+1.30*q+0.60*d:5.5+1.40*q+0.70*d;
   proj=Math.round(proj*2)/2;
   if(price<proj){price=proj;changed++}
   c.usage_role='new_arrival_projected';c.availability_signal='Recent arrival · projected from quality and squad role';c.pricing_guardrail='v67_postpayload_new_arrival_projection';c.projected_arrival_price=proj;
  }
  if(c.pricing_guardrail){p.price=price;p.model_price=price;c.price=price;}
 }
 payload.meta.postpayload_pricing_corrections=changed;payload.meta.price_merge_policy='v67 post-payload corrective pricing before launch freeze/dynamic merge';return payload;
}
'''
html=html.replace(anchor,helper+anchor,1)

old="""  let payload=result.payload,changes=null;
  if(mode==='update'){"""
new="""  let payload=result.payload,changes=null;
  fmApplyPostPayloadPricingCorrections(payload);
  if(mode==='update'){"""
if old not in html: raise SystemExit('import payload branch marker missing')
html=html.replace(old,new,1)

# Duplicate-save path must not block a corrected pricing model from being applied after a code upgrade.
olddup="""  if(result.duplicate){fmDebugAdd('result','Duplicate save detected — no database changes applied.');applyImportedPayload(old,'update');const processed=fmProcessCompletedGameweeks(),live=liveManagerGameweek();syncProgress(100,'Already up to date');syncMessage(processed.length?`Same save · repaired ${processed.length} completed Gameweek${processed.length===1?'':'s'} into your team total.`:live?`Same save · GW ${live.gw} remains ongoing at ${live.gross} live team pts.`:'Same save already imported — 0 database changes, nothing double-counted.','ok');return}
"""
newdup="""  if(result.duplicate&&String(old?.meta?.price_merge_policy||'').includes('v67')){fmDebugAdd('result','Duplicate save detected — no database changes applied.');applyImportedPayload(old,'update');const processed=fmProcessCompletedGameweeks(),live=liveManagerGameweek();syncProgress(100,'Already up to date');syncMessage(processed.length?`Same save · repaired ${processed.length} completed Gameweek${processed.length===1?'':'s'} into your team total.`:live?`Same save · GW ${live.gw} remains ongoing at ${live.gross} live team pts.`:'Same save already imported — 0 database changes, nothing double-counted.','ok');return}
  if(result.duplicate){result.duplicate=false;fmDebugAdd('info','Same save accepted once to apply v6.7 pricing correction.');}
"""
if olddup not in html: raise SystemExit('duplicate save marker missing')
html=html.replace(olddup,newdup,1)

html=html.replace('v26-pricing-rebaseline','v27-postpayload-pricing')
for token in ['fmApplyPostPayloadPricingCorrections','v67_postpayload_established_absence','v67_postpayload_new_arrival_projection','v27-postpayload-pricing']:
    if token not in html: raise SystemExit('missing '+token)
out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out: raise SystemExit('repack mismatch')
print('v6.7 post-payload pricing correction applied')
