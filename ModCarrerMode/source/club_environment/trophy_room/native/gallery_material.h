#pragma once
namespace gallery_material {
// The native light-volume query uses legacy packed SSE memory operands.
// Its position argument must retain 16-byte alignment even when callers add
// other stack locals; an ordinary float[4] does not guarantee that alignment.
struct alignas(16) LightSample {float value[4]={0,150,0,1};};
static_assert(alignof(LightSample)==16&&sizeof(LightSample)==16);
// Trophy materials use envSpecTexture as well as the general specular slot.
// Keep the native ribbon/plastic/metal coefficient maps separate.
template<class Bind>inline void bindSpecular(bool cup,bool available,Bind bind,bool roomEnvironment=false){
 // A gallery-owned cubemap was already assigned to this private material.
 // Do not overwrite it with the field probe returned by the native query.
 if(!available||(cup&&roomEnvironment))return;
 bind("INDIRECT_SPECULAR_TEXTURE");if(cup)bind("envSpecTexture");
}
}
