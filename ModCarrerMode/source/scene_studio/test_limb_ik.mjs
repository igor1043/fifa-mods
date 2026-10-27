import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import * as THREE from 'three';
import {LIMBS,createLimbIK,solveLimbIK,limbForBone} from './limb_ik.js';
import {History,validateScene} from './scene_state.js';
const fixture=JSON.parse(await fs.readFile('./build/tests/baseline-scene.json','utf8'));
const raw=await fs.readFile('./assets/player-'+fixture.actors[0].playerId+'.ff3d');let cursor=28;
const skipName=()=>{const n=raw.readUInt32LE(cursor);cursor+=4+n;};skipName();const parents=[];
for(let i=0;i<raw.readUInt32LE(16);i++){skipName();parents.push(raw.readInt32LE(cursor));cursor+=4+64;}
function makeActor(state){
 const root=new THREE.Group(),bones=state.bones.map(b=>Object.assign(new THREE.Bone(),{name:b.name}));
 bones.forEach((b,i)=>(parents[i]<0?root:bones[parents[i]]).add(b));
 const actor={root,bones,skeleton:new THREE.Skeleton(bones)};reset(actor,state);return actor;
}
function reset(actor,state){
 actor.root.position.fromArray(state.position);actor.root.quaternion.fromArray(state.quaternion);actor.root.scale.fromArray(state.scale);
 actor.bones.forEach((b,i)=>{b.position.fromArray(state.bones[i].position);b.quaternion.fromArray(state.bones[i].quaternion);b.scale.fromArray(state.bones[i].scale);});actor.root.updateMatrixWorld(true);actor.skeleton.update();
}
const pos=b=>b.getWorldPosition(new THREE.Vector3()),local=(actor,p)=>p.clone().applyMatrix4(actor.root.matrixWorld.clone().invert());
const saveBones=a=>a.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray(),scale:b.scale.toArray()}));
let checks=0,maxTargetError=0,maxLengthError=0;
function checkLengths(chain){
 const a=local(chain.actor,pos(chain.upper)),b=local(chain.actor,pos(chain.lower)),c=local(chain.actor,pos(chain.end));
 const error=Math.max(Math.abs(a.distanceTo(b)-chain.first),Math.abs(b.distanceTo(c)-chain.second));maxLengthError=Math.max(maxLengthError,error);assert.ok(error<.001,'Segment length changed: '+error);
}
for(const state of fixture.actors){
 const actor=makeActor(state);
 for(const name of Object.keys(LIMBS)){
  const index=actor.bones.findIndex(b=>b.name===name);assert.ok(limbForBone(actor,index));
  for(const transformed of [false,true]){
   reset(actor,state);
   if(transformed){actor.root.position.set(2,1,-.3);actor.root.rotation.set(.15,.6,-.1);actor.root.scale.set(.02,.015,.03);actor.root.updateMatrixWorld(true);}
   const before=saveBones(actor),chain=createLimbIK(actor,index);assert.ok(chain);
   // The target that matches the current wrist/ankle must preserve the pose.
   let result=solveLimbIK(chain,pos(chain.end));assert.ok(result.error<.00002);checkLengths(chain);
   const direction=chain.axis.clone().add(new THREE.Vector3(.2,-.1,.4)).normalize();
   const targetLocal=chain.a.clone().addScaledVector(direction,(chain.first+chain.second)*.72),target=targetLocal.clone().applyMatrix4(actor.root.matrixWorld);
   const orientation=chain.endWorld.clone();result=solveLimbIK(chain,target);maxTargetError=Math.max(maxTargetError,result.error);assert.ok(result.error<.00002,name+' target error '+result.error);checkLengths(chain);
   if(!transformed){const angle=orientation.angleTo(chain.end.getWorldQuaternion(new THREE.Quaternion()).normalize());assert.ok(angle<.0001,'Effector orientation changed: '+name+' '+angle);}
   const firstBend=local(actor,pos(chain.lower)).sub(chain.a).projectOnPlane(direction).normalize();
   result=solveLimbIK(chain,target,{bend:Math.PI});assert.ok(result.error<.00002);checkLengths(chain);
   const otherBend=local(actor,pos(chain.lower)).sub(chain.a).projectOnPlane(direction).normalize();assert.ok(firstBend.dot(otherBend)<-.9999,'Pole direction did not reverse');
   // Solving the same target repeatedly is stable, including after a different
   // target. Each pointer move starts from a fixed chain frame, without drift.
   solveLimbIK(chain,target.clone().add(new THREE.Vector3(.01,.02,.01)));const stable=solveLimbIK(chain,target,{bend:Math.PI});
   assert.ok(stable.position.distanceTo(result.position)<1e-8);
   const far=chain.a.clone().addScaledVector(direction,(chain.first+chain.second)*10).applyMatrix4(actor.root.matrixWorld);
   result=solveLimbIK(chain,far);assert.equal(result.clamped,true);checkLengths(chain);
   result=solveLimbIK(chain,chain.a.clone().applyMatrix4(actor.root.matrixWorld));assert.equal(result.clamped,true);checkLengths(chain);
   const changed=new Set([chain.upper,chain.lower,chain.end]);
   actor.bones.forEach((b,i)=>{assert.deepEqual(b.position.toArray(),before[i].position,'IK translated '+b.name);assert.deepEqual(b.scale.toArray(),before[i].scale,'IK scaled '+b.name);if(!changed.has(b))assert.deepEqual(b.quaternion.toArray(),before[i].quaternion,'IK changed unrelated bone '+b.name);assert.ok(b.quaternion.toArray().every(Number.isFinite));});
   checks++;
  }
 }
 assert.equal(createLimbIK(actor,actor.bones.findIndex(b=>b.name==='Spine')),null);
}
// Resolved transforms, rather than transient gizmo targets, are saved. Undo and
// redo keep an IK result without requiring a solver on import or in the game.
const state=fixture.actors[0],actor=makeActor(state),chain=createLimbIK(actor,actor.bones.findIndex(b=>b.name==='LeftHand'));
solveLimbIK(chain,chain.a.clone().add(new THREE.Vector3(22,-22,14)).applyMatrix4(actor.root.matrixWorld));
const leg=createLimbIK(actor,actor.bones.findIndex(b=>b.name==='LeftFoot'));solveLimbIK(leg,leg.a.clone().add(new THREE.Vector3(5,-55,20)).applyMatrix4(actor.root.matrixWorld));
const edited=structuredClone(fixture);edited.actors[0].bones=saveBones(actor);
const catalog=new Map(fixture.actors.map(a=>[a.playerId,a.bones.map(b=>b.name)]));validateScene(edited,catalog);
const history=new History();history.push(fixture);assert.deepEqual(history.back(edited).actors[0].bones,fixture.actors[0].bones);assert.deepEqual(history.forward(fixture).actors[0].bones,edited.actors[0].bones);
await fs.writeFile('./build/tests/ik-scene.json',JSON.stringify(edited));
const report={limbs:Object.keys(LIMBS),players:fixture.actors.length,configurations:checks,max_target_error_m:maxTargetError,max_segment_error_cm:maxLengthError,unchanged_joint_positions:true,undo_redo_round_trip:true};
await fs.writeFile('./build/tests/ik-validation.json',JSON.stringify(report,null,2));console.log('PASS:',JSON.stringify(report));
