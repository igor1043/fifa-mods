import {THREE,makeViewport,addActor,setPose} from './scene_view.js';
import {parsePlayer} from './fifa_model.js';
import {validateScene,History,MAX_ACTORS} from './scene_state.js';
import {limbForBone,createLimbIK,solveLimbIK} from './limb_ik.js';
import {setupImagePose} from './image_pose_ui.js';
import {retargetPose} from './pose_retarget.js';
import {layoutPeople} from './pose_capture.js';
const $=id=>document.getElementById(id),view=makeViewport($('canvas'),$('stage'));
document.querySelector('main').inert=true;document.querySelector('.header-tools').inert=true;
let manifest,actors=[],selected=null,bone=-1,mode='object',operation='translate',space='local',templates=new Map(),views=[],loading=true,saveTimer,toastTimer,pointerStart,gesture=false,dirty=false;
const history=new History(),draftKey='fifa-friends-scene-editor-v2';
let activeIK=null;
const ikTarget=new THREE.Group();ikTarget.name='editor-ik-target';view.scene.add(ikTarget);
const ikDot=new THREE.Mesh(new THREE.SphereGeometry(.024,12,8),new THREE.MeshBasicMaterial({color:0xffc169,depthTest:false}));ikDot.renderOrder=110;ikDot.visible=false;ikTarget.add(ikDot);
const ikLine=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3(),new THREE.Vector3()]),new THREE.LineBasicMaterial({color:0xffc169,depthTest:false,transparent:true,opacity:.85}));ikLine.frustumCulled=false;ikLine.renderOrder=100;ikLine.visible=false;view.scene.add(ikLine);
const current=()=>selected&&actors.find(a=>a.id===selected),catalog=()=>new Map([...templates].map(([id,t])=>[id,t.boneData.map(b=>b.name)]));
function toast(message){$('toast').textContent=message;$('toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').style.display='none',3500);}
function status(message){$('status').textContent=message;}
function snapshot(){return {schema:2,type:'fifa16-offline-scene',selection:{actor:selected,bone,mode,ik:$('ikEnabled').checked,keepRotation:$('ikKeepRotation').checked},actors:actors.map(a=>({id:a.id,playerId:a.playerId,label:a.label,pose:a.pose,position:a.root.position.toArray(),quaternion:a.root.quaternion.toArray(),scale:a.root.scale.toArray(),bones:a.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray(),scale:b.scale.toArray()}))})),views:structuredClone(views),camera:{position:view.camera.position.toArray(),target:view.orbit.target.toArray()}};}
function remember(){if(!loading)history.push(snapshot());}
function changed(){view.invalidate();dirty=true;clearTimeout(saveTimer);if(loading)return;saveTimer=setTimeout(()=>{try{localStorage.setItem(draftKey,JSON.stringify(snapshot()));$('recover').disabled=false;}catch{}},700);sync();}
function create(playerId,position=null){
 if(actors.length>=MAX_ACTORS)throw Error('Limite de '+MAX_ACTORS+' jogadores nesta cena.');
 const info=manifest.variants[0].players.find(p=>p.id===playerId);if(!info)throw Error('Jogador não encontrado.');
 const actor=addActor(view,templates.get(playerId),info,crypto.randomUUID());setPose(actor,info);if(position)actor.root.position.fromArray(position);actors.push(actor);view.setActors(actors);return actor;
}
function renderList(){
 $('objects').replaceChildren();for(const a of actors){const button=document.createElement('button');button.classList.toggle('active',a.id===selected);button.textContent=a.label;
  const sub=document.createElement('span');sub.className='object-sub';sub.textContent='#'+a.playerId+' · '+a.bones.length+' ossos';button.appendChild(sub);button.onclick=()=>select(a.id);$('objects').appendChild(button);
 }$('count').textContent='('+actors.length+')';$('empty').style.display=actors.length?'none':'block';
}
function renderBones(){
 const a=current();$('bones').replaceChildren();if(!a)return;const query=$('filter').value.toLowerCase();
 a.bones.forEach((b,i)=>{if(($('armsOnly').checked&&!/Arm|Hand|Elbow|Shoulder|Radialis/i.test(b.name))||!b.name.toLowerCase().includes(query))return;$('bones').add(new Option(b.name,String(i)));});if(bone>=0)$('bones').value=String(bone);
}
function select(id,index=-1){selected=id;bone=index;renderList();renderBones();attach();sync();}
function attach(preserveIK=false){
 preserveIK=preserveIK===true;
 const a=current();view.setSkeleton(mode==='bone'||$('skeleton').checked,$('skeletonDetail').value==='all');
 view.setSelection(a||null,mode==='bone'?bone:-1);view.gizmo.setMode(operation);view.gizmo.setSpace(space);
 if(mode==='object'&&a)view.gizmo.attach(a.root);if(mode==='bone'&&bone<0)view.gizmo.detach();
 const enabled=mode==='bone'&&operation==='translate'&&$('ikEnabled').checked&&limbForBone(a,bone);
 if(enabled){
  if(!preserveIK||activeIK?.actor!==a||activeIK?.index!==bone){activeIK=createLimbIK(a,bone);$('ikBend').value='0';$('ikBendValue').textContent='0°';}
  if(activeIK){activeIK.end.getWorldPosition(ikTarget.position);ikTarget.updateMatrixWorld(true);view.gizmo.attach(ikTarget);view.gizmo.setSpace('world');ikLine.geometry.setFromPoints([activeIK.upper,activeIK.lower,activeIK.end].map(b=>b.getWorldPosition(new THREE.Vector3())));}
 }else activeIK=null;
 ikDot.visible=ikLine.visible=!!activeIK;$('space').disabled=!!activeIK;$('space').textContent=activeIK?'Global · IK':space==='local'?'Local':'Global';
 $('ikBend').disabled=$('ikFlip').disabled=!activeIK;
 $('ikFeedback').textContent=activeIK?activeIK.config.label+' · arraste os eixos; ajuste a dobra se precisar.':'Escolha um punho ou pé e use W · Mover para ativar IK.';
}
function applyIK(){
 if(!activeIK)return;const result=solveLimbIK(activeIK,ikTarget.position,{bend:THREE.MathUtils.degToRad(Number($('ikBend').value)),keepRotation:$('ikKeepRotation').checked});
 ikTarget.position.copy(result.position);ikTarget.updateMatrixWorld(true);ikLine.geometry.setFromPoints(result.points);view.invalidate();
 $('ikBendValue').textContent=$('ikBend').value+'°';$('ikFeedback').textContent=result.clamped?'Limite de alcance: o membro mantém o comprimento original.':activeIK.config.label+' · '+(activeIK.config.kind==='arm'?'cotovelo':'joelho')+' acompanha o alvo.';
}
function sync(){
 const a=current();$('selectedName').textContent=a?a.label:'Selecione um jogador';$('targetName').textContent=activeIK?'IK · '+activeIK.config.label:mode==='bone'?(a&&bone>=0?a.bones[bone].name:'Clique numa articulação'): 'Transformação do jogador inteiro';
 ['duplicate','remove','focus','resetPose','baseline'].forEach(id=>$(id).disabled=!a);$('resetBone').disabled=!a||bone<0;
 $('resetBone').textContent=activeIK?'Repor membro':'Repor osso';for(const name of ['LeftHand','RightHand','LeftFoot','RightFoot'])$('ik'+name).disabled=!a;
 if(a){const angles=new THREE.Euler().setFromQuaternion(a.root.quaternion);for(const c of ['x','y','z']){if(document.activeElement!==$('p'+c))$('p'+c).value=a.root.position[c].toFixed(3);if(document.activeElement!==$('a'+c))$('a'+c).value=THREE.MathUtils.radToDeg(angles[c]).toFixed(1);}if(document.activeElement!==$('size'))$('size').value=(a.root.scale.x/.01).toFixed(2);}
 if(a&&bone>=0){const q=a.base[bone].quaternion.clone().invert().multiply(a.bones[bone].quaternion),e=new THREE.Euler().setFromQuaternion(q);for(const c of ['x','y','z']){if(document.activeElement!==$('r'+c))$('r'+c).value=THREE.MathUtils.radToDeg(e[c]);$('v'+c).textContent=THREE.MathUtils.radToDeg(e[c]).toFixed(1)+'°';}}
 $('undo').disabled=!history.undo.length;$('redo').disabled=!history.redo.length;
}
function chooseMode(next){mode=next;$('objectMode').classList.toggle('active',mode==='object');$('boneMode').classList.toggle('active',mode==='bone');if(mode==='bone'){$('skeleton').checked=true;if(bone<0&&current())bone=current().bones.findIndex(b=>b.name==='LeftArm');}attach();sync();}
function chooseOperation(next){operation=next;for(const [id,value] of [['move','translate'],['rotate','rotate'],['scale','scale']])$(id).classList.toggle('active',operation===value);attach();sync();}
function restore(data){
 const saved=validateScene(data,catalog());view.gizmo.detach();for(const a of actors)view.disposeActor(a);actors=[];view.setActors(actors);
 for(const state of saved.actors){const actor=create(state.playerId);actor.id=state.id;actor.label=state.label;const info=manifest.variants.find(v=>v.id===state.pose).players.find(p=>p.id===actor.playerId);setPose(actor,info,state.pose);
  actor.root.position.fromArray(state.position);actor.root.quaternion.fromArray(state.quaternion).normalize();actor.root.scale.fromArray(state.scale);
  state.bones.forEach((b,i)=>{actor.bones[i].position.fromArray(b.position);actor.bones[i].quaternion.fromArray(b.quaternion);actor.bones[i].scale.fromArray(b.scale);});actor.root.updateMatrixWorld(true);actor.skeleton.update();
 }views=saved.views;renderViews();if(saved.camera){view.camera.position.fromArray(saved.camera.position);view.orbit.target.fromArray(saved.camera.target);view.orbit.update();}if(typeof data.selection?.ik==='boolean')$('ikEnabled').checked=data.selection.ik;if(typeof data.selection?.keepRotation==='boolean')$('ikKeepRotation').checked=data.selection.keepRotation;const pick=actors.find(a=>a.id===data.selection?.actor)||actors[0],index=data.selection?.bone;select(pick?.id||null,Number.isInteger(index)&&index>=0&&index<(pick?.bones.length||0)?index:-1);if(data.selection)chooseMode(data.selection.mode==='bone'?'bone':'object');changed();
}
function formation(){for(const a of actors)view.disposeActor(a);actors=[];for(const info of manifest.variants[0].players)create(info.id);select(actors[0]?.id);view.frame();changed();}
function remove(){const a=current();if(!a)return;remember();view.disposeActor(a);actors=actors.filter(b=>b!==a);view.setActors(actors);select(actors[0]?.id||null);changed();}
function renderViews(){$('views').replaceChildren(new Option('Vistas salvas…',''));views.forEach((v,i)=>$('views').add(new Option(v.name,String(i))));}
function undo(){const state=history.back(snapshot());if(state){restore(state);toast('Alteração desfeita');}sync();}
function redo(){const state=history.forward(snapshot());if(state){restore(state);toast('Alteração refeita');}sync();}
$('add').onclick=()=>{try{remember();const a=current(),position=a?[a.root.position.x+.65,a.root.position.y,a.root.position.z]:[0,0,0];const added=create(Number($('library').value),position);select(added.id);changed();status('Jogador adicionado · clique e arraste os eixos para posicionar');}catch(e){toast(e.message);}};
$('duplicate').onclick=()=>{const a=current();if(!a)return;try{remember();const saved=snapshot(),data=structuredClone(saved.actors.find(v=>v.id===a.id));data.id=crypto.randomUUID();data.position[0]+=.6;data.label+=' · cópia';saved.actors.push(data);restore(saved);select(data.id);changed();}catch(e){toast(e.message);}};
$('remove').onclick=remove;$('new').onclick=()=>{remember();for(const a of actors)view.disposeActor(a);actors=[];view.setActors(actors);select(null);changed();};$('eleven').onclick=()=>{remember();formation();};
$('objectMode').onclick=()=>chooseMode('object');$('boneMode').onclick=()=>chooseMode('bone');$('move').onclick=()=>chooseOperation('translate');$('rotate').onclick=()=>chooseOperation('rotate');$('scale').onclick=()=>chooseOperation('scale');
$('space').onclick=()=>{space=space==='local'?'world':'local';$('space').textContent=space==='local'?'Local':'Global';attach();};
$('skeleton').onchange=attach;$('skeletonDetail').onchange=attach;$('armsOnly').onchange=renderBones;$('filter').oninput=renderBones;
$('bones').onchange=e=>{bone=Number(e.target.value);chooseMode('bone');chooseOperation($('ikEnabled').checked&&limbForBone(current(),bone)?'translate':'rotate');};
for(const name of ['LeftHand','RightHand','LeftFoot','RightFoot'])$('ik'+name).onclick=()=>{const a=current();if(!a)return;$('ikEnabled').checked=true;$('filter').value='';if(name.endsWith('Foot'))$('armsOnly').checked=false;select(a.id,a.bones.findIndex(b=>b.name===name));chooseMode('bone');chooseOperation('translate');status('IK · arraste o punho ou pé para posar o membro');};
$('ikEnabled').onchange=()=>{chooseOperation($('ikEnabled').checked&&limbForBone(current(),bone)?'translate':operation);};
$('ikKeepRotation').onchange=()=>{if(activeIK){remember();applyIK();changed();}};
$('ikBend').onpointerdown=()=>{if(activeIK)remember();};$('ikBend').onkeydown=e=>{if(activeIK&&!e.repeat&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key))remember();};$('ikBend').oninput=()=>{applyIK();changed();};
$('ikFlip').onclick=()=>{if(!activeIK)return;remember();const next=Number($('ikBend').value)+180;$('ikBend').value=next>180?next-360:next;applyIK();changed();};
for(const c of ['x','y','z']){
 $('p'+c).onchange=()=>{const a=current(),value=Number($('p'+c).value);if(!a||!Number.isFinite(value)||Math.abs(value)>1000)return;remember();a.root.position[c]=value;changed();attach();};
 $('a'+c).onchange=()=>{const a=current(),value=Number($('a'+c).value);if(!a||!Number.isFinite(value))return;remember();a.root.rotation[c]=THREE.MathUtils.degToRad(value);changed();attach();};
 $('r'+c).onpointerdown=()=>{if(current()&&bone>=0)remember();};$('r'+c).onkeydown=e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key)&&!e.repeat&&current()&&bone>=0)remember();};$('r'+c).oninput=()=>{const a=current();if(!a||bone<0)return;const e=new THREE.Euler(...['x','y','z'].map(axis=>THREE.MathUtils.degToRad(Number($('r'+axis).value))),'XYZ');a.bones[bone].quaternion.copy(a.base[bone].quaternion).multiply(new THREE.Quaternion().setFromEuler(e));if(activeIK){a.root.updateMatrixWorld(true);activeIK.startEnd.copy(a.bones[bone].quaternion);activeIK.endWorld.copy(a.bones[bone].getWorldQuaternion(new THREE.Quaternion()).normalize());}changed();};
}
$('size').onchange=()=>{const a=current(),value=Number($('size').value);if(!a||!Number.isFinite(value)||value<.05||value>5)return;remember();a.root.scale.setScalar(.01*value);changed();attach();};
$('baseline').onclick=()=>{const a=current();if(!a)return;remember();setPose(a,manifest.variants[0].players.find(p=>p.id===a.playerId));changed();attach();};
$('resetBone').onclick=()=>{const a=current();if(!a||bone<0)return;remember();const indices=activeIK?[activeIK.upper,activeIK.lower,activeIK.end].map(b=>a.bones.indexOf(b)):[bone];for(const i of indices){a.bones[i].position.copy(a.base[i].position);a.bones[i].quaternion.copy(a.base[i].quaternion);a.bones[i].scale.copy(a.base[i].scale);}changed();attach();};
$('resetPose').onclick=()=>{const a=current();if(!a)return;remember();const p=manifest.variants.find(v=>v.id===a.pose).players.find(p=>p.id===a.playerId);setPose(a,p,a.pose);changed();attach();};
$('grid').onchange=()=>view.grid.visible=$('grid').checked;$('shadows').onchange=()=>{view.renderer.shadowMap.enabled=$('shadows').checked;view.invalidate();};
for(const direction of ['front','side','top'])$(direction).onclick=()=>{view.frame(null,direction);changed();};$('frame').onclick=()=>{view.frame();changed();};$('focus').onclick=()=>{if(current())view.frame(current());changed();};
$('bookmark').onclick=()=>{if(views.length>=20){toast('Até 20 vistas por cena.');return;}remember();views.push({name:'Vista '+(views.length+1),position:view.camera.position.toArray(),target:view.orbit.target.toArray()});renderViews();changed();};
$('views').onchange=e=>{const v=views[Number(e.target.value)];if(e.target.value===''||!v)return;view.camera.position.fromArray(v.position);view.orbit.target.fromArray(v.target);view.orbit.update();};
$('undo').onclick=undo;$('redo').onclick=redo;
window.addEventListener('keydown',e=>{
 const focus=document.activeElement;if(loading||focus?.tagName==='TEXTAREA'||(focus?.tagName==='INPUT'&&focus.type!=='range'&&focus.type!=='checkbox'))return;
 if(e.ctrlKey||e.metaKey){if(e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo();}if(['x','y'].includes(e.key.toLowerCase())){e.preventDefault();redo();}return;}
 if(focus?.tagName==='SELECT')return;
 if(e.key.toLowerCase()==='w')chooseOperation('translate');if(e.key.toLowerCase()==='e')chooseOperation('rotate');if(e.key.toLowerCase()==='r')chooseOperation('scale');if(e.key.toLowerCase()==='f'&&current())view.frame(current());
});
view.gizmo.addEventListener('dragging-changed',e=>{view.orbit.enabled=!e.value;gesture=e.value;if(e.value)remember();else{const target=view.gizmo.object;if(target&&!activeIK)for(const axis of ['x','y','z'])target.scale[axis]=THREE.MathUtils.clamp(target.scale[axis],mode==='object'?.0005:.001,mode==='object'?.05:100);changed();attach(true);}});view.gizmo.addEventListener('objectChange',()=>{if(activeIK&&view.gizmo.object===ikTarget)applyIK();view.invalidate();sync();});
$('canvas').addEventListener('pointerdown',e=>pointerStart={x:e.clientX,y:e.clientY,axis:view.gizmo.axis,button:e.button});
$('canvas').addEventListener('pointerup',e=>{if(!pointerStart||gesture||pointerStart.axis||pointerStart.button!==0||Math.hypot(e.clientX-pointerStart.x,e.clientY-pointerStart.y)>4)return;const hit=view.pick(e.clientX,e.clientY);if(hit){select(hit.actor.id,hit.bone);if(hit.bone>=0){chooseMode('bone');if($('ikEnabled').checked&&limbForBone(current(),bone))chooseOperation('translate');}}});
function download(name,data,type){const link=document.createElement('a'),url=URL.createObjectURL(new Blob([data],{type}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
$('save').onclick=()=>{download('cena-fifa-friends.json',JSON.stringify(snapshot(),null,2),'application/json');dirty=false;toast('Cena exportada em JSON editável');};
$('load').onclick=()=>$('sceneFile').click();$('sceneFile').onchange=async e=>{try{if(e.target.files[0].size>20*1024*1024)throw Error('Arquivo de cena muito grande.');const data=JSON.parse(await e.target.files[0].text());remember();restore(data);toast('Cena carregada');}catch(error){toast(error.message);}};
$('recover').onclick=()=>{try{const data=JSON.parse(localStorage.getItem(draftKey));remember();restore(data);toast('Rascunho recuperado');}catch(error){toast(error.message);}};
$('capture').onclick=()=>{view.renderer.render(view.scene,view.camera);$('canvas').toBlob(blob=>download('cena-fifa-friends.png',blob,'image/png'));};
$('exportNative').onclick=async()=>{
 if(!actors.length){toast('Adicione ao menos um jogador.');return;}$('exportNative').disabled=true;$('exportStatus').textContent='Preparando malhas e texturas fora do jogo…';
 try{const response=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snapshot())});const job=await response.json();if(!response.ok)throw Error(job.error||'Falha ao exportar.');
  let completed=false;for(let poll=0;poll<450;poll++){await new Promise(r=>setTimeout(r,650));const response=await fetch('/api/export/'+job.id),result=await response.json();if(!response.ok)throw Error(result.error||'Não foi possível consultar a exportação.');$('exportStatus').textContent=result.message||'Preparando…';if(result.status==='error')throw Error(result.message);if(result.status==='ready'){const a=document.createElement('a');a.href=result.url;a.textContent='Baixar pacote RX3 · '+result.files+' arquivos';a.download='';$('exportStatus').replaceChildren(a);toast('Pacote gerado sem instalar nada no FIFA');completed=true;break;}}if(!completed)throw Error('A exportação excedeu o tempo esperado. Consulte a pasta exports.');
 }catch(error){$('exportStatus').textContent=error.message;}finally{$('exportNative').disabled=false;}
};
const imagePose=setupImagePose({button:$('imagePose'),getLibrary:()=>manifest?.variants[0].players||[],getSelected:current,onVisibility:visible=>view.setPaused(visible),onApply:async request=>{
 if(loading)throw Error('A biblioteca ainda está carregando.');
 if(request.mode==='new'&&request.people.length>MAX_ACTORS)throw Error('Limite de '+MAX_ACTORS+' jogadores.');
 if(request.mode==='selected'&&(!current()||request.people.length!==1))throw Error('Selecione um jogador e uma pessoa da imagem.');
 for(const entry of request.people)if(!templates.has(entry.playerId))throw Error('Modelo de jogador não encontrado.');
 const before=snapshot();let review=0,first=null;
 try{
  if(request.mode==='new'){
   view.gizmo.detach();activeIK=null;for(const actor of actors)view.disposeActor(actor);actors=[];view.setActors(actors);
   const positions=layoutPeople(request.people.map(p=>p.person));
   for(let i=0;i<request.people.length;i++){request.onProgress?.('Transferindo pose · '+(i+1)+' de '+request.people.length);await new Promise(resolve=>setTimeout(resolve,0));const entry=request.people[i],actor=create(entry.playerId,positions[i]);actor.label+=' · Pessoa '+(i+1);if(!first)first=actor;const result=retargetPose(actor,entry.person,request.settings);review+=result.body_points_to_review;}
  }else{first=current();review=retargetPose(first,request.people[0].person,request.settings).body_points_to_review;}
  history.push(before);select(first?.id||null);chooseMode('object');view.frame();changed();status('Poses importadas · '+request.people.length+' pessoa(s)'+(review?' · '+review+' pontos para revisar':'')+' · ajuste com os ossos ou IK');toast('Poses aplicadas. Ctrl+Z desfaz a importação inteira.');return {message:'Poses aplicadas'};
 }catch(error){restore(before);throw error;}
}});
try{
 manifest=await(await fetch('./assets/scene.json')).json();for(let i=0;i<manifest.variants[0].players.length;i++){const p=manifest.variants[0].players[i];$('loading').textContent='Biblioteca Flamengo · '+(i+1)+' de 11';const t=await parsePlayer('./assets/player-'+p.id+'.ff3d');t.textures.forEach(t=>t.anisotropy=4);templates.set(p.id,t);$('library').add(new Option(p.name+' · #'+p.number,String(p.id)));}
 formation();loading=false;history.clear();sync();document.querySelector('main').inert=false;document.querySelector('.header-tools').inert=false;$('loading').classList.add('hidden');status('Editor pronto · '+actors.length+' jogadores · clique para selecionar');try{$('recover').disabled=!localStorage.getItem(draftKey);}catch{}
 window.sceneEditor={snapshot,restore,validate:()=>validateScene(snapshot(),catalog()),get actorCount(){return actors.length;},get ready(){return !loading;}};
}catch(error){$('loading').textContent='Falha: '+error.message;console.error(error);}
