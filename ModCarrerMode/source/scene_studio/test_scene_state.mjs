import assert from 'node:assert/strict';
import {validateScene,History,MAX_ACTORS} from './scene_state.js';
const catalog=new Map([[1,['Arm','Hand']]]);
const bone=name=>({name,position:[0,1,0],quaternion:[0,0,0,1],scale:[1,1,1]});
const actor={id:'a',playerId:1,position:[1,0,0],quaternion:[0,0,0,1],scale:[.01,.01,.01],bones:[bone('Arm'),bone('Hand')]};
const scene={schema:2,type:'fifa16-offline-scene',actors:[actor],views:[{name:'Frente',position:[0,1,4],target:[0,1,0]}]};
assert.equal(validateScene(scene,catalog).actors[0].bones.length,2);
assert.equal(validateScene({...scene,actors:[]},catalog).actors.length,0);
for(const edit of [s=>s.actors.push({...actor}),s=>s.actors[0].playerId=5,s=>s.actors[0].bones[0].name='Fake',s=>s.actors[0].position[0]=Infinity,s=>s.actors[0].scale[0]=0,s=>s.actors[0].bones[0].quaternion=[0,0,0,0],s=>s.views[0].target[0]=NaN]){
 const bad=structuredClone(scene);edit(bad);assert.throws(()=>validateScene(bad,catalog));
}
assert.throws(()=>validateScene({...scene,actors:Array.from({length:MAX_ACTORS+1},(_,i)=>({...actor,id:String(i)}))},catalog));
const h=new History(2);h.push(scene);const modified=structuredClone(scene);modified.actors[0].position[0]=5;
assert.equal(h.back(modified).actors[0].position[0],1);assert.equal(h.forward(scene).actors[0].position[0],5);
h.push(scene);scene.actors[0].position[0]=99;assert.equal(h.back(modified).actors[0].position[0],1);
console.log('PASS: scene round trip, independent history, redo, empty scene, duplicates, bone order, finite transforms and actor limits');
