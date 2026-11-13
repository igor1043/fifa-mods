#define FIFA_STARTUP_GATE_TEST
#include "frontend_startup_gate.h"
#include <assert.h>
#include <stdio.h>

typedef struct Fixture {
    uintptr_t base, pointers[5];
    char page[128];
    int fail_at, calls;
} Fixture;

static int read_fixture(void *context, uintptr_t address, void *out, size_t size)
{
    Fixture *f = context;
    uintptr_t expected[] = {f->base + 0x03809030U,
        f->pointers[0] + 0xE8, f->pointers[1] + 0xC0,
        f->pointers[2] + 0x88, f->pointers[3] + 0x1D8, f->pointers[4]};
    int call = f->calls++;
    if (call > 5 || call == f->fail_at || address != expected[call]) return 0;
    if (call < 5) {
        assert(size == sizeof(uintptr_t));
        memcpy(out, &f->pointers[call], size);
    } else {
        assert(size == sizeof(f->page));
        memcpy(out, f->page, size);
    }
    return 1;
}
static int ready(Fixture *f, int engine, int hooks)
{
    f->calls = 0;
    return fifa_frontend_startup_ready(read_fixture, f, f->base, engine, hooks);
}
int main(void)
{
    Fixture f = {0x140000000ULL,
        {0x100000, 0x200000, 0x300000, 0x400000, 0x500000},
        "game/screens/bootflow/LanguageSelect", -1, 0};
    size_t i;
    assert(ready(&f, 1, 1));
    assert(!ready(&f, 0, 1) && !f.calls);
    assert(!ready(&f, 1, 0) && !f.calls);
    for (i = 0; i < 6; ++i) {
        f.fail_at = (int)i;
        assert(!ready(&f, 1, 1));
    }
    f.fail_at = -1;
    for (i = 0; i < 5; ++i) {
        uintptr_t original = f.pointers[i];
        f.pointers[i] = 0;
        assert(!ready(&f, 1, 1));
        f.pointers[i] = original;
    }
    f.pointers[0] = UINTPTR_MAX;
    assert(!ready(&f, 1, 1));
    f.pointers[0] = 0x100000;
    strcpy(f.page, "game/screens/");
    assert(!ready(&f, 1, 1));
    strcpy(f.page, "game/screens/bootflow/LanguageSelect");
    ((unsigned char *)f.page)[20] = 0xFF;
    assert(!ready(&f, 1, 1));
    memset(f.page, 'x', sizeof(f.page));
    memcpy(f.page, "game/screens/", 13);
    assert(!ready(&f, 1, 1));
    strcpy(f.page, "game/screens/fluxHub/FluxHub");
    assert(ready(&f, 1, 1));
    puts("PASS: native frontend boundary, partial startup, invalid chains and resumed menu");
    return 0;
}
