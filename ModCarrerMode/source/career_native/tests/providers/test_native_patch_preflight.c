#define _CRT_SECURE_NO_WARNINGS
/* Include the real initializer to test its actual patch table/barrier.
 * DllMain is not invoked by this console test; no game process is touched. */
#include "../../src/host/dinput8_wrapper.c"

static int failures;
static void *fake_vector_result;
static int vector_calls, notify_calls;
static void *last_notification;
static unsigned char last_dirty;
static void *fake_stats_vector(void *object, int category, unsigned char enabled)
{
    if (object && category == 4 && enabled == 1) ++vector_calls;
    return fake_vector_result;
}
static void fake_mark_dirty(void *notification, unsigned char dirty)
{
    ++notify_calls;
    last_notification = notification;
    last_dirty = dirty;
}
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
    void *fake_owner[2] = {(void *)(uintptr_t)0x1111, (void *)(uintptr_t)0x2222};
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
        "an unexpected original target stays rejected");
    unexpected[1] ^= 1;
    unexpected = base + g_call_patches[sizeof(g_call_patches) / sizeof(g_call_patches[0]) - 1].call_rva;
    unexpected[1] ^= 1;
    check(!career_patch_sites_ready(base, NULL),
        "the new pre-notification hook must match before any patch is installed");
    unexpected[1] ^= 1;
    check(career_patch_sites_ready(base, NULL),
        "the new pre-notification hook can recover after its target is restored");
    base[g_patches[1].rva] ^= 1;
    check(!career_patch_sites_ready(base, NULL),
        "every byte-patch site is checked before writing any call");
    base[g_patches[1].rva] ^= 1;
    check(career_patch_sites_ready(base, NULL), "readiness can recover safely");
    VirtualFree(base, 0, MEM_RELEASE);
    g_stats_vector = fake_stats_vector;
    fake_vector_result = (void *)(uintptr_t)0x1234;
    g_current_stats_provider_owner = (void *)(uintptr_t)0x4567;
    check(stats_vector_capture(&failures, 4, 1) == fake_vector_result &&
        g_current_stats_provider == fake_vector_result && vector_calls == 1,
        "capture UI vector without depending on a scorer string row");
    fake_vector_result = NULL;
    check(stats_vector_capture(&failures, 4, 1) == NULL &&
        g_current_stats_provider == NULL,
        "a missing native destination cannot reuse an earlier vector");
    g_stats_mark_dirty = fake_mark_dirty;
    stats_mark_dirty_capture(&failures, 1);
    check(notify_calls == 1 && last_notification == &failures && last_dirty == 1 &&
        !g_stats_publication_completed,
        "native notification survives missing custom payload without acknowledgement");
    g_current_stats_provider = (void *)(uintptr_t)0x1234;
    stats_mark_dirty_capture(&failures, 0);
    check(notify_calls == 2 && !last_dirty && !g_stats_publication_completed,
        "a clean native notification does not publish custom fields");
    g_current_stats_provider_owner = NULL;
    g_current_stats_provider = NULL;
    remember_pending_stats_refresh(fake_owner);
    check(g_stats_refresh_schedule.view_revision == 1 &&
        g_pending_stats_provider_registry == fake_owner[1],
        "a real native entry arms a new view with its current registry");
    clear_pending_stats_refresh();
    check(!g_pending_stats_provider_owner && !g_stats_refresh_schedule.view_revision,
        "context reset cancels pending view retries");
    printf("Career native patch readiness: %s (%d failures)\n",
        failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
