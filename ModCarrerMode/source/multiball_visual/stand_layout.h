#pragma once
#include "ball_layout.h"
/* Same centres as the spare balls. Front of each support faces the pitch. */
static float stand_yaw(unsigned index) {
 const float x=ball_positions[index][0],z=ball_positions[index][2];
 return index<4?(x<0?1.570796327f:-1.570796327f):(z<0?0.0f:3.141592654f);
}
static void stand_position(unsigned char *record,unsigned index,float height) {
 const float p[4]={ball_positions[index][0],height,ball_positions[index][2],stand_yaw(index)};
 memcpy(record+0x20,p,16);memcpy(record+0x30,p,16);
}
