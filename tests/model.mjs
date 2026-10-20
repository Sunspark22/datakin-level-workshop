// Synthetic layout only: no authored game stages or game assets are bundled.
import assert from 'node:assert/strict';
import {normalize,blank,addHeadroom,addBelow,insertSection,remove,exportStage,TYPES} from '../web/model.js';
const base={format:'datakin-stage-v1',name:'SAMPLE',theme:1,byte_id:1,draft:false,
 width:1600,height:160,spawn:{x:24,y:104},checkpoint:{x:160,y:104},exit:{x:1540,y:104},
 platforms:[{x:0,y:132,w:1600,h:28}],enemies:[],pickups:[],boss:0,comate:{x:0,y:0}};
const s=blank(normalize(base));
s.platforms.push({x:240,y:80,w:80,h:8,ice:1},{x:400,y:64,w:80,h:8});
s.vanish=[1,2];s.clouds=[2];s.rails=[{platform:2,left:400,right:800}];
remove(s,{key:'platforms',index:1});
assert.deepEqual(s.vanish,[1]);assert.deepEqual(s.clouds,[1]);assert.equal(s.rails[0].platform,1);
const before=structuredClone(s);
addHeadroom(s);assert.equal(s.headroom,160);assert.equal(s.height,320);assert.equal(s.spawn.y,before.spawn.y+160);
addBelow(s);assert.equal(s.height,480);
const x=s.exit.x;insertSection(s,800,240);assert.equal(s.exit.x,x+240);assert.equal(s.width,1840);
const exported=exportStage(s);assert.equal(exported.platforms.length,2);assert.equal(exported.sections.length,1);
assert.equal(exported.theme,1);assert.equal(exported.byte_id,1);assert.equal(TYPES.enemies.defaults.hp,2);
console.log('Model checks passed: deletion references, slippery flag, headroom, space below, section insertion and export.');
