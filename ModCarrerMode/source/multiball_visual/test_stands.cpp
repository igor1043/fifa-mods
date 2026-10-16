#include <assert.h>
#include <stdio.h>
#include "stand_layout.h"
#include "stand_assets.h"
int main(){
 for(const auto& asset:standAssets){
  assert(asset.ballHeight>11.1252f&&asset.ballHeight<50);
  unsigned char source[BALL_STATE_BYTES]={},state[BALL_STATE_BYTES];int count=1;
  memcpy(source+0x50,&count,4);memcpy(source+0x7f8,&count,4);
  source[0x7fc]=source[0x7fd]=source[0x80f]=1;
  float matrix[16]={};matrix[0]=matrix[5]=matrix[10]=1.095f;matrix[15]=1;
  memcpy(source+0x3b0,matrix,64);memcpy(state,source,sizeof(state));
  assert(ball_expand_snapshot_at_height(state,0,asset.ballHeight));
  for(unsigned i=0;i<SPARE_BALLS;++i){
   unsigned char record[0x50]={};stand_position(record,i,0);
   float ball[16],stand[4];memcpy(ball,state+0x3b0+(i+1)*64,64);memcpy(stand,record+0x20,16);
   assert(stand[0]==ball[12]&&stand[2]==ball[14]);assert(stand[1]==0&&ball[13]==asset.ballHeight);
   assert(!memcmp(record+0x20,record+0x30,16));
   const float dot=-stand[0]*sinf(stand[3])-stand[2]*cosf(stand[3]);assert(dot>3000);
   stand_position(record,i,-3000);memcpy(stand,record+0x20,16);assert(stand[1]==-3000);
  }
  assert(!memcmp(source+0x3b0,state+0x3b0,64));assert(source[0x7fd]);
  memcpy(state,source,sizeof(state));assert(!ball_expand_snapshot_at_height(state,0,NAN));
  assert(!ball_expand_snapshot_at_height(state,0,200));
 }
 puts("PASS five RX3 variants: ball/support centres, contact heights, inward orientation, hidden transform, gameplay ball preserved");
}
