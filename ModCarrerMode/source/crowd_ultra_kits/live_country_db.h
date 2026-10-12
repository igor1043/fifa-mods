#pragma once

// The frontend team-name resolver and the registration of service 0x21 both
// expose the database used by the current game mode. Prefer that backend over
// the installed T3DB. Never query the database from the draw hooks.
using ResolveTeamName = uintptr_t (__fastcall*)(void*, int, void*);
static ResolveTeamName originalTeamName;
static void* volatile currentCountryService;
static SRWLOCK countryLock = SRWLOCK_INIT;
static SRWLOCK countryRefreshLock = SRWLOCK_INIT;
static std::unordered_map<int, bool> liveClubCountries;
static bool countrySnapshotReady;
static uintptr_t countrySnapshotBackend;

struct CountryRow { int id, value; };
#include "installed_country_db.h"

static void remember_country_service(void* service) {
    if (service && InterlockedExchangePointer(&currentCountryService, service) != service)
        log_event("country_service_captured service=%p", service);
}
static uintptr_t __fastcall capture_team_name(void* service, int team, void* result) {
    const uintptr_t originalResult = originalTeamName(service, team, result);
    remember_country_service(service);
    return originalResult;
}
static void __fastcall capture_country_registration(void* registry, void* descriptor, void* service) {
    ((void (__fastcall*)(void*, void*, void*))(image + 0x4461f10))(registry, descriptor, service);
    int index = 0; uintptr_t type = 0;
    if (read((uintptr_t)descriptor, index) && index == 0x21 &&
        read((uintptr_t)descriptor + 8, type) && type == image + 0x3314c28)
        remember_country_service(service);
}

static bool current_country_backend(uintptr_t& backend) {
    const uintptr_t service = (uintptr_t)InterlockedCompareExchangePointer(&currentCountryService, nullptr, nullptr);
    uintptr_t registry = 0, type = 0, wrapper = 0, actual = 0, vtable = 0, execute = 0;
    int index = 0, count = 0;
    backend = 0;
    // Constructor 5b3c430 writes this service's owner registry at offset 0x10.
    // Validate the current registry entry to reject a deleted/replaced service.
    return service && read(service + 0x10, registry) && registry &&
        read(registry + 0x21 * 32, index) && index == 0x21 &&
        read(registry + 0x21 * 32 + 8, type) && type == image + 0x3314c28 &&
        read(registry + 0x21 * 32 + 16, count) && count > 0 && count <= 64 &&
        read(registry + 0x21 * 32 + 24, wrapper) && read(wrapper, actual) && actual == service &&
        read(service, backend) && backend && read(backend, vtable) && read(vtable + 8, execute) &&
        execute >= image + 0x1000 && execute < image + 0x9500000;
}

static bool query_live_rows(void* backend, const char* table, const char* idField,
                           const char* valueField, bool nationNames,
                           CountryRow* rows, size_t capacity, size_t& size) {
    uint64_t query[7]{}, result = 0;
    bool queryReady = false, resultReady = false, okay = false;
    size = 0;
    __try {
        __try {
            ((void* (__fastcall*)(void*, int, const char*))(image + 0x445a2f0))(query, 1, table);
            queryReady = true;
            ((void* (__fastcall*)(void*))(image + 0x5cc32f0))(&result); resultReady = true;
            uintptr_t vtable = 0, execute = 0;
            if (read((uintptr_t)backend, vtable) && read(vtable + 8, execute) && execute >= image && execute < image + 0x9500000) {
                ((void (__fastcall*)(void*, void*, void*))execute)(backend, query, &result);
                const int count = ((int (__fastcall*)(void*))(image + 0x4468cf0))(&result);
                if (count >= 0 && (size_t)count <= capacity) {
                    for (int i = 0; i < count; ++i) {
                        rows[i].id = ((int (__fastcall*)(void*, int, const char*))(image + 0x4462ab0))(&result, i, idField);
                        if (nationNames) {
                            const char* name = ((const char* (__fastcall*)(void*, int, const char*))(image + 0x511b070))(&result, i, valueField);
                            rows[i].value = ultra_brazil_country(name) ? 1 : 0;
                        } else rows[i].value = ((int (__fastcall*)(void*, int, const char*))(image + 0x4462ab0))(&result, i, valueField);
                    }
                    size = (size_t)count; okay = true;
                }
            }
        } __finally {
            if (resultReady) ((void (__fastcall*)(void*))(image + 0x445e130))(&result);
            if (queryReady) ((void (__fastcall*)(void*))(image + 0x445e020))(query);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { okay = false; size = 0; }
    return okay;
}

static bool native_country_catalog(uintptr_t backend, std::unordered_map<int, bool>& clubs) {
    std::vector<CountryRow> rows(65535);
    std::unordered_map<int, bool> nations, leagues;
    size_t count = 0;
    if (!query_live_rows((void*)backend, "nations", "nationid", "nationname", true, rows.data(), rows.size(), count) || !count) return false;
    for (size_t i = 0; i < count; ++i) nations[rows[i].id] = rows[i].value != 0;
    if (!query_live_rows((void*)backend, "leagues", "leagueid", "countryid", false, rows.data(), rows.size(), count) || !count) return false;
    for (size_t i = 0; i < count; ++i) leagues[rows[i].id] = nations[rows[i].value];
    if (!query_live_rows((void*)backend, "leagueteamlinks", "teamid", "leagueid", false, rows.data(), rows.size(), count) || !count) return false;
    for (size_t i = 0; i < count; ++i) clubs[rows[i].id] = clubs[rows[i].id] || leagues[rows[i].value];
    // Some databases omit this table; league nationality still remains usable.
    if (query_live_rows((void*)backend, "rowteamnationlinks", "teamid", "nationid", false, rows.data(), rows.size(), count))
        for (size_t i = 0; i < count; ++i) clubs[rows[i].id] = clubs[rows[i].id] || nations[rows[i].value];
    return true;
}

static void refresh_live_countries(bool refreshLoaded = false) {
    AcquireSRWLockExclusive(&countryRefreshLock);
    uintptr_t backend = 0;
    current_country_backend(backend);
    // Keep the installed snapshot for the session. A newly captured backend
    // replaces it at scene preparation; loaded careers can refresh per scene.
    if (countrySnapshotReady && backend == countrySnapshotBackend && (!backend || !refreshLoaded)) {
        ReleaseSRWLockExclusive(&countryRefreshLock); return;
    }
    std::unordered_map<int, bool> clubs;
    bool okay = backend && native_country_catalog(backend, clubs);
    const char* source = "loaded_database";
    if (!okay) {
        clubs.clear(); source = "installed_database";
        okay = installed_country_db::load(clubs);
    }
    unsigned eligible = 0;
    if (okay) for (const auto& row : clubs) if (row.second) ++eligible;
    AcquireSRWLockExclusive(&countryLock);
    liveClubCountries.clear(); countrySnapshotReady = okay; countrySnapshotBackend = backend;
    if (okay) liveClubCountries.swap(clubs);
    ReleaseSRWLockExclusive(&countryLock);
    log_event("country_db status=%s source=%s backend=%p brazilian_clubs=%u fixed_club_ids=0",
              okay ? "loaded" : "unavailable_scope_original", source, (void*)backend, eligible);
    ReleaseSRWLockExclusive(&countryRefreshLock);
}

static bool live_brazil_club(int club) {
    AcquireSRWLockShared(&countryLock);
    const auto found = liveClubCountries.find(club);
    const bool result = countrySnapshotReady && found != liveClubCountries.end() && found->second;
    ReleaseSRWLockShared(&countryLock); return result;
}

static std::string live_country_lua() {
    std::string text = "FIFA16_ULTRA_LIVE_BRAZIL={";
    AcquireSRWLockShared(&countryLock);
    for (const auto& row : liveClubCountries) if (row.second) text += "[" + std::to_string(row.first) + "]=true,";
    ReleaseSRWLockShared(&countryLock);
    return text + "};";
}
