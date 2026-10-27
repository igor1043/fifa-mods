import * as THREE from 'three';

export const LIMBS=Object.freeze({
 LeftHand:{upper:'LeftArm',lower:'LeftForeArm',label:'Punho esquerdo',kind:'arm'},
 RightHand:{upper:'RightArm',lower:'RightForeArm',label:'Punho direito',kind:'arm'},
 LeftFoot:{upper:'LeftUpLeg',lower:'LeftLeg',label:'Pé esquerdo',kind:'leg'},
 RightFoot:{upper:'RightUpLeg',lower:'RightLeg',label:'Pé direito',kind:'leg'}
});
const position=object=>object.getWorldPosition(new THREE.Vector3());
const quaternion=object=>object.getWorldQuaternion(new THREE.Quaternion()).normalize();
function perpendicular(direction,preferred){
 const result=preferred.clone().addScaledVector(direction,-preferred.dot(direction));
 if(result.lengthSq()<1e-12){const fallback=Math.abs(direction.x)<.8?new THREE.Vector3(1,0,0):new THREE.Vector3(0,1,0);result.copy(fallback).addScaledVector(direction,-fallback.dot(direction));}
 return result.normalize();
}

export function limbForBone(actor,index){return actor&&index>=0?LIMBS[actor.bones[index]?.name]||null:null;}

// Work in actor coordinates (centimeters). This keeps reach independent of the
// actor's translation, rotation and even a non-uniform scene scale.
export function createLimbIK(actor,index){
 const config=limbForBone(actor,index);if(!config)return null;
 const upper=actor.bones.find(b=>b.name===config.upper),lower=actor.bones.find(b=>b.name===config.lower),end=actor.bones[index];
 if(!upper||!lower||lower.parent!==upper||end.parent!==lower)return null;
 actor.root.updateMatrixWorld(true);
 const inverse=actor.root.matrixWorld.clone().invert(),a=position(upper).applyMatrix4(inverse),b=position(lower).applyMatrix4(inverse),c=position(end).applyMatrix4(inverse);
 const first=a.distanceTo(b),second=b.distanceTo(c);if(first<1e-6||second<1e-6)return null;
 let axis=c.clone().sub(a);if(axis.lengthSq()<1e-12)axis.copy(b).sub(a);axis.normalize();
 const rawBend=b.clone().sub(a).addScaledVector(axis,-b.clone().sub(a).dot(axis));
 // Almost straight knees are ill-conditioned. Keep the real plane when it is
// defined, otherwise use the front of the actor (legs) or down (arms).
 const bend=perpendicular(axis,rawBend.length()>(first+second)*1e-5?rawBend:config.kind==='leg'?new THREE.Vector3(0,0,1):new THREE.Vector3(0,-1,0));
 return {actor,index,config,upper,lower,end,a,axis,bend,first,second,
  startUpper:upper.quaternion.clone(),startLower:lower.quaternion.clone(),startEnd:end.quaternion.clone(),endWorld:quaternion(end)};
}

function pointBone(bone,child,targetWorld){
 bone.parent.updateWorldMatrix(true,false);
 const inverse=bone.parent.matrixWorld.clone().invert(),start=position(bone).applyMatrix4(inverse);
 const current=position(child).applyMatrix4(inverse).sub(start).normalize(),desired=targetWorld.clone().applyMatrix4(inverse).sub(start).normalize();
 bone.quaternion.premultiply(new THREE.Quaternion().setFromUnitVectors(current,desired)).normalize();bone.updateMatrixWorld(true);
}

// Analytic two-bone IK: change rotations only. The target never translates a
// wrist/ankle out of its joint, stretches a segment, or modifies the torso.
export function solveLimbIK(chain,targetWorld,{bend=0,keepRotation=true}={}){
 if(!chain||!targetWorld?.isVector3||![targetWorld.x,targetWorld.y,targetWorld.z,bend].every(Number.isFinite))throw Error('Alvo IK inválido.');
 const {actor,upper,lower,end,first,second,a}=chain;
 upper.quaternion.copy(chain.startUpper);lower.quaternion.copy(chain.startLower);end.quaternion.copy(chain.startEnd);actor.root.updateMatrixWorld(true);
 const target=targetWorld.clone().applyMatrix4(actor.root.matrixWorld.clone().invert()),direction=target.clone().sub(a),requested=direction.length();
 if(requested<1e-10)direction.copy(chain.axis);else direction.divideScalar(requested);
 const epsilon=(first+second)*1e-5,minReach=Math.abs(first-second)+epsilon,maxReach=first+second-epsilon,distance=THREE.MathUtils.clamp(requested,minReach,maxReach);
 const bendDirection=perpendicular(direction,chain.bend.clone().applyQuaternion(new THREE.Quaternion().setFromUnitVectors(chain.axis,direction))).applyAxisAngle(direction,bend);
 const along=(distance*distance+first*first-second*second)/(2*distance),height=Math.sqrt(Math.max(0,first*first-along*along));
 const elbow=a.clone().addScaledVector(direction,along).addScaledVector(bendDirection,height),goal=a.clone().addScaledVector(direction,distance);
 pointBone(upper,lower,elbow.applyMatrix4(actor.root.matrixWorld));pointBone(lower,end,goal.applyMatrix4(actor.root.matrixWorld));
 if(keepRotation){end.quaternion.copy(quaternion(end.parent).invert().multiply(chain.endWorld)).normalize();end.updateMatrixWorld(true);}
 actor.root.updateMatrixWorld(true);actor.skeleton.update();
 const actual=position(end),error=actual.distanceTo(targetWorld);
 return {position:actual,clamped:Math.abs(distance-requested)>epsilon*.01,error,points:[position(upper),position(lower),actual.clone()]};
}
