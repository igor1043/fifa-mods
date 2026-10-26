// Resolve the editor's local Three.js dependency for data/geometry tests.
export async function resolve(specifier,context,next){
 if(specifier==='three')return {url:new URL('./vendor/three/build/three.module.js',import.meta.url).href,shortCircuit:true};
 return next(specifier,context);
}
