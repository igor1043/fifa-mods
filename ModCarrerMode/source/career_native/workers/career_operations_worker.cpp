#include "../src/features/operations/career_operations_io.h"
#include <cstdio>
int main(int argc,char**argv){if(argc!=3){fprintf(stderr,"usage: career_operations_worker.exe REQUEST MOD_DIRECTORY\n");return 2;}
    std::string message;bool ok=career_ops::run_request(argv[1],argv[2],message);
    printf("status=%s message=%s\n",ok?"ok":"error",message.c_str());
    std::string status=std::string(argv[1])+".result.txt";
    FILE*f=fopen(status.c_str(),"wb");if(f){fprintf(f,"status=%s\nmessage=%s\n",ok?"ok":"error",message.c_str());fclose(f);}
    return ok?0:1;
}
