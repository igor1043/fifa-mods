import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {parsePlayer} from './fifa_model.js';
import {THREE,addActor,setPose} from './scene_view.js';
import {validateScene} from './scene_state.js';
const read=async path=>JSON.parse(await fs.readFile(path,'utf8'));
const manifest=await read('./assets/scene.json');
// Exercise file parsing and CPU skinning, without driving or mocking a browser.
globalThis.fetch=async path=>new Response(await fs.readFile(path));
const scene=new THREE.Scene(),view={scene},actors=[],catalog=new Map();
const original=await fs.readFile('./assets/baseline.ff3d');let offset=16,maxError=0,count=0;
for(const info of manifest.variants[0].players){
 const template=await parsePlayer('./assets/player-'+info.id+'.ff3d');catalog.set(info.id,template.boneData.map(b=>b.name));
 const actor=addActor(view,template,info,'player-'+info.id);setPose(actor,info);actors.push(actor);
 for(const mesh of actor.meshes){
  const nv=original.readUInt32LE(offset),ni=original.readUInt32LE(offset+4);offset+=44;assert.equal(mesh.geometry.attributes.position.count,nv);
  for(let i=0;i<nv;i++){
   const p=mesh.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(mesh.matrixWorld).multiplyScalar(100);
   for(const [axis,k] of [['x',0],['y',1],['z',2]])maxError=Math.max(maxError,Math.abs(p[axis]-original.readFloatLE(offset+i*32+k*4)));
  }offset+=nv*32+ni*4;count++;
 }
}
assert.ok(maxError<.003,'Eight-weight CPU geometry differs from native output: '+maxError);
const snapshot=()=>({schema:2,type:'fifa16-offline-scene',actors:actors.map(a=>({id:a.id,playerId:a.playerId,label:a.label,pose:a.pose,position:a.root.position.toArray(),quaternion:a.root.quaternion.toArray(),scale:a.root.scale.toArray(),bones:a.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray(),scale:b.scale.toArray()}))})),views:[],camera:{position:[0,1.5,8],target:[0,.9,0]}});
const saved=validateScene(snapshot(),catalog);await fs.mkdir('./build/tests',{recursive:true});await fs.writeFile('./build/tests/baseline-scene.json',JSON.stringify(saved));
// A duplicate owns its skeleton/materials and keeps shared immutable geometry.
const source=actors[0],copy=addActor(view,source.template,source.info,'copy');setPose(copy,source.info);
const index=source.bones.findIndex(b=>b.name==='LeftArm'),q=source.bones[index].quaternion.clone();
copy.bones[index].rotateY(.25);copy.root.position.x+=1;copy.root.updateMatrixWorld(true);copy.skeleton.update();
assert.ok(source.bones[index].quaternion.equals(q));assert.notEqual(copy.skeleton,source.skeleton);assert.notEqual(copy.meshes[0].material,source.meshes[0].material);
assert.equal(copy.meshes[0].geometry,source.meshes[0].geometry);assert.equal(copy.bones.length,400);
// After a bone edit the selected actor's bounds can be rebuilt for picking.
copy.meshes[0].computeBoundingBox();copy.meshes[0].computeBoundingSphere();assert.ok(Number.isFinite(copy.meshes[0].boundingSphere.radius));
const report={players:actors.length,bones_per_player:400,parts:count,max_error_cm:maxError,independent_actor_skeletons:true};
await fs.writeFile('./build/tests/geometry-validation.json',JSON.stringify(report,null,2));console.log('PASS:',JSON.stringify(report));
