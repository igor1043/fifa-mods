#ifndef KICKOFF_SPACING_H
#define KICKOFF_SPACING_H
#include <math.h>
#include <stdint.h>
/* This is native pass charge, not a promise of proportional ball velocity. */
static __inline int kickoff_soften_charge(float original,float *adjusted) {
 if(!isfinite(original) || original<=0.0f || original>1.0f)return 0;
 *adjusted=original*0.75f;return 1;
}
static __inline int kickoff_central_receiver_sign(const float v[4]) {
 if(!isfinite(v[0]) || !isfinite(v[1]) || !isfinite(v[2]) ||
    fabsf(v[0])<0.5f || fabsf(v[0])>2.0f || fabsf(v[1])>=0.2f ||
    fabsf(v[2])<2.0f || fabsf(v[2])>7.0f)return 0;
 return v[0]>0.0f?1:-1;
}
static __inline int kickoff_face_receiver(const float position[4],const float target[4],float *yaw) {
 float dx,dz;
 if(!isfinite(position[0]) || !isfinite(position[1]) || !isfinite(position[2]) ||
    !isfinite(target[0]) || !isfinite(target[2]) || fabsf(position[1])>0.2f ||
    position[0]*position[0]+position[2]*position[2]>9.0f)return 0;
 dx=target[0]-position[0];dz=target[2]-position[2];
 if(dx*dx+dz*dz<100.0f)return 0;
 *yaw=atan2f(-dz,dx);return 1;
}
/* Runtime field units: metre * 3.2808. Circle 9.15m, target 10.25m. */
static __inline int kickoff_space_other(uint32_t role,uint32_t side,uint32_t kicking_side,
                                       int special,float v[4]) {
 float radius,scale;
 if(special || role>27U || side>1U || side!=kicking_side ||
    !isfinite(v[0]) || !isfinite(v[1]) || !isfinite(v[2]) || fabsf(v[1])>=0.2f)return 0;
 radius=sqrtf(v[0]*v[0]+v[2]*v[2]);
 if(radius<3.0f || radius>30.01932f)return 0;
 scale=33.6282f/radius;v[0]*=scale;v[2]*=scale;
 return 1;
}
/* Limit the computed kick velocity, leaving direction and homogeneous W intact. */
static __inline int kickoff_limit_velocity(float velocity[4],float *before,float *after) {
 float speed,factor;
 if(!isfinite(velocity[0]) || !isfinite(velocity[1]) || !isfinite(velocity[2]))return 0;
 speed=sqrtf(velocity[0]*velocity[0]+velocity[1]*velocity[1]+velocity[2]*velocity[2]);
 if(!isfinite(speed) || speed<6.0f || speed>400.0f)return 0;
 factor=0.55f;
 if(speed*factor>26.2464f)factor=26.2464f/speed;
 *before=speed;*after=speed*factor;
 velocity[0]*=factor;velocity[1]*=factor;velocity[2]*=factor;return 1;
}
#endif
