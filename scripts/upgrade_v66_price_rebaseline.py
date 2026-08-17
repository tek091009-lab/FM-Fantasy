from pathlib import Path
import base64,gzip

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
packed=''.join(p.read_text().strip() for p in PARTS)
html=gzip.decompress(base64.b64decode(packed)).decode('utf-8')

old=""" const oldPrice=Number((o.price??o.dynamic_price??o.launch_price??p.price)||0);let tracker=fmDeepClone(o.price_tracker||fmPriceTrackerSeed(o,o.price_baseline_gw??oldP.meta?.price_baseline_gw??0));"""
new=""" const oldPrice=Number((o.price??o.dynamic_price??o.launch_price??p.price)||0);
 // v6.6: model-correction guardrails must be allowed to replace a broken frozen launch
 // price. v6.5 correctly calculated Tosin/Gimenez-style prices, but this update path then
 // restored the old baseline. A guardrail is an importer correction, not a weekly market
 // move, so re-baseline immediately and do not create a price-rise/fall news event.
 const correctedModelPrice=Number(p.model_price??p.price??0),guardrail=String(p.price_context?.pricing_guardrail||'');
 if(guardrail&&Number.isFinite(correctedModelPrice)&&correctedModelPrice>0&&Math.abs(correctedModelPrice-oldPrice)>=0.49){
   p.launch_price=correctedModelPrice;p.dynamic_price=correctedModelPrice;p.price=correctedModelPrice;
   p.price_baseline_gw=Number(payload.meta?.latest_gameweek_with_result||0);p.price_change_history=[];
   p.price_tracker=fmPriceTrackerSeed(p,p.price_baseline_gw);p.price_context=p.price_context||{};
   p.price_context.price=correctedModelPrice;p.price_context.rebaseline_applied='v66_corrective_model_guardrail';continue
 }
 let tracker=fmDeepClone(o.price_tracker||fmPriceTrackerSeed(o,o.price_baseline_gw??oldP.meta?.price_baseline_gw??0));"""
if old not in html:raise SystemExit('dynamic pricing oldPrice marker missing')
html=html.replace(old,new,1)
html=html.replace('v25-pricing-guardrails','v26-pricing-rebaseline')
# Leave the Python pricing model name intact; add an explicit JS merge policy in metadata
# on every import so debug exports prove the corrective merge layer is present.
old2="""payload.meta.price_policy='launch price frozen at database import; only post-import sustained form can move price';return{increases:inc.sort((a,b)=>b.delta-a.delta),decreases:dec.sort((a,b)=>a.delta-b.delta)} }"""
new2="""payload.meta.price_policy='launch price frozen at database import; only post-import sustained form can move price';payload.meta.price_merge_policy='v66 corrective model guardrails rebaseline before dynamic pricing';return{increases:inc.sort((a,b)=>b.delta-a.delta),decreases:dec.sort((a,b)=>a.delta-b.delta)} }"""
if old2 not in html:raise SystemExit('dynamic pricing return marker missing')
html=html.replace(old2,new2,1)
for token in ['v66_corrective_model_guardrail','price_merge_policy','v26-pricing-rebaseline']:
    if token not in html:raise SystemExit('missing '+token)
out=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
step=(len(out)+len(PARTS)-1)//len(PARTS)
for i,p in enumerate(PARTS):p.write_text(out[i*step:(i+1)*step]+'\n')
if ''.join(p.read_text().strip() for p in PARTS)!=out:raise SystemExit('repack mismatch')
print('v6.6 corrective price rebaseline applied')
