(() => {
'use strict';
const model=window.MARKET_REVIEW,host=document.getElementById('stage'),picker=document.getElementById('save-picker');
let dataset=model.datasets.find(d=>d.id===model.default)||model.datasets[0],key='entry',focus=0;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scene=()=>dataset.scenes.find(s=>s.key===key)||dataset.scenes.find(s=>s.key==='overview');
function node(n){
 if(n.type==='rect')return `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" fill="${n.color}"/>`;
 if(n.type==='dot')return `<ellipse cx="${n.x+n.w/2}" cy="${n.y+n.h/2}" rx="${n.w/2}" ry="${n.h/2}" fill="${n.color}"/>`;
 if(n.type==='image')return dataset.assets[n.asset]?`<image x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" href="${esc(dataset.assets[n.asset])}" preserveAspectRatio="xMidYMid meet"/>`:'';
 if(n.type==='text'){
  const x=n.align===1?n.x+n.w:n.align===2?n.x+n.w/2:n.x,anchor=n.align===1?'end':n.align===2?'middle':'start';
  return `<text x="${x}" y="${n.y+n.size*.94}" font-size="${n.size}" font-weight="${n.bold?600:400}" text-anchor="${anchor}" fill="${n.color}"><title>${esc(n.text)}</title>${esc(n.display??n.text)}</text>`;
 }
 if(n.type==='action')return `<g data-action="${n.index}" role="button" aria-label="${esc(n.text||'Abrir negócios da liga')}" tabindex="-1"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" fill="${n.color}"/>${n.text?`<text x="${n.x+n.w/2}" y="${n.y+n.h/2+n.size*.34}" fill="${n.ink}" font-size="${n.size}" text-anchor="middle">${esc(n.text)}</text>`:''}</g>`;
 return '';
}
function render(){
 const s=scene();key=s.key;focus=Math.min(focus,s.actions.length-1);
 const a=s.actions[focus];
 host.innerHTML=`<svg viewBox="0 0 1920 1080" role="img" aria-label="${esc(s.title)}">${s.nodes.map(node).join('')}${a?`<rect class="focus-ring" x="${a.x+2}" y="${a.y+2}" width="${a.w-4}" height="${a.h-4}"/>`:''}</svg>`;
 document.title=s.title+' · Prévia FIFA';
}
async function go(target){
 if(target==='refresh'){
  const busy=document.getElementById('busy');busy.hidden=false;
  try{
   if(location.protocol==='file:'){location.reload();return;}
   const response=await fetch('/api/refresh?save='+encodeURIComponent(dataset.id),{cache:'no-store'});
   if(!response.ok)throw Error(await response.text());
   const updated=await response.json();Object.assign(dataset,updated);render();
  }catch(error){alert('Não foi possível atualizar: '+error.message);}finally{busy.hidden=true;}
  return;
 }
 key=target;focus=target==='entry'?scene().actions.length-1:0;render();host.focus({preventScroll:true});
}
function move(direction){const s=scene();if(direction<2&&s.pagination?.count>1){go(s.pagination[direction===0?'previous':'next']);return;}focus=s.navigation[focus]?.[direction]??focus;render();}
function changeTab(delta){const tabs=['overview','leagues','clubs','deals','mine'],group=key.startsWith('league')?'leagues':key.startsWith('deals')?'deals':key;go(tabs[(Math.max(0,tabs.indexOf(group))+delta+tabs.length)%tabs.length]);}
picker.innerHTML=model.datasets.map(d=>`<option value="${esc(d.id)}">${esc(d.label)}</option>`).join('');picker.value=dataset.id;
picker.onchange=()=>{dataset=model.datasets.find(d=>d.id===picker.value);key='entry';focus=scene().actions.length-1;render();};
document.getElementById('show-entry').onclick=()=>go('entry');
host.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(b){focus=Number(b.dataset.action);go(scene().actions[focus].target);}});
host.addEventListener('pointerover',e=>{const b=e.target.closest('[data-action]');if(b&&focus!==Number(b.dataset.action)){focus=Number(b.dataset.action);const a=scene().actions[focus],ring=host.querySelector('.focus-ring');if(ring){ring.setAttribute('x',a.x+2);ring.setAttribute('y',a.y+2);ring.setAttribute('width',a.w-4);ring.setAttribute('height',a.h-4);}}});
document.addEventListener('keydown',e=>{
 if(e.target===picker)return;
 const arrows={ArrowLeft:0,ArrowRight:1,ArrowUp:2,ArrowDown:3};
 if(e.key in arrows){e.preventDefault();move(arrows[e.key]);}
 else if(e.key==='Enter'){e.preventDefault();go(scene().actions[focus].target);}
 else if(e.key==='Escape'||e.key==='Backspace'){e.preventDefault();go(key==='entry'?'entry':scene().back);}
});
let previous=0;
function pad(now){
 const p=Array.from(navigator.getGamepads?.()||[]).find(Boolean);
 if(p&&now-previous>190){
  const keys=p.buttons;const x=p.axes[0]||0,y=p.axes[1]||0;
  if(keys[0]?.pressed){previous=now;go(scene().actions[focus].target);}
  else if(keys[1]?.pressed){previous=now;go(scene().back);}
  else if(keys[4]?.pressed){previous=now;changeTab(-1);}
  else if(keys[5]?.pressed){previous=now;changeTab(1);}
  else{const dir=keys[14]?.pressed||x<-.6?0:keys[15]?.pressed||x>.6?1:keys[12]?.pressed||y<-.6?2:keys[13]?.pressed||y>.6?3:-1;if(dir>=0){previous=now;move(dir);}}
 }requestAnimationFrame(pad);
}
focus=scene().actions.length-1;render();requestAnimationFrame(pad);
window.marketReview={go,move,getState:()=>({save:dataset.id,key,focus,scene:scene()})};
})();
