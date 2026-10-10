#include <assert.h>
#include <stdio.h>
#include "ball_layout.h"
int main(void) {
 unsigned char source[BALL_STATE_BYTES]={0},copy[BALL_STATE_BYTES];int one=1,count,i;float matrix[16]={0};
 memcpy(source+0x50,&one,4);memcpy(source+0x7f8,&one,4);
 source[0x7fc]=source[0x7fd]=source[0x80f]=1;
 matrix[0]=matrix[5]=matrix[10]=1.095f;matrix[15]=1;matrix[12]=1234;
 memcpy(source+0x3b0,matrix,sizeof(matrix));memcpy(copy,source,sizeof(copy));
 assert(ball_expand_snapshot(copy,0));memcpy(&count,copy+0x7f8,4);assert(count==14);
 assert(!copy[0x7fd]);assert(source[0x7fd]);assert(!memcmp(copy+0x3b0,source+0x3b0,64));
 for(i=0;i<SPARE_BALLS;i++) {
  float m[16];memcpy(m,copy+0x3b0+(i+1)*64,64);
  assert(fabsf(m[12])>5250 || fabsf(m[14])>3400);
  assert(m[13]>16 && m[13]<17);assert(m[15]==1);assert(copy[0x7fe + i]);
 }
 memcpy(copy,source,sizeof(copy));copy[0x50]=0;assert(!ball_expand_snapshot(copy,0));
 memcpy(copy,source,sizeof(copy));copy[0x80e]=1;assert(!ball_expand_snapshot(copy,0));
 memcpy(copy,source,sizeof(copy));copy[0x7f8]=4;assert(!ball_expand_snapshot(copy,0));
 for(i=2;i<=3;i++) {
  float extra[16];memcpy(copy,source,sizeof(copy));memcpy(copy+0x7f8,&i,4);
  copy[0x7fe]=1;copy[0x3f0]=123;
  assert(ball_expand_snapshot(copy,0));assert(copy[0x3f0]==123);
  memcpy(&count,copy+0x7f8,4);assert(count==i+13);assert(!copy[0x7fd] && !copy[0x7fe]);
  memcpy(extra,copy+0x3b0+i*64,64);assert(extra[12]==-5450);
 }
 memcpy(copy,source,sizeof(copy));assert(ball_expand_snapshot(copy,1));assert(copy[0x7fd]);
 ball_support_snapshot(copy);
 for(i=0;i<SPARE_BALLS;i++) {
  float m[16];memcpy(m,copy+0x3b0+(i+1)*64,64);
  assert(m[12]==ball_positions[i][0] && m[14]==ball_positions[i][2]);
  assert(m[13]==2.6f && m[0]>m[5]*6);assert(m[15]==1);
 }
 puts("PASS layout, world units, original slot, menu exclusion, hidden ball, busy slots");return 0;
}
