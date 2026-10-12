#include <assert.h>
#include <stdio.h>
#include "crowd_policy.h"
int main() {
    UltraConfig c;
    c.replacePercent = 100;
    unsigned primary = 0, secondary = 0;
    for (uint32_t i = 0; i < 100000; ++i) {
        const uint32_t original = ultra_hash(i);
        const uint32_t after = ultra_flags(original, i, c);
        assert((original & ~0x00380000U) == (after & ~0x00380000U));
        if (((original >> 22) & 3U) == 2U) { assert(original == after); continue; }
        assert(after & 0x80000U);
        assert(((after >> 20) & 1U) == ((original & 0x08000000U) ? 0U : 1U));
        if (after & 0x00200000U) ++secondary; else ++primary;
        assert(after == ultra_flags(original, i, c));
    }
    assert(primary * 100U / (primary + secondary) >= 87);
    assert(primary * 100U / (primary + secondary) <= 89);
    assert(ultra_third_count(1200, c) == 300);
    assert(ultra_goalkeeper_count(1200, c) == 100);
    for (unsigned n = 0; n < 5000; ++n) assert(ultra_third_count(n, c) + ultra_goalkeeper_count(n, c) <= n);
    c.replacePercent = 96;
    unsigned selected = 0;
    for (uint32_t i = 0; i < 100000; ++i) if (ultra_flags(0, i, c) & 0x80000U) ++selected;
    assert(selected >= 95000 && selected <= 97000);
    c.replacePercent = 0;
    for (uint32_t i = 0; i < 1000; ++i) assert(ultra_flags(i, i, c) == i);
    c.kit2Percent = c.kit3Percent = c.goalkeeperPercent = 0; c.kit1Percent = 100;
    assert(ultra_third_count(2000, c) == 0);
    assert(ultra_goalkeeper_count(2000, c) == 0);
    printf("PASS: seat bits, affiliation, deterministic mix, zero replacement and kit split. Primary=%u Secondary=%u\n", primary, secondary);
}
