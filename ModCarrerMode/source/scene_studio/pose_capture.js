// Capture interchange is independent of FIFA rigs and of the inference backend.
export const BODY_EDGES=[[5,6],[5,7],[7,9],[6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16],[0,1],[0,2],[1,3],[2,4],[15,17],[17,18],[15,19],[16,20],[20,21],[16,22]];
export const BODY_NAMES=['Nariz','Olho E','Olho D','Orelha E','Orelha D','Ombro E','Ombro D','Cotovelo E','Cotovelo D','Punho E','Punho D','Quadril E','Quadril D','Joelho E','Joelho D','Tornozelo E','Tornozelo D','Dedão E','Dedos E','Calcanhar E','Dedão D','Dedos D','Calcanhar D'];
const array=(value,count,limit,label)=>{
 if(!Array.isArray(value)||value.length!==count||value.some(n=>typeof n!=='number'||!Number.isFinite(n)||Math.abs(n)>limit))throw Error(label+' inválido.');return value.map(n=>n===0?0:n);
};
export function validateCapture(data){
 if(!data||data.schema!==1||data.type!=='fifa-friends-pose-capture'||!data.image||!Number.isInteger(data.image.width)||!Number.isInteger(data.image.height)||data.image.width<1||data.image.height<1||data.image.width>10000||data.image.height>10000)throw Error('Captura de poses incompatível.');
 if(!Array.isArray(data.people)||data.people.length>48)throw Error('A captura aceita até 48 pessoas.');
 const ids=new Set(),people=data.people.map((person,index)=>{
  if(typeof person.id!=='string'||!person.id||person.id.length>80||ids.has(person.id))throw Error('Identificação de pessoa inválida.');ids.add(person.id);
  const bbox=array(person.bbox,4,20000,'Recorte');if(bbox[2]<=bbox[0]||bbox[3]<=bbox[1])throw Error('Recorte vazio.');
  if(!Array.isArray(person.keypoints2d)||person.keypoints2d.length!==133||!Array.isArray(person.keypoints3d)||person.keypoints3d.length!==133)throw Error('A captura deve ter os 133 pontos COCO-WholeBody.');
  const read=(p,n,limit)=>{const out=array(p,n,limit,'Articulação');if(out[n-1]<0||out[n-1]>1)throw Error('Confiança da articulação inválida.');return out;};
  const scale=person.meters_per_pixel;if(typeof scale!=='number'||!Number.isFinite(scale)||scale<=0||scale>1)throw Error('Escala da imagem inválida.');
  return {id:person.id,bbox,confidence:Number.isFinite(person.confidence)?Math.min(1,Math.max(0,person.confidence)):0,keypoints2d:person.keypoints2d.map(p=>read(p,3,50000)),keypoints3d:person.keypoints3d.map(p=>read(p,4,100)),meters_per_pixel:scale,...(Number.isInteger(person.suggestedPlayerId)&&person.suggestedPlayerId>0&&person.suggestedPlayerId<=524287?{suggestedPlayerId:person.suggestedPlayerId}:{})};
 });
 let retarget;
 if(data.retarget){const value=data.retarget;if(typeof value.confidence!=='number'||!Number.isFinite(value.confidence)||value.confidence<0||value.confidence>1||typeof value.depth!=='number'||!Number.isFinite(value.depth)||value.depth<0||value.depth>2)throw Error('Configuração da transferência inválida.');retarget={confidence:value.confidence,depth:value.depth,mirror:!!value.mirror,fingers:!!value.fingers,ground:!!value.ground};}
 return {schema:1,type:'fifa-friends-pose-capture',image:{width:data.image.width,height:data.image.height,name:String(data.image.name||'Imagem').slice(0,120),...(typeof data.image.sha256==='string'?{sha256:data.image.sha256.slice(0,64)}:{}),...(typeof data.image.url==='string'&&/^\/imports\/[a-f0-9]{32}\/input\.png$/.test(data.image.url)?{url:data.image.url}:{})},model:String(data.model||'Captura importada').slice(0,150),device:String(data.device||'local').slice(0,40),people,...(retarget?{retarget}:{})};
}
export function moveCapturePoint(person,index,x,y){
 if(!Number.isInteger(index)||index<0||index>=133||![x,y].every(Number.isFinite))throw Error('Ponto inválido.');
 const previous=person.keypoints2d[index],p=person.keypoints3d[index],factor=person.meters_per_pixel;
 p[0]+=(x-previous[0])*factor;p[1]-=(y-previous[1])*factor;p[3]=1;previous[0]=x;previous[1]=y;previous[2]=1;
}
export function layoutPeople(people){
 if(!people.length)return [];
 const sizes=people.map(p=>p.bbox[3]-p.bbox[1]).sort((a,b)=>a-b),scale=1.8/Math.max(64,sizes[Math.floor(sizes.length/2)]),centers=people.map(p=>(p.keypoints2d[11][0]+p.keypoints2d[12][0])/2),middle=(Math.min(...centers)+Math.max(...centers))/2;
 const floors=people.map(p=>(p.keypoints2d[15][1]+p.keypoints2d[16][1])/2),floorMiddle=(Math.min(...floors)+Math.max(...floors))/2;
 return people.map((p,i)=>[(centers[i]-middle)*scale*1.2,0,(floors[i]-floorMiddle)*scale*1.4]);
}
