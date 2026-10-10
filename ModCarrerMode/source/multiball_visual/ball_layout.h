#ifndef BALL_LAYOUT_H
#define BALL_LAYOUT_H
#include <math.h>
#include <stdint.h>
#include <string.h>
#define BALL_STATE_BYTES 0x820
#define SPARE_BALLS 13
#define BALL_SUPPORT_HEIGHT 5.2f
/* FIFA world coordinates are centimetres: X along the pitch, Z across it. */
static const float ball_positions[SPARE_BALLS][3] = {
 {-5450,11.1252f,-2016},{-5450,11.1252f,2016},
 {5450,11.1252f,-2016},{5450,11.1252f,2016},
 {-4200,11.1252f,-3650},{-2100,11.1252f,-3650},
 {0,11.1252f,-3650},{2100,11.1252f,-3650},{4200,11.1252f,-3650},
 {-4200,11.1252f,3650},{-1400,11.1252f,3650},
 {1400,11.1252f,3650},{4200,11.1252f,3650}
};
/* Only a PRIVATE rendering snapshot is changed; never the live ball state. */
static int ball_expand_snapshot(unsigned char *state, int include_match_ball) {
 int count, id, i, reserved; float original[16], scale;
 memcpy(&count,state+0x7f8,4); memcpy(&id,state+0x50,4);
 if(id!=1 || count<1 || count>16-SPARE_BALLS || state[0x80e] || !state[0x80f] ||
    !state[0x7fc] || !state[0x7fd])return 0;
 memcpy(original,state+0x3b0,sizeof(original));
 scale=sqrtf(original[0]*original[0]+original[1]*original[1]+original[2]*original[2]);
 if(!isfinite(scale) || scale<0.5f || scale>2.0f)return 0;
 reserved=count;
 for(i=0;i<SPARE_BALLS;i++) {
  float matrix[16]={0};
  matrix[0]=matrix[5]=matrix[10]=scale;matrix[15]=1;
  matrix[12]=ball_positions[i][0];matrix[13]=ball_positions[i][1]+BALL_SUPPORT_HEIGHT;matrix[14]=ball_positions[i][2];
  memcpy(state+0x3b0+(i+reserved)*64,matrix,sizeof(matrix));
  /* Share the current ball's lighting bindings, not stale spare slot values. */
  memcpy(state+0xa0+(i+reserved)*48,state+0xa0,48);
  state[0x7fd+i+reserved]=1;
 }
 count=SPARE_BALLS+reserved;memcpy(state+0x7f8,&count,4);
 if(!include_match_ball)for(i=0;i<reserved;i++)state[0x7fd+i]=0;
 return 1;
}
/* Low rounded holder: the existing graphical mesh is flattened into a base.
   This prototype deliberately shares the loaded ball material. */
static void ball_support_snapshot(unsigned char *state) {
 int count,reserved,i;float scale;
 memcpy(&count,state+0x7f8,4);reserved=count-SPARE_BALLS;
 if(reserved<1 || reserved>3)return;
 memcpy(&scale,state+0x3b0+reserved*64,4);
 for(i=0;i<SPARE_BALLS;i++) {
  float matrix[16]={0};matrix[0]=matrix[10]=scale*1.45f;
  matrix[5]=scale*0.2337f;matrix[15]=1;
  matrix[12]=ball_positions[i][0];matrix[13]=BALL_SUPPORT_HEIGHT*0.5f;matrix[14]=ball_positions[i][2];
  memcpy(state+0x3b0+(i+reserved)*64,matrix,64);
 }
}
#endif
