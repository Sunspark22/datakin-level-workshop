export const THEMES=['Training','Sky','Frost','Metal','Nature','Fire','Water','Electric','Chemical','Shadow','Cosmic','Gauntlet'];
export const EMITTER_KINDS=['Vat','Dripper','Acid shower'];
export const ENEMIES=['Patrol foe','Charging foe','Platform-riding foe','Snowball thrower','Ice charger','Divebomb flyer','Laser robot','Frog','Camouflaged lizard','Pond fish','Grass guard','Magma drake','Fire lizard','Fire flyer','Magma jelly','Alligator','Seagull','Jellyfish','Lock-on bug','Water fish','Land alligator','Monkey laser bot','Duckbot','Vat Rat','Chemical slime','Cloud Puff','Thunder Puff','Top-hat skeleton','Pursuing bat','Pumpkin Man','Sword patrol','Missile launcher','Platform guardian','Floor mine','Burst node','Fuse bot','Robot King','Mama drake','Mama jelly','Wall turret','Arrow drone'];
const box=(label,group,color,limit,extra={})=>({label,group,color,limit,shape:'box',defaults:{w:64,h:8,...extra}});
const point=(label,group,color,limit,extra={})=>({label,group,color,limit,shape:'point',defaults:extra});
export const TYPES={
 switches:{...point('Road switch','Secrets','#ffdc91',5),note:'Numbered 1–5 on the map and overview. Activate with Up or an attack. All five switches open the Cosmic skateboard gate. Activated switches stay saved.'},
 road_entry:{...point('Skateboard gate','Secrets','#ffaedd',1),unique:true,feet:true,optional:true,note:'Cosmic needs five road switches and a road return marker. Frost needs the return marker only. Up enters the behind-Ket course.'},
 road_return:{...point('Road return','Secrets','#86eee8',1),unique:true,feet:true,optional:true},
 flight_start:{...point('Air Pad','Secrets','#8ff0ff',1),unique:true,feet:true,optional:true,note:'Gauntlet. Standing on the pad starts free flight with an auto-scrolling screen until the landing marker. Needs a Flight landing marker at least a screen to the right.'},flight_end:{...point('Flight landing','Secrets','#5fd3e0',1),unique:true,feet:true,optional:true},
 spiral:{...point('Spiral lift','Secrets','#ffb4ff',1),unique:true,feet:true,optional:true,note:'Gauntlet. Standing here starts the spiral lift (three rounds of foes on a turning platform); Ket reappears at the Spiral lift top marker.'},spiral_exit:{...point('Spiral lift top','Secrets','#e490e4',1),unique:true,feet:true,optional:true},
 platforms:box('Platform','Ground','#71dbc9',Infinity),terrain:{...box('Slope','Ground','#b1bcf0',Infinity,{w:96,rise:32,ice:0}),shape:'slope',defaults:{w:96,rise:32,ice:0}},movers:box('Moving platform','Ground','#f4c27a',Infinity,{axis:0,travel:64,period:180,phase:0}),
 enemies:point('Enemy','Creatures','#ff818b',Infinity,{hp:2,kind:0}),pickups:point('Stamina gem','Collectibles','#72caff',Infinity),caches:point('Bit cache','Collectibles','#ffe185',32,{bits:15}),comate:{...point('Hidden byte','Collectibles','#da99ff',1),unique:true},
 spawn:{...point('Start position','Markers','#81edc0',1),unique:true,feet:true},checkpoints:{...point('Checkpoint','Markers','#daa8ff',32),feet:true},exit:{...point('Level exit','Markers','#d8faff',1),unique:true,feet:true},boss:{...point('Boss entry','Markers','#ff9191',1),unique:true},
 miniboss_entry:{...point('Mini-boss entry','Markers','#d5a4ff',1),unique:true,feet:true,optional:true,planned:true},miniboss_exit:{...point('Mini-boss stage exit','Markers','#ffc58c',1),unique:true,feet:true,optional:true,planned:true},
 spikes:box('Spikes','Hazards','#ff6e89',Infinity,{w:40,h:8}),traps:box('Moving spikes','Hazards','#e789b7',Infinity,{w:32,h:16,axis:1,travel:40,period:180}),lasers:point('Ceiling / floor laser','Hazards','#ed819b',Infinity,{h:72,dir:1,phase:0}),chemicals:box('Chemical pool','Hazards','#afd367',Infinity,{w:80,h:8}),lava:box('Lava pool','Hazards','#ff974e',Infinity,{w:96,h:20}),jets:point('Magma spout','Hazards','#ffa865',Infinity,{h:60,period:240,phase:0}),
 emitters:{...point('Vat / dripper','Hazards','#c3e563',Infinity,{h:96,kind:1,period:240,phase:0}),note:'Vats lob two toxin splashes, drippers let single drops fall, and the acid shower warns and then pours a curtain. Pour length is how far the curtain reaches and is used by the acid shower only; set it so the curtain lands on the floor. Toxin puddles hurt Ket wherever they land, in any environment, and the artwork borrows whichever palette the stage uses outside Chemical.'},
 arcs:{...box('Floor arc','Hazards','#9fe8ff',Infinity,{w:100,h:18,period:180,phase:70}),note:'An electrode sits at each end and they bridge the gap for about half a second every cycle. Put the bottom edge of the box on the floor line: the electrodes draw there and the box is the area that hurts. Timing offset staggers one arc against its neighbours.'},
 spotlights:{...box('Bat spotlight','Hazards','#f9dda1',Infinity,{w:96,h:88,travel:48,period:300,phase:0,dir:1,on:180,off:180}),note:'Drag the unswept light cone. Direction selects a lamp at the top or bottom centre; Sweep controls how far its beam swings to either side. On/Off times control blinking (both zero means always on). Spotting Ket summons two bats. Solid platforms provide cover and Stealth avoids detection. A light rearms after Ket leaves and its bats are gone; at most eight summoned bats can be alive together.'},
 crushers:{...box('Crusher','Hazards','#c8c8e0',Infinity,{w:56,h:32,axis:1,travel:90,period:210,phase:0}),note:'Gauntlet. A heavy block that shakes, slams along one axis (negative travel slams up or left), holds, then slowly retracts. Touching it hurts, like moving spikes; it is not solid.'},
 storms:{...box('Storm zone','Hazards','#b7a2ff',Infinity,{w:600,h:300,period:200}),note:'Gauntlet. While Ket is inside the box, lightning strikes near her every Cycle: the ground flashes first, then the bolt hits. A raised shield (Up + R with Vector Aim) blocks it.'},
 shadow_dusk:{...point('Dusk starts','Environment','#b195dd',1),unique:true,optional:true},shadow_library_entry:{...point('Library entry','Environment','#bf9b70',1),unique:true,optional:true},
 shadow_blackout_start:{...point('Blackout starts','Environment','#8068ad',1),unique:true,optional:true,note:'Shadow only. Between the two blackout markers, the scenery disappears and platforms glow in timed pulses. Lamps and pursuing bats remain visible.'},shadow_blackout_end:{...point('Blackout ends','Environment','#caacef',1),unique:true,optional:true},
 winds:box('Wind / current','Environment','#83cce2',Infinity,{w:80,h:56,dx:0,dy:-70}),waters:box('Water','Environment','#558ac8',Infinity,{w:128,h:64}),grass:box('Tall grass','Environment','#94c46e',Infinity,{w:72,h:28}),vines:point('Vine','Environment','#a2c689',Infinity,{length:40}),
 belts:{...box('Conveyor belt','Environment','#c2a9ff',Infinity,{w:240,h:16,dx:330,period:240}),note:'Carries Ket while she stands inside the box. Put the bottom edge on the floor line: the belt surface draws there. Belt speed is the push each frame, negative for leftwards. A reverse cycle of 0 seconds means the belt never turns around.'}
};
// Where a ranged enemy will open fire, taken from the engine's own tests. 'flat'
// shots keep the shooter's height; 'aimed' ones track Ket. A missing y means the
// engine applies no vertical limit, so the shot can cross into another room.
export const ENEMY_REACH={
 0:{x:180,aim:'flat'},1:{x:180,aim:'flat'},2:{x:180,aim:'flat'},
 3:{x:210,aim:'aimed'},6:{x:205,aim:'flat'},
 8:{x:180,y:195,aim:'aimed'},10:{x:150,y:195,aim:'aimed'},
 11:{x:300,y:195,aim:'aimed'},12:{x:300,y:195,aim:'flat'},
 13:{x:300,y:195,aim:'aimed'},14:{x:300,y:195,aim:'aimed'},
 17:{x:290,y:190,aim:'aimed'},18:{x:290,y:190,aim:'aimed'},20:{x:290,y:190,aim:'aimed'},
 21:{x:255,y:170,aim:'aimed'},22:{x:255,y:170,aim:'aimed'},27:{x:190,y:105,aim:'aimed'},
 31:{x:640,y:160,aim:'aimed',note:'2-second countdown · fires before onscreen'}
};
// The box a shooter fires into, in map coordinates, or null for a melee enemy.
// A missing y in ENEMY_REACH means the engine applies no vertical limit, so the
// box covers the whole map: that shooter can hit Ket in a room below or above.
export function reachBox(enemy,height){
 const r=ENEMY_REACH[enemy.kind];if(!r)return null;
 if(r.aim==='flat')return {x:enemy.x-r.x,y:enemy.y-12,w:r.x*2,h:24,note:'fires level'};
 if(r.y===undefined)return {x:enemy.x-r.x,y:25,w:r.x*2,h:height-25,note:'fires at any height'};
 return {x:enemy.x-r.x,y:enemy.y-r.y,w:r.x*2,h:r.y*2,note:r.note||'firing range'};
}
export const clone=o=>JSON.parse(JSON.stringify(o));
export const MOTION_LIMITS={travel:512,period:1800};
// The ROM edition receives fixed capacities from the verified cartridge profile.
export function trapIssues(s){
 const issues=[],rules=[['x','X position',0,s.width-1],['y','Y position',25,s.height-1],['w','Width',8,100],['h','Height',4,s.height-30],['axis','Travel direction',0,1],['travel','Travel',0,MOTION_LIMITS.travel],['period','Cycle',60,MOTION_LIMITS.period]];
 for(const [index,p] of (s.traps||[]).entries())for(const [field,label,lo,hi] of rules){const value=p[field];if(Number.isInteger(value)&&value>=lo&&value<=hi)continue;let reason;
  if(field==='period'&&typeof value==='number')reason=`Cycle is ${Number((value/60).toFixed(4))} seconds; allowed 1-${MOTION_LIMITS.period/60} seconds (60-${MOTION_LIMITS.period} whole frames).`;
  else if(field==='axis')reason=`Travel direction is ${value}; choose Left / right (0) or Up / down (1).`;
  else if(!Number.isInteger(value))reason=`${label} must be a whole number; allowed ${lo}-${hi}.`;
  else reason=`${label} is ${value} px; allowed ${lo}-${hi} px.`;
  issues.push({key:'traps',index,field,message:`Moving spikes #${index+1} (X ${p.x}, Y ${p.y}): ${reason}`});
 }
 return issues;
}
export function platformSlippery(s,e){
 if(e.data.ice!==undefined)return !!e.data.ice;
 if(e.key==='movers')return s.theme===2;
 const p=e.data;
 return s.terrain.some(t=>t.ice&&p.x<t.x+t.w&&p.x+p.w>t.x&&Math.abs(p.y-(t.y+(Math.max(t.x,Math.min(t.x+t.w,p.x+p.w/2))-t.x)*t.rise/t.w))<5);
}
export function normalize(s){s=clone(s);s.height??=160;s.headroom??=0;for(const [k,t] of Object.entries(TYPES))if(!t.unique)s[k]??=[];s.checkpoints=s.checkpoints.length?s.checkpoints:[clone(s.checkpoint)];s.vanish??=[];s.rails??=[];s.arena??=[];s.clouds??=[];s.sections??=[];for(const p of s.spotlights){p.dir??=1;p.on??=180;p.off??=180;}for(const p of s.movers)p.phase??=0;return s;}
export function entities(s){const all=[];for(const [key,t] of Object.entries(TYPES)){if(t.unique){if(key==='boss'){if(s.boss)all.push({key,index:0,data:{x:s.boss,y:s.exit.y+28}});}else if(s[key]&&(key!=='comate'||s[key].x))all.push({key,index:0,data:s[key]});}else(s[key]||[]).forEach((data,index)=>all.push({key,index,data}));}return all;}
export function find(s,sel){return sel&&entities(s).find(e=>e.key===sel.key&&e.index===sel.index);}
export function bounds(e){const t=TYPES[e.key],p=e.data;if(t.shape==='box')return {x:p.x,y:p.y,w:p.w,h:p.h};if(t.shape==='slope')return {x:p.x,y:Math.min(p.y,p.y+p.rise),w:p.w,h:Math.max(8,Math.abs(p.rise))};if(t.feet)return {x:p.x,y:p.y,w:26,h:28};if(e.key==='vines')return {x:p.x-5,y:p.y,w:10,h:p.length};return {x:p.x-9,y:p.y-12,w:18,h:24};}
export const railOf=(s,index)=>s.rails.find(r=>r.platform===index);
// Raft steering limits are map positions for the platform's left edge: they ride with the raft and stay on the map.
export function fitRail(s,index){const r=railOf(s,index),p=s.platforms[index];if(!r||!p)return;const far=Math.max(0,s.width-p.w);
 r.left=Math.min(Math.max(0,Math.round(r.left)),far);r.right=Math.min(Math.max(r.left,Math.round(r.right)),far);
 r.left=Math.min(r.left,p.x);r.right=Math.max(r.right,p.x);}
export function fitRails(s){for(const r of s.rails)fitRail(s,r.platform);}
export function slideRail(s,index,dx){const r=railOf(s,index);if(!r||!dx)return;r.left+=dx;r.right+=dx;fitRail(s,index);}
export function setRailLimit(s,index,key,value){const r=railOf(s,index),p=s.platforms[index];if(!r||!p)return;
 if(!Number.isInteger(value))throw Error('Use a whole pixel position for the raft limit.');
 r[key]=Math.min(Math.max(0,value),Math.max(0,s.width-p.w));
 if(r.left>r.right)r[key==='left'?'right':'left']=r[key];
 p.x=Math.min(Math.max(r.left,p.x),r.right);}
export function remove(s,sel){const t=TYPES[sel.key];if(t.unique){if(t.optional)delete s[sel.key];else if(sel.key==='boss')s.boss=0;else if(sel.key==='comate')s.comate={x:0,y:0};else throw Error('Move this required marker instead of deleting it.');return;}if(sel.key==='checkpoints'&&s.checkpoints.length===1)throw Error('Keep at least one checkpoint.');s[sel.key].splice(sel.index,1);if(sel.key==='platforms')for(const k of ['vanish','arena','clouds'])s[k]=s[k].filter(i=>i!==sel.index).map(i=>i>sel.index?i-1:i);if(sel.key==='platforms')s.rails=s.rails.filter(r=>r.platform!==sel.index).map(r=>({...r,platform:r.platform>sel.index?r.platform-1:r.platform}));}
export function exportStage(s){s=clone(s);if(s.theme!==10&&s.theme!==11)s.checkpoints.sort((a,b)=>a.x-b.x);if(!s.checkpoint||s.checkpoint.x>s.width-26||s.checkpoint.y>s.height-28)s.checkpoint=clone(s.checkpoints[0]);s.terrain.sort((a,b)=>a.x-b.x);return s;}
export function blank(base){const s=normalize(base);for(const [k,t] of Object.entries(TYPES)){if(t.optional)delete s[k];else if(!t.unique)s[k]=[];}s.name='MY NEW ROUTE';s.headroom=0;s.width=1600;s.height=160;s.boss=0;s.draft=false;s.spawn={x:24,y:104};s.checkpoints=[{x:160,y:104}];s.checkpoint=clone(s.checkpoints[0]);s.exit={x:1540,y:104};s.comate={x:0,y:0};s.platforms=[{x:0,y:132,w:1600,h:28}];s.vanish=[];s.rails=[];s.arena=[];s.clouds=[];s.sections=[];return s;}
export function addHeadroom(s,amount=160){if(s.height+amount>2048)throw Error('Maximum map height is 2048 pixels.');for(const e of entities(s))if(e.key!=='boss')e.data.y+=amount;s.checkpoint.y+=amount;s.height+=amount;s.headroom=(s.headroom||0)+amount;}
export function addBelow(s,amount=160){if(s.height+amount>2048)throw Error('Maximum map height is 2048 pixels.');s.height+=amount;}
export function insertSection(s,x,amount){if(!Number.isInteger(x)||x<0||x>s.width||!Number.isInteger(amount)||amount<8)throw Error('Choose an insertion point inside the map and a width of at least 8 pixels.');if(s.width+amount>8000)throw Error('Maximum map width is 8000 pixels.');for(const e of entities(s)){if(e.key==='boss'){if(s.boss>=x)s.boss+=amount;continue;}const p=e.data;if(p.x>=x)p.x+=amount;else if(p.w&&p.x+p.w>x&&!['movers','traps'].includes(e.key))p.w+=amount;}if(s.checkpoint.x>=x)s.checkpoint.x+=amount;for(const r of s.rails)for(const k of ['left','right'])if(r[k]>=x)r[k]+=amount;s.width+=amount;s.sections.push({x,w:amount});}
