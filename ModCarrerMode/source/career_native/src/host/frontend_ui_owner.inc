/* Registration is called only from FIFA's Background ViewModel factory,
 * never from the render worker. The engine Update dispatches on that same
 * thread; exiting Career may invalidate CareerContext without losing this
 * independent frontend owner. No native UI is invoked at registration. */
typedef void (*FrontendUiCallback)(void);
static PVOID volatile g_frontend_ui_callback;
static volatile LONG g_frontend_ui_running;
static volatile LONG64 g_frontend_ui_factory;

static LONG64 frontend_ui_factory(void)
{
    return InterlockedCompareExchange64(&g_frontend_ui_factory,0,0);
}

__declspec(dllexport) BOOL WINAPI Fifa16FrontendRegisterUiCallback(FrontendUiCallback callback)
{
    PVOID previous;
    LONG64 factory, next;
    if(!callback)return FALSE;
    previous=InterlockedCompareExchangePointer(&g_frontend_ui_callback,(PVOID)callback,NULL);
    if(previous && previous!=(PVOID)callback)return FALSE;
    /* Keep the factory revision and thread in one atomic publication. */
    do {
        factory=frontend_ui_factory();
        next=(LONG64)((((ULONGLONG)factory>>32)+1)<<32 | GetCurrentThreadId());
    } while(InterlockedCompareExchange64(&g_frontend_ui_factory,next,factory)!=factory);
    return TRUE;
}
static int frontend_ui_is_owner(void)
{
    return (DWORD)frontend_ui_factory()==GetCurrentThreadId();
}
static int frontend_ui_dispatching(void)
{
    return frontend_ui_is_owner()&&InterlockedCompareExchange(&g_frontend_ui_running,0,0)!=0;
}
static void drain_frontend_ui_tick(void)
{
    FrontendUiCallback callback;
    if(!frontend_ui_is_owner()||InterlockedCompareExchange(&g_frontend_ui_running,1,0))return;
    callback=(FrontendUiCallback)InterlockedCompareExchangePointer(&g_frontend_ui_callback,NULL,NULL);
    __try {if(callback)callback();}
    __except(EXCEPTION_EXECUTE_HANDLER){
        InterlockedCompareExchangePointer(&g_frontend_ui_callback,NULL,(PVOID)callback);
        append_loader_log("frontend_ui_callback_disabled");
    }
    InterlockedExchange(&g_frontend_ui_running,0);
}
