#define _CRT_SECURE_NO_WARNINGS
/* Include the real initializer to test its actual patch table/barrier.
 * DllMain is not invoked by this console test; no game process is touched. */
#include "integration/dinput8_wrapper.c"

static int failures;
static void check(int condition, const char *name)
{
    if (!condition) { ++failures; printf("FAIL: %s\n", name); }
}

static int commit_site(unsigned char *base, uintptr_t rva)
{
    return VirtualAlloc(base + (rva & ~(uintptr_t)4095), 4096,
        MEM_COMMIT, PAGE_READWRITE) != NULL;
}

int main(void)
{
    SIZE_T i;
    unsigned char *base = (unsigned char *)VirtualAlloc(NULL, 0x09525000,
        MEM_RESERVE, PAGE_NOACCESS);
    unsigned char *missing;
    unsigned char *unexpected;
    unsigned char original[5];
    if (!base) return 2;
    for (i = 0; i < sizeof(g_patches) / sizeof(g_patches[0]); ++i) {
        const PatchSpec *p = &g_patches[i];
        if (!commit_site(base, p->rva)) return 2;
        memcpy(base + p->rva, p->expected, p->size);
    }
    for (i = 0; i < sizeof(g_call_patches) / sizeof(g_call_patches[0]); ++i) {
        const CallPatchSpec *p = &g_call_patches[i];
        int32_t delta = (int32_t)((intptr_t)p->expected_target_rva -
            (intptr_t)p->call_rva - 5);
        if (!commit_site(base, p->call_rva)) return 2;
        base[p->call_rva] = 0xE8;
        memcpy(base + p->call_rva + 1, &delta, sizeof(delta));
    }
    check(career_patch_sites_ready(base, NULL), "all native sites are ready");
    missing = base + g_call_patches[0].call_rva;
    memcpy(original, missing, sizeof(original));
    memset(missing, 0xCC, sizeof(original));
    check(!career_patch_sites_ready(base, NULL),
        "a decoded standings marker is not enough to start Career hooks");
    check(missing[0] == 0xCC && missing[4] == 0xCC,
        "waiting does not modify an encrypted call site");
    memcpy(missing, original, sizeof(original));
    check(career_patch_sites_ready(base, NULL),
        "late native decryption allows initialization on the next attempt");
    unexpected = base + g_call_patches[18].call_rva;
    unexpected[1] ^= 1;
    check(!career_patch_sites_ready(base, NULL),
        "an unexpected original target stays rejected, including the last site");
    unexpected[1] ^= 1;
    base[g_patches[1].rva] ^= 1;
    check(!career_patch_sites_ready(base, NULL),
        "every byte-patch site is checked before writing any call");
    base[g_patches[1].rva] ^= 1;
    check(career_patch_sites_ready(base, NULL), "readiness can recover safely");
    VirtualFree(base, 0, MEM_RELEASE);
    printf("Career native patch readiness: %s (%d failures)\n",
        failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
