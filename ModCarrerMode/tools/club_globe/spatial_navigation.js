(() => {
function usable(element){return !element.closest('[inert]')&&!element.disabled&&!element.hidden&&element.getClientRects().length>0&&getComputedStyle(element).visibility!=='hidden';}
function next(elements,current,direction){
 const list=elements.filter(usable);if(!list.length)return null;
 if(!usable(current)||!list.includes(current))return list[0];
 const a=current.getBoundingClientRect(),horizontal=direction==='left'||direction==='right',sign=direction==='left'||direction==='up'?-1:1;
 let winner=null,best=Infinity;
 for(const el of list){if(el===current)continue;const b=el.getBoundingClientRect(),dx=(b.left+b.right-a.left-a.right)/2,dy=(b.top+b.bottom-a.top-a.bottom)/2,forward=(horizontal?dx:dy)*sign,side=Math.abs(horizontal?dy:dx);if(forward<=3)continue;
 const overlap=horizontal?Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top):Math.min(a.right,b.right)-Math.max(a.left,b.left);
 const score=forward+side*2+(overlap>0?0:500);if(score<best){best=score;winner=el;}}
 return winner||current;
}
window.FFSpatialNavigation={next,usable};
})();
