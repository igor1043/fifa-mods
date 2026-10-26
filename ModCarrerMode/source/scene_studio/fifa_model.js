import * as THREE from "three";
export async function parsePlayer(url){
  const response=await fetch(url);if(!response.ok)throw new Error("Modelo FIFA não encontrado: "+url);const data=await response.arrayBuffer(),view=new DataView(data);let offset=0;
  const bytes=n=>{if(n<0||offset+n>data.byteLength)throw new Error("Arquivo FF3D incompleto.");const b=new Uint8Array(data,offset,n);offset+=n;return b;};
  const u32=()=>{const x=view.getUint32(offset,true);offset+=4;return x;},i32=()=>{const x=view.getInt32(offset,true);offset+=4;return x;},f32=()=>{const x=view.getFloat32(offset,true);offset+=4;return x;};
  const str=()=>{const n=u32();if(n>4096)throw new Error("Nome FF3D inválido.");return new TextDecoder().decode(bytes(n));};
  const magic=new TextDecoder().decode(bytes(8));if(magic!=="FF3D0002"&&magic!=="FF3D0003")throw new Error("Formato de jogador FF3D não reconhecido.");
  const partCount=u32(),textureCount=u32(),boneCount=u32(),playerId=u32(),height=u32(),playerName=str();if(!partCount||partCount>256||!boneCount||boneCount>1024||textureCount>512)throw new Error("Dimensões inválidas no jogador FIFA.");
  const boneData=[];for(let i=0;i<boneCount;i++){const name=str(),pr=u32(),m=[];for(let k=0;k<16;k++)m.push(f32());const inverse=new THREE.Matrix4().fromArray(m);boneData.push({name,parent:pr===0xffffffff?-1:pr,inverse,restWorld:inverse.clone().invert()});}
  const parts=[];
  for(let p=0;p<partCount;p++){
    const name=str(),asset=str(),texture=i32(),skinned=!!u32(),blend=!!u32(),alpha=f32(),hairCoeff=magic==="FF3D0003"?i32():-1,color=[f32(),f32(),f32()],tint=[f32(),f32(),f32()],vertexCount=u32(),indexCount=u32();
    if(vertexCount>5000000||indexCount>15000000||indexCount%3)throw new Error("Malha inválida: "+name);
    const positions=new Float32Array(vertexCount*3),normals=new Float32Array(vertexCount*3),uvs=new Float32Array(vertexCount*2),si=new Uint16Array(vertexCount*4),sw=new Float32Array(vertexCount*4),si2=new Uint16Array(vertexCount*4),sw2=new Float32Array(vertexCount*4);
    for(let v=0;v<vertexCount;v++){
      const at=v*3,uv=v*2,px=f32(),py=f32(),pz=f32(),nx=f32(),ny=f32(),nz=f32(),u=f32(),vv=f32(),j=[],w=[];
      for(let k=0;k<8;k++){j.push(view.getUint16(offset,true));offset+=2;}for(let k=0;k<8;k++)w.push(view.getUint8(offset++));
      positions.set([px,py,pz],at);normals.set([nx,ny,nz],at);uvs.set([u,vv],uv);
      if(skinned){let sum=w.reduce((a,b)=>a+b,0);if(!sum){w[0]=1;j[0]=0;sum=1;}for(let k=0;k<8;k++){if(w[k]&&j[k]>=boneCount)throw new Error("Índice de osso inválido em "+name);const n=v*4+k%4;(k<4?si:si2)[n]=w[k]?j[k]:0;(k<4?sw:sw2)[n]=w[k]/sum;}}
    }
    const indices=new Uint32Array(indexCount);for(let k=0;k<indexCount;k++){indices[k]=u32();if(indices[k]>=vertexCount)throw new Error("Índice inválido em "+name);}
    const geometry=new THREE.BufferGeometry();geometry.setAttribute("position",new THREE.BufferAttribute(positions,3));geometry.setAttribute("normal",new THREE.BufferAttribute(normals,3));geometry.setAttribute("uv",new THREE.BufferAttribute(uvs,2));geometry.setIndex(new THREE.BufferAttribute(indices,1));
    if(skinned){geometry.setAttribute("skinIndex",new THREE.BufferAttribute(si,4));geometry.setAttribute("skinWeight",new THREE.BufferAttribute(sw,4));geometry.setAttribute("skinIndex2",new THREE.BufferAttribute(si2,4));geometry.setAttribute("skinWeight2",new THREE.BufferAttribute(sw2,4));}
    parts.push({name,asset,texture,skinned,blend,alpha,hairCoeff,color,tint,geometry});
  }
  const textures=[];for(let i=0;i<textureCount;i++){const w=u32(),h=u32(),fmt=u32(),size=u32();if(!w||!h||w>4096||h>4096||size>64*1024*1024)throw new Error("Textura FIFA inválida.");textures.push(decodeTexture(w,h,fmt,bytes(size)));}
  if(offset!==data.byteLength)throw new Error("O arquivo FF3D tem dados extras fora do formato.");
  for(const part of parts){
    const map=part.texture>=0?textures[part.texture]||null:null,hair=part.asset.toLowerCase().includes("/hair/");
    const material=new THREE.MeshStandardMaterial({color:new THREE.Color(...(map?part.tint:part.color)),map,roughness:1,metalness:0,side:THREE.DoubleSide,transparent:part.blend,alphaTest:hair ? .12 : (part.blend ? .025 : .35),opacity:hair?part.alpha:1,toneMapped:false});
    if(hair){material.transparent=false;material.alphaTest=.55;material.opacity=1;}
    if(part.skinned)material.onBeforeCompile=shader=>{
      shader.vertexShader=shader.vertexShader.replace("#include <skinning_pars_vertex>","#include <skinning_pars_vertex>\nattribute vec4 skinIndex2;\nattribute vec4 skinWeight2;");
      const extra="skinWeight2.x * getBoneMatrix(skinIndex2.x) + skinWeight2.y * getBoneMatrix(skinIndex2.y) + skinWeight2.z * getBoneMatrix(skinIndex2.z) + skinWeight2.w * getBoneMatrix(skinIndex2.w)";
      shader.vertexShader=shader.vertexShader.replace("#include <skinnormal_vertex>",THREE.ShaderChunk.skinnormal_vertex.replace("skinMatrix = bindMatrixInverse","skinMatrix += "+extra+";\n skinMatrix = bindMatrixInverse"));
      shader.vertexShader=shader.vertexShader.replace("#include <skinning_vertex>",THREE.ShaderChunk.skinning_vertex.replace("transformed =","skinned += ("+extra+") * skinVertex;\n transformed ="));
    };
    if(part.skinned)material.customProgramCacheKey=()=>"fifa16-eight-weights-v1";part.material=material;
  }
  return{parts,textures,boneData,playerId,height,playerName};
}
function decodeTexture(w,h,format,data){
  const rgba=new Uint8Array(w*h*4);if(format===3)rgba.set(data.subarray(0,rgba.length));else{
    const nx=Math.ceil(w/4),ny=Math.ceil(h/4),block=format===0?8:16,c565=v=>[(v>>11&31)*255/31,(v>>5&63)*255/63,(v&31)*255/31,255];
    for(let by=0;by<ny;by++)for(let bx=0;bx<nx;bx++){
      const base=(by*nx+bx)*block,cb=base+(format===0?0:8),c0=data[cb]|data[cb+1]<<8,c1=data[cb+2]|data[cb+3]<<8,col=[c565(c0),c565(c1)];
      if(c0>c1||format!==0){col.push([0,1,2,3].map(k=>(2*col[0][k]+col[1][k])/3));col.push([0,1,2,3].map(k=>(col[0][k]+2*col[1][k])/3));}else{col.push([0,1,2,3].map(k=>(col[0][k]+col[1][k])/2));col.push([0,0,0,0]);}
      let bits=(data[cb+4]|data[cb+5]<<8|data[cb+6]<<16|data[cb+7]<<24)>>>0,ab=0,ap=[];
      if(format===2){const a0=data[base],a1=data[base+1];ap=[a0,a1];if(a0>a1)for(let n=1;n<=6;n++)ap.push(((7-n)*a0+n*a1)/7);else{for(let n=1;n<=4;n++)ap.push(((5-n)*a0+n*a1)/5);ap.push(0,255);}for(let n=0;n<6;n++)ab+=data[base+2+n]*2**(n*8);}
      for(let py=0;py<4;py++)for(let px=0;px<4;px++){const x=bx*4+px,y=by*4+py;if(x>=w||y>=h)continue;const p=py*4+px,c=col[(bits>>>(p*2))&3],at=(y*w+x)*4;rgba[at]=c[0];rgba[at+1]=c[1];rgba[at+2]=c[2];rgba[at+3]=format===1?(data[base+Math.floor(p/2)]>>((p%2)*4)&15)*17:format===2?ap[Math.floor(ab/2**(p*3))&7]:c[3];}
    }
  }
  const t=new THREE.DataTexture(rgba,w,h,THREE.RGBAFormat,THREE.UnsignedByteType);t.colorSpace=THREE.SRGBColorSpace;t.flipY=false;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.magFilter=THREE.LinearFilter;t.minFilter=THREE.LinearMipmapLinearFilter;t.generateMipmaps=true;t.needsUpdate=true;return t;
}
