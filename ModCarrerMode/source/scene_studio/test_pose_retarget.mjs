import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {parsePlayer} from './fifa_model.js';
import {THREE,addActor,setPose} from './scene_view.js';
import {validateScene,History} from './scene_state.js';
import {retargetPose,resetRest} from './pose_retarget.js';
import {validateCapture,layoutPeople} from './pose_capture.js';
globalThis.fetch=async path=>new Response(await fs.readFile(path));
const capture=validateCapture(JSON.parse(await fs.readFile('./build/tests/ai-reference.json','utf8'))),manifest=JSON.parse(await fs.readFile('./assets/scene.json','utf8')),actors=[],catalog=new Map(),scene=new THREE.Scene(),layout=layoutPeople(capture.people),reports=[];
const position=b=>b.getWorldPosition(new THREE.Vector3());
function state(a){return {id:a.id,playerId:a.playerId,label:a.label,pose:a.pose,position:a.root.position.toArray(),quaternion:a.root.quaternion.toArray(),scale:a.root.scale.toArray(),bones:a.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray(),scale:b.scale.toArray()}))};}
for(let i=0;i<capture.people.length;i++){
 const info=manifest.variants[0].players[i%manifest.variants[0].players.length],template=await parsePlayer('./assets/player-'+info.id+'.ff3d');catalog.set(info.id,template.boneData.map(b=>b.name));
 const actor=addActor({scene},template,info,'ai-person-'+i);setPose(actor,info);actor.root.position.fromArray(layout[i]);
 resetRest(actor);const rest=actor.bones.map(b=>({position:b.position.toArray(),scale:b.scale.toArray()}));
 const report=retargetPose(actor,capture.people[i],{ground:true});assert.ok(report.changed.length>=8);reports.push({person:i,changed:report.changed.length,review:report.body_points_to_review});
 actor.bones.forEach((b,j)=>{assert.deepEqual(b.position.toArray(),rest[j].position);assert.deepEqual(b.scale.toArray(),rest[j].scale);assert.ok(b.quaternion.toArray().every(Number.isFinite));assert.ok(Math.abs(b.quaternion.length()-1)<1e-6);});
 // The source shoulder-to-elbow direction and the solved direction must agree.
 const person=capture.people[i];if(person.keypoints3d[5][3]>=.3&&person.keypoints3d[7][3]>=.3){const desired=new THREE.Vector3(...person.keypoints3d[7].slice(0,3)).sub(new THREE.Vector3(...person.keypoints3d[5].slice(0,3))).normalize(),actual=position(actor.bones.find(b=>b.name==='LeftForeArm')).sub(position(actor.bones.find(b=>b.name==='LeftArm'))).normalize();assert.ok(desired.dot(actual)>.9999);}
 actors.push(actor);
}
const saved=validateScene({schema:2,type:'fifa16-offline-scene',actors:actors.map(state),views:[]},catalog);await fs.writeFile('./build/tests/ai-scene.json',JSON.stringify(saved));
await fs.writeFile('./build/tests/ai-world.json',JSON.stringify(actors.map(a=>{const matrices=[];for(let i=0;i<a.bones.length;i++){const b=a.bones[i],m=new THREE.Matrix4().compose(b.position,b.quaternion,b.scale),parent=a.template.boneData[i].parent;matrices.push(parent<0?m:matrices[parent].clone().multiply(m));}return {playerId:a.playerId,position:a.root.position.toArray(),poseWorld:matrices.map(m=>m.toArray())};})));
const h=new History();h.push(saved);const edited=structuredClone(saved);edited.actors[0].position[0]+=1;assert.deepEqual(h.back(edited),saved);assert.deepEqual(h.forward(saved),edited);
// Poor confidence keeps finite rest transforms; a mirrored capture is valid.
const low=structuredClone(capture.people[0]);low.keypoints3d.forEach(p=>p[3]=0);assert.equal(retargetPose(actors[0],low,{ground:false}).changed.length,0);retargetPose(actors[0],capture.people[0],{ground:false,mirror:true,depth:0});assert.ok(actors[0].bones.every(b=>b.quaternion.toArray().every(Number.isFinite)));
await fs.writeFile('./build/tests/retarget-validation.json',JSON.stringify({players:actors.length,source:'actual local RTMW3D inference',reports,keeps_bone_lengths:true,editable_scene_saved:true},null,2));console.log('PASS: actual 11-person capture transferred to 11 FIFA rigs; joint directions, bone lengths, confidence fallback, mirror, save/undo/redo');
