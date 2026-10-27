import * as THREE from 'three';
const mirrorIndex=i=>{
 if(i>=1&&i<=16)return i%2?i+1:i-1;
 if(i>=17&&i<=19)return i+3;if(i>=20&&i<=22)return i-3;
 if(i>=91&&i<=111)return i+21;if(i>=112&&i<=132)return i-21;return i;
};
export function resetRest(actor){
 actor.bones.forEach((bone,i)=>{const data=actor.template.boneData[i],local=data.parent<0?data.restWorld.clone():actor.template.boneData[data.parent].restWorld.clone().invert().multiply(data.restWorld);local.decompose(bone.position,bone.quaternion,bone.scale);bone.quaternion.normalize();});actor.root.updateMatrixWorld(true);actor.skeleton.update();
}
function frame(x,y){
 if(x.lengthSq()<1e-10||y.lengthSq()<1e-10)return null;x.normalize();y.addScaledVector(x,-x.dot(y));if(y.lengthSq()<1e-10)return null;y.normalize();const z=new THREE.Vector3().crossVectors(x,y).normalize();return new THREE.Matrix4().makeBasis(x,y,z);
}
export function retargetPose(actor,person,{confidence=.3,depth=1,mirror=false,fingers=true,ground=true}={}){
 if(!actor||!person||person.keypoints3d?.length!==133||!Number.isFinite(confidence)||confidence<0||confidence>1||!Number.isFinite(depth)||depth<0||depth>2)throw Error('Pose ou configuração inválida.');
 if(person.keypoints3d.some(p=>!Array.isArray(p)||p.length!==4||p.some(v=>!Number.isFinite(v))))throw Error('Coordenadas inválidas.');
 resetRest(actor);const report={changed:[],missing:[],body_points_to_review:person.keypoints3d.slice(0,23).filter(p=>p[3]<confidence).length};
 const find=name=>actor.bones.find(b=>b.name===name),rootInverse=()=>actor.root.matrixWorld.clone().invert();
 const point=b=>b.getWorldPosition(new THREE.Vector3()).applyMatrix4(rootInverse());
 const source=(i,minimum=confidence)=>{const p=person.keypoints3d[mirror?mirrorIndex(i):i];return p[3]<minimum?null:new THREE.Vector3(p[0]*(mirror?-100:100),p[1]*100,p[2]*100*depth);};
 const average=(i,j)=>{const a=source(i),b=source(j);return a&&b?a.add(b).multiplyScalar(.5):null;};
 function align(boneName,childName,from,to){
  const bone=find(boneName),child=find(childName),minimum=from>=91?Math.max(confidence,.5):confidence,a=source(from,minimum),b=source(to,minimum);
  if(!bone||!child||!a||!b){report.missing.push(boneName);return;}
  const inverse=bone.parent.matrixWorld.clone().premultiply(rootInverse()).invert(),current=point(child).sub(point(bone)).transformDirection(inverse),target=b.sub(a).transformDirection(inverse);
  if(current.lengthSq()<1e-10||target.lengthSq()<1e-10){report.missing.push(boneName);return;}
  bone.quaternion.premultiply(new THREE.Quaternion().setFromUnitVectors(current,target)).normalize();bone.updateMatrixWorld(true);report.changed.push(boneName);
 }
 function orient(boneName,currentX,currentY,targetX,targetY){
  const bone=find(boneName),a=frame(currentX,currentY),b=frame(targetX,targetY);if(!bone||!a||!b)return;
  const parent=new THREE.Quaternion();bone.parent.matrixWorld.clone().premultiply(rootInverse()).decompose(new THREE.Vector3(),parent,new THREE.Vector3());parent.normalize();const delta=new THREE.Quaternion().setFromRotationMatrix(b.multiply(a.invert())).normalize();
  bone.quaternion.premultiply(parent.clone().invert().multiply(delta).multiply(parent)).normalize();bone.updateMatrixWorld(true);report.changed.push(boneName);
 }
 const hip=average(11,12),shoulder=average(5,6),leftHip=source(11),rightHip=source(12),leftShoulder=source(5),rightShoulder=source(6);
 if(hip&&shoulder&&leftHip&&rightHip){orient('Hips',point(find('LeftUpLeg')).sub(point(find('RightUpLeg'))),point(find('Spine3')).sub(point(find('Hips'))),leftHip.clone().sub(rightHip),shoulder.clone().sub(hip));}
 if(hip&&shoulder&&leftShoulder&&rightShoulder){orient('Spine',point(find('LeftArm')).sub(point(find('RightArm'))),point(find('Spine3')).sub(point(find('Hips'))),leftShoulder.clone().sub(rightShoulder),shoulder.clone().sub(hip));}
 for(const [side,offset] of [['Left',0],['Right',1]]){
  align(side+'UpLeg',side+'Leg',11+offset,13+offset);align(side+'Leg',side+'Foot',13+offset,15+offset);
  align(side+'Foot',side+'ToeBase',19+offset*3,17+offset*3);
  align(side+'Arm',side+'ForeArm',5+offset,7+offset);align(side+'ForeArm',side+'Hand',7+offset,9+offset);
  const start=side==='Left'?91:112,wrist=source(9+offset),middle=source(start+9),index=source(start+5),pinky=source(start+17);
  if(wrist&&middle&&index&&pinky)orient(side+'Hand',point(find(side+'HandIndex1')).sub(point(find(side+'HandPinky1'))),point(find(side+'HandMiddle1')).sub(point(find(side+'Hand'))),index.clone().sub(pinky),middle.clone().sub(wrist));
  if(fingers)for(const [finger,n] of [['Thumb',1],['Index',5],['Middle',9],['Ring',13],['Pinky',17]])for(let j=0;j<3;j++)align(side+'Hand'+finger+(j+1),side+'Hand'+finger+(j===2?'End':j+2),start+n+j,start+n+j+1);
 }
 // The longer chin-to-nose-bridge axis is more stable than the tiny depth
 // difference between nose and ears, especially with stylized/game faces.
 // COCO WholeBody face points 23..90 follow the standard 68-point topology.
 const le=source(3),re=source(4),bridge=source(50,Math.max(confidence,.4)),chin=source(31,Math.max(confidence,.4));
 if(le&&re&&bridge&&chin){const x=le.clone().sub(re),y=bridge.clone().sub(chin),bone=find('Head'),m=bone.matrixWorld.clone().premultiply(rootInverse());orient('Head',new THREE.Vector3(0,0,1).transformDirection(m),new THREE.Vector3(1,0,0).transformDirection(m),x,y);}
 actor.root.updateMatrixWorld(true);actor.skeleton.update();
 if(ground){
  let floor=Infinity;actor.meshes.forEach((mesh,i)=>{if(!actor.template.parts[i].asset.includes('/shoe/'))return;const v=new THREE.Vector3();for(let j=0;j<mesh.geometry.attributes.position.count;j++){mesh.getVertexPosition(j,v).applyMatrix4(mesh.matrixWorld);floor=Math.min(floor,v.y);}});
  if(Number.isFinite(floor))actor.root.position.y-=floor;
 }
 actor.root.updateMatrixWorld(true);actor.skeleton.update();return report;
}
