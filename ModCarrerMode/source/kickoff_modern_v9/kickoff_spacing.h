#ifndef KICKOFF_SPACING_H
#define KICKOFF_SPACING_H
#include <math.h>
#include <stdint.h>
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
#endif
