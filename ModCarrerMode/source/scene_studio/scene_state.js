export const MAX_ACTORS=48;
const vector=(v,n,label,limit=10000)=>{
 if(!Array.isArray(v)||v.length!==n||v.some(x=>typeof x!=='number'||!Number.isFinite(x)||Math.abs(x)>limit))throw Error(label+' inválido.');
 return [...v];
};
export function validateScene(data,catalog){
 if(!data||data.schema!==2||data.type!=='fifa16-offline-scene')throw Error('Formato de cena incompatível.');
 if(!Array.isArray(data.actors)||data.actors.length>MAX_ACTORS)throw Error('Limite de '+MAX_ACTORS+' jogadores por cena.');
 const ids=new Set();
 const actors=data.actors.map(a=>{
  const template=catalog.get(a.playerId);
  if(!template)throw Error('Jogador não disponível nesta biblioteca: '+a.playerId);
  if(typeof a.id!=='string'||!a.id||a.id.length>100||ids.has(a.id))throw Error('Identificador de jogador repetido ou inválido.');ids.add(a.id);
  if(!Array.isArray(a.bones)||a.bones.length!==template.length)throw Error('Esqueleto incompatível.');
  const bones=a.bones.map((b,i)=>{
   if(b.name!==template[i])throw Error('Ordem dos ossos incompatível.');
   const quaternion=vector(b.quaternion,4,'Rotação',2),length=Math.hypot(...quaternion);
   if(length<.5||length>1.5)throw Error('Rotação degenerada.');
   const scale=vector(b.scale,3,'Escala');if(scale.some(x=>x<=0||x>100))throw Error('Escala do osso fora do limite.');
   return {name:b.name,position:vector(b.position,3,'Posição do osso'),quaternion:quaternion.map(x=>x/length),scale};
  });
  const scale=vector(a.scale,3,'Escala do jogador');if(scale.some(x=>x<=0||x>10))throw Error('Escala do jogador fora do limite.');
  const quaternion=vector(a.quaternion,4,'Giro do jogador',2),length=Math.hypot(...quaternion);if(length<.5||length>1.5)throw Error('Giro do jogador degenerado.');
  return {id:a.id,playerId:a.playerId,label:String(a.label||'Jogador').slice(0,100),pose:a.pose==='candidate'?'candidate':'baseline',
   position:vector(a.position,3,'Posição do jogador',1000),quaternion:quaternion.map(x=>x/length),scale,bones};
 });
 const views=(Array.isArray(data.views)?data.views:[]).slice(0,20).map(v=>({name:String(v.name||'Vista').slice(0,50),position:vector(v.position,3,'Câmera',1000),target:vector(v.target,3,'Alvo da câmera',1000)}));
 return {schema:2,type:'fifa16-offline-scene',actors,views,camera:data.camera?{position:vector(data.camera.position,3,'Câmera',1000),target:vector(data.camera.target,3,'Alvo da câmera',1000)}:null};
}
export class History{
 constructor(limit=25){this.limit=limit;this.undo=[];this.redo=[];}
 push(state){this.undo.push(structuredClone(state));if(this.undo.length>this.limit)this.undo.shift();this.redo=[];}
 back(current){if(!this.undo.length)return null;this.redo.push(structuredClone(current));return this.undo.pop();}
 forward(current){if(!this.redo.length)return null;this.undo.push(structuredClone(current));return this.redo.pop();}
 clear(){this.undo=[];this.redo=[];}
}
