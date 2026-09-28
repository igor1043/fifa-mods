#include "easfc_hide_plugin_safe.c"

int main(void)
{
    unsigned char *candidate;
    int result = 0;

    if (safe_signature_compare((const unsigned char *)(uintptr_t)1U)
            != SAFE_FAULT)
        return 10;

    candidate = (unsigned char *)VirtualAlloc(NULL, 0x1000U,
        MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!candidate)
        return 11;

    memcpy(candidate, k_widget_signature, EASFC_SIGNATURE_SIZE);
    if (safe_signature_compare(candidate) != SAFE_MATCH)
        result = 12;
    else if (patch_candidate(candidate) != PATCH_APPLIED)
        result = 13;
    else if (candidate[0x1EU] != 0x74U || candidate[0x26U] != 0x74U
            || candidate[0x2EU] != 0x74U)
        result = 14;

    VirtualFree(candidate, 0, MEM_RELEASE);
    return result;
}
