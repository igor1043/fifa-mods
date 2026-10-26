import * as THREE from 'three';
import {OrbitControls} from './vendor/three/examples/jsm/controls/OrbitControls.js';
import {BODY_EDGES,BODY_NAMES,validateCapture,moveCapturePoint} from './pose_capture.js';
import {History} from './scene_state.js';

const colors=['#69d6ce','#f7c76f','#91b6ff','#f39cb9','#b7e17b','#d4a7fa'];
const handEdges=[];for(const start of [91,112])for(const n of [1,5,9,13,17]){handEdges.push([start,start+n]);for(let j=0;j<3;j++)handEdges.push([start+n+j,start+n+j+1]);}
const allEdges=[...BODY_EDGES,...handEdges];
function download(name,value){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}

class SkeletonPreview{
 constructor(canvas){
  this.canvas=canvas;this.renderer=new THREE.WebGLRenderer({canvas,antialias:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0x172630);this.camera=new THREE.PerspectiveCamera(38,1,.01,100);this.camera.position.set(2,1.5,4);this.orbit=new OrbitControls(this.camera,canvas);this.orbit.target.set(0,.8,0);this.scene.add(new THREE.GridHelper(8,16,0x628495,0x354d5b));this.group=new THREE.Group();this.scene.add(this.group);
 }
 show(person,settings){
  for(const child of [...this.group.children]){this.group.remove(child);child.geometry.dispose();child.material.dispose();}
  if(person){
   const points=person.keypoints3d.map(p=>new THREE.Vector3(p[0]*(settings.mirror?-1:1),p[1],p[2]*settings.depth));const floor=Math.min(...points.slice(0,23).map(p=>p.y));points.forEach(p=>p.y-=floor);
   const vertices=[];for(const [a,b] of allEdges)if(person.keypoints3d[a][3]>=settings.confidence&&person.keypoints3d[b][3]>=settings.confidence)vertices.push(...points[a].toArray(),...points[b].toArray());
   const lines=new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(vertices,3)),new THREE.LineBasicMaterial({color:0x77e3cc}));this.group.add(lines);
   const data=[],tints=[];points.forEach((p,i)=>{data.push(...p.toArray());const c=new THREE.Color(person.keypoints3d[i][3]>=settings.confidence?0xa5f0dd:0xefae68);tints.push(c.r,c.g,c.b);});
   this.group.add(new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(data,3)).setAttribute('color',new THREE.Float32BufferAttribute(tints,3)),new THREE.PointsMaterial({size:.025,vertexColors:true})));
  }this.draw();
 }
 draw(){const rect=this.canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;this.renderer.setSize(rect.width,rect.height,false);this.camera.aspect=rect.width/rect.height;this.camera.updateProjectionMatrix();this.orbit.update();this.renderer.render(this.scene,this.camera);}
 active(value){this.renderer.setAnimationLoop(value?()=>this.draw():null);}
}

export function setupImagePose({button,getLibrary,getSelected,onApply,onVisibility}){
 const dialog=document.createElement('dialog');dialog.className='pose-dialog';dialog.innerHTML=`
 <div class="pose-shell"><div class="pose-title"><div><h2>Capturar poses de uma imagem</h2><p>IA local · corpo, mãos e pés · esqueleto editável</p></div><button data-p="close" aria-label="Fechar captura">Fechar</button></div>
 <div class="pose-inputs"><button data-p="image">Escolher imagem</button><button data-p="load">Importar mapa</button><button data-p="save" disabled>Exportar mapa</button><label>Máximo de pessoas <input data-p="maximum" type="number" min="1" max="48" value="16"></label><button data-p="detect" class="pose-primary" disabled>Analisar imagem</button></div>
 <div class="pose-message" data-p="message">Escolha uma foto. O arquivo será processado neste computador.</div>
 <div class="pose-workspace"><div class="pose-view"><div class="pose-view-tabs"><button data-p="imageTab" class="active">Imagem e pontos</button><button data-p="threeTab">Esqueleto 3D</button><label><input data-p="detail" type="checkbox"> Mãos e rosto</label></div>
 <div class="pose-canvas-wrap"><canvas data-p="canvas" width="1000" height="650"></canvas><canvas data-p="preview3d" class="pose-3d" hidden></canvas><span class="pose-placeholder" data-p="placeholder">Importe uma imagem ou um mapa de poses</span></div>
 <div class="pose-edit-tools"><button data-p="crop" disabled>Adicionar por recorte</button><button data-p="analyzeCrop" disabled>Analisar recorte</button><button data-p="undo" disabled>↶ Ponto</button><button data-p="redo" disabled>↷ Ponto</button><span data-p="pointHint">Clique numa pessoa; arraste as articulações para corrigir.</span></div></div>
 <aside class="pose-people"><h3>Pessoas detectadas</h3><div data-p="people" class="pose-person-list"></div><p class="hint" data-p="selection">Nenhuma captura carregada.</p>
 <h3>Ajustar transferência</h3><label>Pontos confiáveis <output data-p="thresholdText">0,30</output><input data-p="threshold" type="range" min="0.05" max="0.9" step="0.05" value="0.3"></label>
 <label>Profundidade estimada <output data-p="depthText">100%</output><input data-p="depth" type="range" min="0" max="1.5" step="0.05" value="1"></label>
 <label><input data-p="mirror" type="checkbox"> Espelhar pose</label><label><input data-p="fingers" type="checkbox" checked> Transferir dedos visíveis</label><label><input data-p="ground" type="checkbox" checked> Apoiar calçados no piso</label>
 <p class="hint">Verde: ponto confiável. Laranja: revisar. Uma foto só estima a profundidade e partes escondidas; os ajustes continuam no editor com IK.</p></aside></div>
 <div class="pose-footer"><span data-p="model">Verificando IA local…</span><div><button data-p="applyOne" disabled>Aplicar ao jogador selecionado</button><button data-p="applyScene" class="pose-primary" disabled>Criar cena com as poses</button></div></div>
 <input data-p="imageFile" type="file" accept="image/png,image/jpeg,image/webp" hidden><input data-p="mapFile" type="file" accept="application/json,.json" hidden></div>`;
 document.body.appendChild(dialog);const $=name=>dialog.querySelector('[data-p="'+name+'"]'),canvas=$('canvas'),ctx=canvas.getContext('2d');
 let capture=null,image=null,imageData=null,imageName='',selected=null,original=null,busy=false,applying=false,drag=null,cropMode=false,cropBox=null,preview=null,view3d=false;const chosen=new Map(),models=new Map(),history=new History(25);
 const settings=()=>({confidence:Number($('threshold').value),depth:Number($('depth').value),mirror:$('mirror').checked,fingers:$('fingers').checked,ground:$('ground').checked});
 const person=()=>capture?.people.find(p=>p.id===selected),included=()=>capture?capture.people.filter(p=>chosen.get(p.id)):[];
 const message=(text,error=false)=>{$('message').textContent=text;$('message').classList.toggle('pose-error',error);};
 function remember(){if(capture)history.push(capture);}
 function buttons(){const count=included().length;$('close').disabled=applying;$('detect').disabled=busy||!imageData;$('image').disabled=busy;$('load').disabled=busy;$('crop').disabled=busy||!imageData;$('analyzeCrop').disabled=busy||!cropBox;$('save').disabled=!capture||!count;$('applyScene').disabled=busy||!count;$('applyOne').disabled=busy||count!==1||!getSelected();$('undo').disabled=!history.undo.length;$('redo').disabled=!history.redo.length;$('applyScene').textContent=count?'Criar cena com '+count+(count===1?' pessoa':' pessoas'):'Criar cena com as poses';}
 function renderPeople(){
  $('people').replaceChildren();const library=getLibrary();for(const [i,p] of (capture?.people||[]).entries()){
   if(!chosen.has(p.id))chosen.set(p.id,true);if(!models.has(p.id))models.set(p.id,library.some(a=>a.id===p.suggestedPlayerId)?p.suggestedPlayerId:library[i%library.length]?.id);
   const row=document.createElement('div');row.className='pose-person'+(p.id===selected?' selected':'');
   const header=document.createElement('div');header.className='pose-person-heading';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=chosen.get(p.id);checkbox.ariaLabel='Incluir pessoa '+(i+1);checkbox.onchange=()=>{chosen.set(p.id,checkbox.checked);renderPeople();draw();};
   const pick=document.createElement('button');pick.textContent='Pessoa '+(i+1)+' · '+Math.round(p.confidence*100)+'%';pick.style.color=colors[i%colors.length];pick.onclick=()=>{selected=p.id;renderPeople();draw();};header.append(checkbox,pick);row.append(header);
   const select=document.createElement('select');select.ariaLabel='Modelo da pessoa '+(i+1);for(const actor of library)select.add(new Option(actor.name,String(actor.id)));select.value=String(models.get(p.id));select.onchange=()=>models.set(p.id,Number(select.value));row.append(select);$('people').append(row);
  }$('selection').textContent=capture?included().length+' de '+capture.people.length+' pessoas marcadas. Escolha o modelo de cada uma.':'Nenhuma captura carregada.';buttons();
 }
 function draw(){
  ctx.fillStyle='#15242e';ctx.fillRect(0,0,canvas.width,canvas.height);if(image)ctx.drawImage(image,0,0,canvas.width,canvas.height);
  $('placeholder').hidden=!!image||!!capture;
  const factor=canvas.width/Math.max(500,canvas.getBoundingClientRect().width),threshold=settings().confidence;
  for(const [i,p] of (capture?.people||[]).entries()){
   if(!chosen.get(p.id))continue;const active=p.id===selected,color=colors[i%colors.length];ctx.globalAlpha=active?1:.52;ctx.lineWidth=(active?2.6:1.6)*factor;ctx.strokeStyle=color;const [x,y,right,bottom]=p.bbox;ctx.strokeRect(x,y,right-x,bottom-y);ctx.fillStyle=color;ctx.font='bold '+Math.round(14*factor)+'px Segoe UI';ctx.fillText('Pessoa '+(i+1),x+5*factor,Math.max(18*factor,y-5*factor));
   for(const [a,b] of ($('detail').checked?allEdges:BODY_EDGES)){const from=p.keypoints2d[a],to=p.keypoints2d[b];if(from[2]<.08||to[2]<.08)continue;ctx.strokeStyle=Math.min(from[2],to[2])<threshold?'#f4ad68':color;ctx.beginPath();ctx.moveTo(from[0],from[1]);ctx.lineTo(to[0],to[1]);ctx.stroke();}
   const maximum=$('detail').checked?133:23;for(let j=0;j<maximum;j++){const point=p.keypoints2d[j];if(point[2]<.08)continue;ctx.beginPath();ctx.fillStyle=point[2]<threshold?'#f4ad68':active?'#d5fff4':color;ctx.arc(point[0],point[1],(active?4:2.5)*factor,0,Math.PI*2);ctx.fill();}
  }ctx.globalAlpha=1;
  if(cropBox){ctx.strokeStyle='#dfb3ff';ctx.setLineDash([8*factor,5*factor]);ctx.lineWidth=2*factor;ctx.strokeRect(cropBox[0],cropBox[1],cropBox[2]-cropBox[0],cropBox[3]-cropBox[1]);ctx.setLineDash([]);}
  if(view3d&&preview)preview.show(person(),settings());buttons();
 }
 function setCapture(data,{append=false}={}){
  const valid=validateCapture(data);
  if(append&&capture){if(capture.people.length+valid.people.length>48)throw Error('Limite de 48 pessoas por captura.');remember();for(const p of valid.people){p.id='manual-'+crypto.randomUUID();capture.people.push(p);selected=p.id;}}
  else{capture=valid;original=structuredClone(valid);history.clear();chosen.clear();models.clear();selected=capture.people[0]?.id||null;}
  if(valid.retarget&&!append){$('threshold').value=String(valid.retarget.confidence);$('depth').value=String(valid.retarget.depth);for(const name of ['mirror','fingers','ground'])$(name).checked=valid.retarget[name];$('thresholdText').textContent=valid.retarget.confidence.toFixed(2).replace('.',',');$('depthText').textContent=Math.round(valid.retarget.depth*100)+'%';}
  canvas.width=capture.image.width;canvas.height=capture.image.height;renderPeople();draw();
 }
 async function normalizedFile(file){
  if(!file||!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Escolha PNG, JPG ou WebP.');if(file.size>15*1024*1024)throw Error('Use uma imagem de até 15 MB.');
  const bitmap=await createImageBitmap(file,{imageOrientation:'from-image'});if(bitmap.width*bitmap.height>24_000_000){bitmap.close();throw Error('Use uma imagem de até 24 megapixels.');}
  const factor=Math.min(1,3072/Math.max(bitmap.width,bitmap.height)),buffer=document.createElement('canvas');buffer.width=Math.round(bitmap.width*factor);buffer.height=Math.round(bitmap.height*factor);const graphics=buffer.getContext('2d');graphics.fillStyle='#ffffff';graphics.fillRect(0,0,buffer.width,buffer.height);graphics.drawImage(bitmap,0,0,buffer.width,buffer.height);bitmap.close();return buffer.toDataURL('image/jpeg',.96);
 }
 async function loadImage(url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error('A imagem de referência não está disponível. O mapa continua utilizável.'));img.src=url;});}
 async function detect(regions=[]){
  if(busy||!imageData)return;busy=true;buttons();message('Preparando análise local…');const append=regions.length>0;
  try{
   const response=await fetch('/api/pose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:imageData,name:imageName,max_people:append?1:Number($('maximum').value),confidence:.35,regions})});const job=await response.json();if(!response.ok)throw Error(job.error||'Não foi possível iniciar a IA local.');
   let complete=false;for(let poll=0;poll<600;poll++){
    await new Promise(resolve=>setTimeout(resolve,450));const response=await fetch('/api/pose/'+job.id),result=await response.json();if(!response.ok)throw Error(result.error||'Análise não encontrada.');message(result.message||'Analisando…');
    if(result.status==='error')throw Error(result.message);
    if(result.status==='ready'){
     setCapture(result.capture,{append});cropBox=null;cropMode=false;$('crop').classList.remove('active');$('model').textContent=result.capture.model+' · '+(result.capture.device==='DirectML'?'GPU local':'CPU local');message(result.capture.people.length?(append?'Pessoa adicionada. Revise os pontos e o modelo.':result.capture.people.length+' pessoas detectadas. Revise antes de criar a cena.'):'Nenhuma pessoa encontrada. Use Adicionar por recorte para indicar a região.');complete=true;break;
    }
   }if(!complete)throw Error('A análise excedeu o tempo esperado. Tente um recorte menor.');
  }catch(error){message(error.message,true);}finally{busy=false;buttons();draw();}
 }
 $('image').onclick=()=>$('imageFile').click();$('imageFile').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  try{imageData=await normalizedFile(file);image=await loadImage(imageData);imageName=file.name;canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;capture=original=null;history.clear();chosen.clear();models.clear();selected=null;cropBox=null;renderPeople();draw();message('Imagem pronta. Clique em Analisar imagem.');setTab(false);}catch(error){message(error.message,true);}event.target.value='';
 };
 $('detect').onclick=()=>detect();$('crop').onclick=()=>{cropMode=!cropMode;$('crop').classList.toggle('active',cropMode);setTab(false);message(cropMode?'Arraste um retângulo ao redor da pessoa que quer adicionar.':'Clique e arraste as articulações para corrigir.');};$('analyzeCrop').onclick=()=>{if(cropBox)detect([cropBox]);};
 $('load').onclick=()=>$('mapFile').click();$('mapFile').onchange=async event=>{
  try{const file=event.target.files[0];if(!file)return;if(file.size>10*1024*1024)throw Error('Mapa muito grande.');const valid=validateCapture(JSON.parse(await file.text()));image=null;imageData=null;setCapture(valid);if(valid.image.url){try{image=await loadImage(valid.image.url);const buffer=document.createElement('canvas');buffer.width=image.naturalWidth;buffer.height=image.naturalHeight;buffer.getContext('2d').drawImage(image,0,0);imageData=buffer.toDataURL('image/jpeg',.96);}catch{}}draw();message('Mapa importado. Os pontos e as poses podem ser ajustados.');}catch(error){message(error.message,true);}event.target.value='';
 };
 $('save').onclick=()=>{try{const data=validateCapture({...capture,people:included().map(p=>({...p,suggestedPlayerId:models.get(p.id)})),retarget:settings()});download('mapa-poses-fifa-friends.json',data);message('Mapa exportado com as pessoas, modelos e correções.');}catch(error){message(error.message,true);}};
 function undo(){const previous=history.back(capture);if(previous){capture=previous;renderPeople();draw();}}
 function redo(){const next=history.forward(capture);if(next){capture=next;renderPeople();draw();}}
 $('undo').onclick=undo;$('redo').onclick=redo;
 const pointer=event=>{const r=canvas.getBoundingClientRect();return [THREE.MathUtils.clamp((event.clientX-r.left)/r.width*canvas.width,0,canvas.width),THREE.MathUtils.clamp((event.clientY-r.top)/r.height*canvas.height,0,canvas.height)];};
 canvas.onpointerdown=event=>{
  if(busy||event.button!==0)return;const [x,y]=pointer(event);canvas.setPointerCapture(event.pointerId);
  if(cropMode){drag={crop:true,start:[x,y]};cropBox=[x,y,x,y];return;}
  const active=person(),radius=12*canvas.width/canvas.getBoundingClientRect().width;if(active){let hit=-1,best=radius;active.keypoints2d.slice(0,$('detail').checked?133:23).forEach((p,i)=>{const distance=Math.hypot(p[0]-x,p[1]-y);if(distance<best){best=distance;hit=i;}});if(hit>=0){remember();drag={id:active.id,index:hit};$('pointHint').textContent=BODY_NAMES[hit]||'Ponto '+hit;return;}}
  const hit=capture?.people.filter(p=>chosen.get(p.id)&&x>=p.bbox[0]&&x<=p.bbox[2]&&y>=p.bbox[1]&&y<=p.bbox[3]).sort((a,b)=>(a.bbox[2]-a.bbox[0])*(a.bbox[3]-a.bbox[1])-(b.bbox[2]-b.bbox[0])*(b.bbox[3]-b.bbox[1]))[0];if(hit){selected=hit.id;renderPeople();draw();}
 };
 canvas.onpointermove=event=>{if(!drag)return;const [x,y]=pointer(event);if(drag.crop){const [a,b]=drag.start;cropBox=[Math.min(a,x),Math.min(b,y),Math.max(a,x),Math.max(b,y)];}else{const p=capture.people.find(p=>p.id===drag.id);moveCapturePoint(p,drag.index,x,y);}draw();};
 canvas.onpointerup=()=>{drag=null;if(cropBox&&(cropBox[2]-cropBox[0]<12||cropBox[3]-cropBox[1]<24))cropBox=null;draw();};canvas.onpointercancel=()=>{drag=null;};
 function setTab(three){view3d=three;canvas.hidden=three;$('preview3d').hidden=!three;$('imageTab').classList.toggle('active',!three);$('threeTab').classList.toggle('active',three);if(three&&!preview)preview=new SkeletonPreview($('preview3d'));preview?.active(three&&dialog.open);draw();}
 $('imageTab').onclick=()=>setTab(false);$('threeTab').onclick=()=>setTab(true);
 for(const name of ['threshold','depth','mirror','detail','fingers','ground'])$(name).oninput=()=>{$('thresholdText').textContent=Number($('threshold').value).toFixed(2).replace('.',',');$('depthText').textContent=Math.round(Number($('depth').value)*100)+'%';draw();};
 async function apply(mode){
  try{const people=included();if(!people.length)throw Error('Marque uma pessoa.');if(mode==='selected'&&people.length!==1)throw Error('Marque apenas uma pessoa para aplicar ao selecionado.');
   busy=applying=true;buttons();message('Transferindo poses para os esqueletos do FIFA…');await new Promise(resolve=>setTimeout(resolve,30));const data=validateCapture({...capture,people});const result=await onApply({capture:data,people:data.people.map(p=>({person:p,playerId:models.get(p.id)})),mode,settings:settings(),onProgress:text=>message(text)});dialog.close();if(result?.message)message(result.message);
  }catch(error){message(error.message,true);}finally{busy=applying=false;buttons();}
 }
 $('applyScene').onclick=()=>apply('new');$('applyOne').onclick=()=>apply('selected');$('close').onclick=()=>{if(!applying)dialog.close();};dialog.addEventListener('cancel',event=>{if(applying)event.preventDefault();});dialog.addEventListener('close',()=>{preview?.active(false);onVisibility?.(false);});
 dialog.addEventListener('keydown',event=>{event.stopPropagation();const focus=document.activeElement,typing=focus?.tagName==='TEXTAREA'||(focus?.tagName==='INPUT'&&!['range','checkbox'].includes(focus.type));if((event.ctrlKey||event.metaKey)&&!typing){if(event.key.toLowerCase()==='z'){event.preventDefault();event.shiftKey?redo():undo();}if(['x','y'].includes(event.key.toLowerCase())){event.preventDefault();redo();}}});
 button.onclick=async()=>{dialog.showModal();onVisibility?.(true);buttons();draw();preview?.active(view3d);try{const info=await(await fetch('/api/pose')).json();$('model').textContent=info.ready?'RTMW3D-X · 133 pontos · instalado localmente':'Modelos locais não instalados';}catch{$('model').textContent='Servidor local indisponível';}};
 return {open:()=>button.click(),get capture(){return capture;}};
}
