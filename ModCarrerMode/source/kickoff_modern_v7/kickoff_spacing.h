#ifndef KICKOFF_SPACING_H
#define KICKOFF_SPACING_H
#include <math.h>
#include <stdint.h>
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
