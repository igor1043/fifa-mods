#pragma once
#include <map>
#include <string>
#include <istream>
#include <sstream>
#include <vector>
namespace clubstadium {
inline std::map<int,std::string> names(std::istream& in){
 std::map<int,std::string> result;std::string line;
 while(std::getline(in,line)){
  if(line.size()>8192)continue;
  std::vector<std::string> fields;std::string value;std::istringstream row(line);while(std::getline(row,value,'|'))fields.push_back(value);
  if(fields.size()<5||fields[3].empty()||fields[3]=="AO VIVO")continue;
  try{size_t used=0;int id=std::stoi(fields[0],&used);if(used==fields[0].size()&&id>0&&id<2000000)result[id]=fields[3];}catch(...){}
 }
 return result;
}
}
