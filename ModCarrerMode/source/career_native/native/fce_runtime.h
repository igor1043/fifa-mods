#ifndef FIFA16_FCE_RUNTIME_H
#define FIFA16_FCE_RUNTIME_H
#include "fce_model.h"
typedef struct FceLiveSnapshot FceLiveSnapshot;
typedef void (*FceRuntimeReadyCallback)(unsigned long generation);
typedef enum FceRuntimeLogMode {
    FCE_RUNTIME_LOG_PRODUCTION = 0,
    FCE_RUNTIME_LOG_DEVELOPMENT = 1,
    FCE_RUNTIME_LOG_TRACE = 2
} FceRuntimeLogMode;
void fce_runtime_log_dir(const char *directory);
/* Logging is selected once at process startup from
 * ModCarrerMode\career_native_mode.ini.  Production keeps only critical
 * runtime diagnostics; development/trace retain the verbose row dumps. */
int fce_runtime_log_mode(void);
int fce_runtime_log_verbose(void);
void fce_runtime_set_ready_callback(FceRuntimeReadyCallback callback);
void fce_runtime_request_refresh(void);
/* Keep sampling the live career model while a competition provider is
 * available. Repeated calls extend the window without resetting FCE's
 * settle counter or creating a redraw loop. */
void fce_runtime_keep_fresh(unsigned window_ms, unsigned interval_ms);
void fce_runtime_suppress_refresh(int suppress);
int fce_runtime_install(void);
/* Drop every published model when FIFA changes the active career context.
 * The next provider-boundary acquire rebuilds it from the live FCE tables. */
void fce_runtime_invalidate(void);
/* True only after FCE completed two Update cycles after a context/request
 * boundary. UI adornments must remain hidden while FIFA rebuilds a career. */
int fce_runtime_is_stable(void);
/* Called only at the native UI provider boundary. Never starts a process. */
FceLiveSnapshot *fce_runtime_acquire(void);
/* Retains only an already-published model.  Safe for UI decoration paths
 * that must never request a capture while a calendar cell is rendered. */
FceLiveSnapshot *fce_runtime_cached_acquire(void);
const FceModel *fce_runtime_model(const FceLiveSnapshot *);
unsigned long fce_runtime_generation(const FceLiveSnapshot *);
void fce_runtime_release(FceLiveSnapshot *);
#endif
