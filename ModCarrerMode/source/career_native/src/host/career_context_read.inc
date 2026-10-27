/* Read-only service identity for external readers. Unlike a deferred card
 * owner this remains available on financial/mail screens. Readers verify the
 * sequence, registry entry, service vtable and current selected context. */
typedef struct CareerContextRead {
    DWORD schema, size;
    volatile LONG sequence;
    DWORD pid;
    uintptr_t service, vtable, registry;
    DWORD epoch, owner_thread;
} CareerContextRead;
__declspec(dllexport) CareerContextRead Fifa16CareerContextRead = {
    1, sizeof(CareerContextRead), 0, 0, 0, 0, 0, 0, 0
};
static SRWLOCK g_context_read_lock=SRWLOCK_INIT;
static void publish_career_context_read(void *service, void *owner)
{
    uintptr_t vtable = 0, registry = 0;
    if (!is_readable_range(service, 32) || !is_readable_range(owner, 16)) return;
    memcpy(&vtable, service, sizeof(vtable));
    memcpy(&registry, (unsigned char *)owner + 8, sizeof(registry));
    if (!vtable || !registry) return;
    AcquireSRWLockExclusive(&g_context_read_lock);
    if (Fifa16CareerContextRead.service==(uintptr_t)service
        && Fifa16CareerContextRead.vtable==vtable && Fifa16CareerContextRead.registry==registry
        && Fifa16CareerContextRead.epoch==fce_runtime_context_epoch()
        && Fifa16CareerContextRead.owner_thread==GetCurrentThreadId()) {
        ReleaseSRWLockExclusive(&g_context_read_lock);return;
    }
    InterlockedIncrement(&Fifa16CareerContextRead.sequence);
    Fifa16CareerContextRead.pid = GetCurrentProcessId();
    Fifa16CareerContextRead.service = (uintptr_t)service;
    Fifa16CareerContextRead.vtable = vtable;
    Fifa16CareerContextRead.registry = registry;
    Fifa16CareerContextRead.epoch = fce_runtime_context_epoch();
    Fifa16CareerContextRead.owner_thread = GetCurrentThreadId();
    InterlockedIncrement(&Fifa16CareerContextRead.sequence);
    ReleaseSRWLockExclusive(&g_context_read_lock);
}
