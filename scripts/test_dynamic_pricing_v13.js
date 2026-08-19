const M=require('../dynamicpricingv13.js');

function make(price,backup=false){
  const p={pid:'x',name:'X',club:'Test FC',pos:'MID',price,launch_price:price,history:[],price_context:{nailedness:backup?.25:.9,availability_signal:backup?'Rotation':'Starter'},price_change_history:[]};
  p.price_tracker_v13=M.seed(p,0);p.price_tracker=p.price_tracker_v13;return p;
}
const clone=x=>JSON.parse(JSON.stringify(x));
function run(start,rows,backup=false){let o=make(start,backup),path=[start];for(let i=0;i<rows.length;i++){const n=clone(o);n.history.push(rows[i]);M.applyDynamicPricing({players:[o],meta:{}},{players:[n],meta:{latest_gameweek_with_result:i+1}},{new_results:[]});o=n;path.push(n.price)}return path}
const poor=i=>({date:'p'+i,minutes:90,fpl_points:2,rating:6,goals:0,assists:0});
const normal=i=>({date:'n'+i,minutes:90,fpl_points:8,rating:7.7,goals:0,assists:1});
const brace=i=>({date:'b'+i,minutes:90,fpl_points:14,rating:8.6,goals:2,assists:0});
const goal=i=>({date:'g'+i,minutes:90,fpl_points:9,rating:7.8,goals:1,assists:0});
const steady=i=>({date:'s'+i,minutes:90,fpl_points:4,rating:7.2,goals:0,assists:0});

const out={
  bowen:run(10,[0,1,2,3,4].map(poor)),
  nyoni:run(6.5,[0,1,2,3,4].map(normal)),
  taty:run(9,[brace(0),goal(1),brace(2),goal(3),goal(4)]),
  barco:run(6,[0,1,2,3,4,5,6,7].map(steady),true)
};

let injured=make(8.5,false),injury=[8.5];
for(let i=0;i<8;i++){const n=clone(injured);n.injured=true;n.injury_status='Injured';M.applyDynamicPricing({players:[injured],meta:{}},{players:[n],meta:{latest_gameweek_with_result:i+1}},{new_results:[{home:'Test FC',away:'Other'}]});injured=n;injury.push(n.price)}
out.daramy=injury;

const expected={bowen:9.8,nyoni:6.7,taty:9.4,barco:6.8,daramy:8.5};
for(const [k,v] of Object.entries(expected)){const got=out[k][out[k].length-1];if(got!==v)throw new Error(`${k}: expected ${v}, got ${got}`)}
if(out.bowen[1]!==10||out.nyoni[1]!==6.5||out.taty[1]!==9||out.barco[1]!==6)throw new Error('one-match no-change rule failed');
console.log(JSON.stringify(out,null,2));
