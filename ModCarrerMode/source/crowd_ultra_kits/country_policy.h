#pragma once
#include <string.h>
static inline bool ultra_brazil_country(const char* name) {
    return name && (!strcmp(name, "Brazil") || !strcmp(name, "Brasil") || !strncmp(name, "Brasil ", 7));
}
