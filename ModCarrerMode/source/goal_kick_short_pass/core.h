#ifndef F16_CORE_H
#define F16_CORE_H
#include <stdint.h>
#include <stddef.h>
#define F16_SIZE 0xf000
#define F16_GOAL 0x9000
#define F16_IMAGE_SIZE 0x9525000
#define F16_HOOKS 11
typedef struct {uint32_t pos,end,target;} Fixup;
typedef struct {uint32_t pos,to,span,opcode;} Patch;
typedef struct {const char *name;uint32_t rva,offset,length;const unsigned char *bytes;const Fixup *fix;size_t nfix;const Patch *patch;size_t npatch;} Clone;
typedef struct {const char *name;uint32_t rva,length;const unsigned char *bytes;} Signature;
typedef struct {uint32_t rva,width;uint64_t original,replacement;int changed;} Hook;
extern const Clone f16_clones[];
extern const size_t f16_nclones;
extern const Signature f16_signatures[];
extern const size_t f16_nsignatures;
extern const unsigned char f16_kickoff[0x9000],f16_goal[0x6000];
int f16_bounds(uint64_t image,uint64_t min,uint64_t max,uint64_t *low,uint64_t *high);
int f16_build(unsigned char *out,uint64_t image,uint64_t allocation);
int f16_plan(Hook *hooks,uint64_t image,uint64_t allocation);
typedef int (*F16CAS)(void *context,uint32_t rva,uint32_t width,uint64_t expected,uint64_t desired);
int f16_publish(Hook *hooks,F16CAS cas,void *context);
int f16_rollback(Hook *hooks,F16CAS cas,void *context);
#if defined(F16_LAYOUT_TEST) && !defined(_WIN32)
#define F16_LAYOUT_ABI __attribute__((ms_abi))
#else
#define F16_LAYOUT_ABI
#endif
void F16_LAYOUT_ABI f16_layout_init(unsigned char *context);
int F16_LAYOUT_ABI f16_layout_target(unsigned char *context,void *team,void *player,float *out);
void F16_LAYOUT_ABI f16_goalpass_adjust(unsigned char *context,void *subsystem,void *query,void *alternate);
#endif
