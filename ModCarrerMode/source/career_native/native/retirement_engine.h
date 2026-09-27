#ifndef RETIREMENT_ENGINE_H
#define RETIREMENT_ENGINE_H

#include <windows.h>

typedef struct RetirementApplyResult {
    int status;
    unsigned int players_seen;
    unsigned int players_retiring;
    unsigned int players_changed;
    unsigned int crc_before;
    unsigned int crc_after;
    char message[256];
    char backup_data[1024];
    char backup_index[1024];
} RetirementApplyResult;

/* The engine is inert unless career_retirement_background.ini contains
 * enabled=1.  It is intentionally independent from the UI/NAV layer. */
int retirement_engine_apply_file(const char *data_path, const char *mode,
    int target_age, RetirementApplyResult *result);
int retirement_engine_apply_buffer(void *buffer, SIZE_T size,
    const char *mode, int target_age, RetirementApplyResult *result);
int retirement_engine_apply_buffer_from_config(void *buffer, SIZE_T size,
    RetirementApplyResult *result);
int retirement_engine_backup_before_write(const char *data_path);
void retirement_engine_set_mod_dir(const char *mod_dir);
int retirement_engine_start(const char *mod_dir);
void retirement_engine_note_write(const char *data_path);

#endif
