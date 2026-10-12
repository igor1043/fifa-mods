#pragma once
#include <stdint.h>

struct UltraConfig {
    unsigned replacePercent = 96;
    unsigned kit1Percent = 88;
    unsigned kit2Percent = 8;
    unsigned kit3Percent = 3;
    unsigned goalkeeperPercent = 1;
};

static inline uint32_t ultra_hash(uint32_t value) {
    value ^= value >> 16; value *= 0x7feb352dU;
    value ^= value >> 15; value *= 0x846ca68bU;
    return value ^ (value >> 16);
}

// Confirmed in native crowd buffer allocation at RVA 5cb9560:
// bit 19 selects normal/ultra, bits 20..21 select one of four prototypes.
// bits 22..23 represent seat state (2 = empty), bit 27 is home affiliation.
// Ultra prototype parity: 0/2 home, 1/3 away.
static inline uint32_t ultra_flags(uint32_t flags, uint32_t index, const UltraConfig& config) {
    if (((flags >> 22) & 3U) == 2U) return flags;
    if (ultra_hash(index ^ 0x164031U) % 100U >= config.replacePercent) return flags;
    const unsigned side = (flags & 0x08000000U) ? 0U : 1U;
    const unsigned secondary = ultra_hash(index ^ 0x160080U) % 100U >= config.kit1Percent ? 2U : 0U;
    return (flags & ~0x00380000U) | 0x00080000U | ((side + secondary) << 20);
}

static inline unsigned ultra_third_count(unsigned count, const UltraConfig& config) {
    const unsigned secondary = config.kit2Percent + config.kit3Percent + config.goalkeeperPercent;
    return secondary ? (unsigned)(((uint64_t)count * config.kit3Percent + secondary / 2U) / secondary) : 0U;
}

static inline unsigned ultra_goalkeeper_count(unsigned count, const UltraConfig& config) {
    const unsigned secondary = config.kit2Percent + config.kit3Percent + config.goalkeeperPercent;
    return secondary ? (unsigned)(((uint64_t)count * config.goalkeeperPercent + secondary / 2U) / secondary) : 0U;
}
