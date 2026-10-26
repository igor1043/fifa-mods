import * as THREE from 'three';
import {OrbitControls} from './vendor/three/examples/jsm/controls/OrbitControls.js';
import {TransformControls} from './vendor/three/examples/jsm/controls/TransformControls.js';
export {THREE};
export const mainBone=name=>/^(Reference|Hips|Spine[0-9]*|Neck|Head|Left(Shoulder|Arm|ForeArm|Hand|UpLeg|Leg|Foot|ToeBase)|Right(Shoulder|Arm|ForeArm|Hand|UpLeg|Leg|Foot|ToeBase))$/.test(name);
export function enableEightWeights(material){
 material.onBeforeCompile=shader=>{
  shader.vertexShader=shader.vertexShader.replace('#include <skinning_pars_vertex>','#include <skinning_pars_vertex>\nattribute vec4 skinIndex2;\nattribute vec4 skinWeight2;');
  const extra='skinWeight2.x * getBoneMatrix(skinIndex2.x) + skinWeight2.y * getBoneMatrix(skinIndex2.y) + skinWeight2.z * getBoneMatrix(skinIndex2.z) + skinWeight2.w * getBoneMatrix(skinIndex2.w)';
  shader.vertexShader=shader.vertexShader.replace('#include <skinnormal_vertex>',THREE.ShaderChunk.skinnormal_vertex.replace('skinMatrix = bindMatrixInverse','skinMatrix += '+extra+';\n skinMatrix = bindMatrixInverse'));
  shader.vertexShader=shader.vertexShader.replace('#include <skinning_vertex>',THREE.ShaderChunk.skinning_vertex.replace('transformed =','skinned += ('+extra+') * skinVertex;\n transformed ='));
 };material.customProgramCacheKey=()=> 'fifa-editor-eight-weights-v2';
}
// Three's stock picking uses four weights. The FIFA meshes retain eight, so
// CPU bounds/picking must use the same eight influences as the GPU shader.
export function eightWeightCPU(mesh){
 const source=new THREE.Vector3(),point=new THREE.Vector3(),matrix=new THREE.Matrix4();
 mesh.applyBoneTransform=function(index,target){
  source.copy(target).applyMatrix4(this.bindMatrix);target.set(0,0,0);
  for(let slot=0;slot<8;slot++){
   const j=this.geometry.getAttribute(slot<4?'skinIndex':'skinIndex2'),w=this.geometry.getAttribute(slot<4?'skinWeight':'skinWeight2'),weight=w.getComponent(index,slot%4);
   if(weight){matrix.fromArray(this.skeleton.boneMatrices,j.getComponent(index,slot%4)*16);target.addScaledVector(point.copy(source).applyMatrix4(matrix),weight);}
  }return target.applyMatrix4(this.bindMatrixInverse);
 };
}
export function makeViewport(canvas,stage){
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.95;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
 const scene=new THREE.Scene();scene.background=new THREE.Color(0x28333c);scene.fog=new THREE.Fog(0x28333c,25,80);
 const camera=new THREE.PerspectiveCamera(34,1,.02,200);camera.position.set(0,1.5,8);
 const orbit=new OrbitControls(camera,canvas);orbit.target.set(0,.9,0);orbit.enableDamping=true;orbit.minDistance=.2;orbit.maxDistance=60;
 const gizmo=new TransformControls(camera,canvas);gizmo.setSpace('local');gizmo.setMode('translate');gizmo.setSize(.7);scene.add(gizmo.getHelper());
 scene.add(new THREE.HemisphereLight(0xd9e8f2,0x606259,1.1));
 const key=new THREE.DirectionalLight(0xfff4e7,2.1);key.position.set(-3,7,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-8,right:8,top:8,bottom:-8,near:.1,far:30});key.shadow.bias=-.00015;key.shadow.normalBias=.012;key.target.position.set(0,.9,0);scene.add(key,key.target);
 const fill=new THREE.DirectionalLight(0xd8e7ff,.6);fill.position.set(5,3,-3);scene.add(fill);
 const ground=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:0x586466,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.008;ground.receiveShadow=true;scene.add(ground);
 const grid=new THREE.GridHelper(30,60,0x9badb4,0x63747c);grid.position.y=-.005;grid.material.transparent=true;grid.material.opacity=.32;scene.add(grid);
 const marker=new THREE.Mesh(new THREE.SphereGeometry(.015,12,8),new THREE.MeshBasicMaterial({color:0xffd275,depthTest:false}));marker.visible=false;marker.renderOrder=100;scene.add(marker);
 const points=new THREE.InstancedMesh(new THREE.SphereGeometry(.018,8,6),new THREE.MeshBasicMaterial({color:0x74e4c6,depthTest:false}),1024);points.frustumCulled=false;points.instanceMatrix.setUsage(THREE.DynamicDrawUsage);points.visible=false;points.renderOrder=90;points.count=0;scene.add(points);
 const selection=new THREE.Box3Helper(new THREE.Box3(),0xf3c87a);selection.visible=false;selection.material.depthTest=false;selection.renderOrder=50;scene.add(selection);
 let all=[],selected=null,bone=-1,boneView=false,full=false,pickIndices=[],paused=false;
 const invalidate=()=>renderer.shadowMap.needsUpdate=true;
 function refresh(){
  for(const a of all){a.root.updateMatrixWorld(true);a.skeleton.update();a.helper.visible=boneView&&full&&a===selected;}
  points.visible=boneView&&!!selected;points.count=0;pickIndices=[];
  if(selected&&boneView){
   const m=new THREE.Matrix4();for(let i=0;i<selected.bones.length;i++)if(full||mainBone(selected.bones[i].name)){
    m.makeTranslation(...selected.bones[i].getWorldPosition(new THREE.Vector3()).toArray());points.setMatrixAt(points.count++,m);pickIndices.push(i);
   }points.instanceMatrix.needsUpdate=true;
  }
  marker.visible=boneView&&!!selected&&bone>=0;
  if(marker.visible)selected.bones[bone].getWorldPosition(marker.position);
 }
 function bounds(actor){actor.root.updateMatrixWorld(true);actor.skeleton.update();const box=new THREE.Box3();for(const mesh of actor.meshes){mesh.computeBoundingBox();box.union(mesh.boundingBox.clone().applyMatrix4(mesh.matrixWorld));}return box;}
 function select(actor,index=-1){
  selected=actor;bone=index;gizmo.detach();selection.visible=!!actor&&!boneView;
  if(actor){gizmo.attach(boneView&&index>=0?actor.bones[index]:actor.root);if(boneView&&index<0)gizmo.detach();selection.box.copy(bounds(actor));}refresh();
 }
 new ResizeObserver(()=>{const {width,height}=stage.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}).observe(stage);
 renderer.setAnimationLoop(()=>{if(paused)return;orbit.update();refresh();renderer.render(scene,camera);});
 return {renderer,scene,camera,orbit,gizmo,grid,key,bounds,invalidate,refresh,
  setPaused(value){paused=!!value;},
  setActors(values){all=values;refresh();},setSelection:select,
  setSkeleton(value,complete=false){boneView=value;full=complete;select(selected,bone);},
  pick(x,y){
   const rect=canvas.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((x-rect.left)/rect.width*2-1,-(y-rect.top)/rect.height*2+1),camera);
   if(boneView&&selected){refresh();points.computeBoundingSphere();const hit=ray.intersectObject(points)[0];if(hit)return {actor:selected,bone:pickIndices[hit.instanceId]};}
   for(const actor of all)for(const mesh of actor.meshes){mesh.computeBoundingBox();mesh.computeBoundingSphere();}
   const hits=ray.intersectObjects(all.flatMap(a=>a.meshes),false);if(hits[0])return {actor:all.find(a=>a.root===hits[0].object.parent),bone:-1};return null;
  },
  frame(actor=null,direction='front'){
   if(!all.length)return;const box=new THREE.Box3();for(const a of actor?[actor]:all)box.union(bounds(a));
   const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3()),distance=Math.max(size.y,size.x/Math.max(.5,camera.aspect))/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.18;
   const offset=direction==='side'?new THREE.Vector3(distance,.1,0):direction==='top'?new THREE.Vector3(0,distance,.001):new THREE.Vector3(0,distance*.04,distance);
   orbit.target.copy(center);camera.position.copy(center).add(offset);orbit.update();
  },
  disposeActor(a){if(selected===a)select(null);scene.remove(a.root,a.helper);a.skeleton.dispose();a.helper.geometry.dispose();a.helper.material.dispose();for(const m of a.meshes){m.material.dispose();m.customDepthMaterial.dispose();}}
 };
}
export function addActor(view,template,info,id){
 const root=new THREE.Group();root.scale.setScalar(.01);root.position.fromArray(info.position).multiplyScalar(.01);view.scene.add(root);
 const bones=template.boneData.map(d=>{const bone=new THREE.Bone();bone.name=d.name;return bone;});
 for(let i=0;i<bones.length;i++){const d=template.boneData[i],M=d.parent<0?d.restWorld.clone():template.boneData[d.parent].restWorld.clone().invert().multiply(d.restWorld);M.decompose(bones[i].position,bones[i].quaternion,bones[i].scale);(d.parent<0?root:bones[d.parent]).add(bones[i]);}
 root.updateMatrixWorld(true);const skeleton=new THREE.Skeleton(bones,template.boneData.map(d=>d.inverse.clone())),meshes=[];
 for(const part of template.parts){
  const material=part.material.clone();material.toneMapped=true;material.roughness=.85;enableEightWeights(material);
  const mesh=new THREE.SkinnedMesh(part.geometry,material);mesh.frustumCulled=false;mesh.castShadow=true;mesh.receiveShadow=false;mesh.name=part.name;root.add(mesh);mesh.bind(skeleton,new THREE.Matrix4());eightWeightCPU(mesh);
  mesh.customDepthMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking,map:material.map,alphaTest:material.alphaTest,side:THREE.DoubleSide});enableEightWeights(mesh.customDepthMaterial);meshes.push(mesh);
 }
 const helper=new THREE.SkeletonHelper(root);helper.material.depthTest=false;helper.material.color.set(0x74e4c6);helper.renderOrder=20;helper.visible=false;view.scene.add(helper);
 return {id,playerId:info.id,label:info.name,root,bones,skeleton,meshes,helper,template,info,base:[],pose:'baseline'};
}
export function setPose(actor,info,pose='baseline'){
 const world=info.poseWorld.map(m=>new THREE.Matrix4().fromArray(m));
 for(let i=0;i<actor.bones.length;i++){const parent=actor.template.boneData[i].parent,M=parent<0?world[i]:world[parent].clone().invert().multiply(world[i]);M.decompose(actor.bones[i].position,actor.bones[i].quaternion,actor.bones[i].scale);}
 actor.base=actor.bones.map(b=>({position:b.position.clone(),quaternion:b.quaternion.clone(),scale:b.scale.clone()}));actor.pose=pose;actor.root.updateMatrixWorld(true);actor.skeleton.update();
}
