#ifndef FIFA16_CARD_REFRESH_SCOPE_H
#define FIFA16_CARD_REFRESH_SCOPE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef int (*CardScopeReadFn)(uintptr_t, void *, size_t);

/* The statistics owner outlives the Hub in readable memory. Its vtable and
 * registry therefore do not prove that replay is safe. Follow the same native
 * active-page chain as Server16, and only retain a Hub view for deferred work.
 * No FIFA callback, allocation, lock or save operation is performed here.
 */
static uintptr_t card_refresh_hub_view(uintptr_t image, CardScopeReadFn read)
{
    static const unsigned offsets[] = {232, 192, 136};
    static const char hub[] = "game/screens/fluxHub/FluxHub";
    uintptr_t node = 0, page = 0, check = 0;
    char name[128];
    size_t i;
    if (!image || !read || !read(image + 0x3809030U, &node, sizeof(node)))
        return 0;
    for (i = 0; i < sizeof(offsets) / sizeof(offsets[0]); ++i) {
        if (!node || !read(node + offsets[i], &node, sizeof(node))) return 0;
    }
    if (!node || !read(node + 472U, &page, sizeof(page)) || !page
        || !read(page, name, sizeof(name))
        || !memchr(name, 0, sizeof(name)) || strcmp(name, hub) != 0
        || !read(node + 472U, &check, sizeof(check)) || check != page)
        return 0;
    return node;
}
#endif
