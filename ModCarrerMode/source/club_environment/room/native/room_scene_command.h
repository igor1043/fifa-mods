#pragma once
#include <cstdint>
#include <cstring>
namespace room_command {
struct Request {uint32_t club=0;uint64_t sequence=0;int code=0;char nonce[17]{};};
inline bool number(const char*&p,uint64_t&value,uint64_t maximum){
 value=0;unsigned digits=0;
 while(*p>='0'&&*p<='9'){
  const auto digit=static_cast<unsigned>(*p-'0');
  if(++digits>16||value>(maximum-digit)/10)return false;
  value=value*10+digit;++p;
 }
 return digits>0;
}
// Exactly one bounded command, never a substring search through game memory.
inline bool parse(const char*wire,Request&out){
 if(!wire||std::strncmp(wire,"S16ROOM2|",9))return false;
 const char*p=wire+9;uint64_t club=0,sequence=0,code=0;Request next;
 if(!number(p,club,0xffffffffull)||!club||*p++!='|')return false;
 for(unsigned i=0;i<16;++i){const char c=*p++;if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;next.nonce[i]=c;}
 if(*p++!='|'||!number(p,sequence,9007199254740991ull)||!sequence||*p++!='|')return false;
 const bool negative=*p=='-';if(negative)++p;
 if(!number(p,code,127)||std::strcmp(p,"|ENDROOM"))return false;
 if(negative&&(code<1||code>5))return false;
 next.club=static_cast<uint32_t>(club);next.sequence=sequence;next.code=negative?-static_cast<int>(code):static_cast<int>(code);
 out=next;return true;
}
struct Receipt {
 uint32_t club=0;uint64_t sequence=0;char nonce[17]{};
 bool accepts(const Request&r)const{return club!=r.club||std::strcmp(nonce,r.nonce)||r.sequence>sequence;}
 void commit(const Request&r){club=r.club;sequence=r.sequence;std::memcpy(nonce,r.nonce,sizeof nonce);}
};
}
