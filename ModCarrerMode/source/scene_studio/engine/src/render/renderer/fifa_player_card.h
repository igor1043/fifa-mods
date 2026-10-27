#pragma once

#include "imgui.h"
#include <algorithm>
#include <cmath>
#include <string>

/* Reusable MyClub-style player tile for native screens. The face texture is
 * expected to come from fifa_player::Renderer (transparent, cropped 3D model);
 * this component only owns presentation and never loads assets on the draw
 * thread. */
namespace fifa_player_card {
struct Data {
    int player_id = 0;
    int team_id = 0;
    int overall = -1;
    const char *position = "-";
    const char *name = "";
    /* Raw club primary RGB. The card softens it over a neutral shadow; the
     * face texture is rendered independently and is never multiplied by it. */
    unsigned primary_color = 0x07558d;
};

inline ImU32 mix(unsigned a, unsigned b, float t, int alpha = 255) {
    t = std::max(0.f, std::min(1.f, t));
    auto channel = [t](unsigned x, unsigned y) {
        return (int)(x * (1.f - t) + y * t + .5f);
    };
    return IM_COL32(channel((a >> 16) & 255, (b >> 16) & 255),
        channel((a >> 8) & 255, (b >> 8) & 255), channel(a & 255, b & 255), alpha);
}

inline std::string fitted_name(const char *name, ImFont *font, float font_size,
    float width) {
    std::string result = name ? name : "";
    if (result.empty() || !font || font->CalcTextSizeA(font_size, FLT_MAX, 0,
        result.c_str()).x <= width) return result;
    /* Three ASCII dots also work with the game's smaller custom font atlases,
     * which do not always include U+2026. */
    const std::string ellipsis = "...";
    while (!result.empty()) {
        size_t start = result.size() - 1;
        while (start && (static_cast<unsigned char>(result[start]) & 0xc0) == 0x80) --start;
        result.resize(start);
        std::string candidate = result + ellipsis;
        if (font->CalcTextSizeA(font_size, FLT_MAX, 0, candidate.c_str()).x <= width)
            return candidate;
    }
    return font->CalcTextSizeA(font_size, FLT_MAX, 0, ellipsis.c_str()).x <= width
        ? ellipsis : std::string();
}

inline void draw(ImDrawList *list, ImVec2 at, ImVec2 size, const Data &player,
    ImTextureID face, ImTextureID crest, ImFont *font = nullptr) {
    if (!list || size.x < 48.f || size.y < 64.f) return;
    if (!font) font = ImGui::GetFont();
    const float scale = std::max(.62f, std::min(1.65f, size.y / 320.f));
    const float radius = std::min(size.x, size.y) * .065f;
    const ImVec2 end(at.x + size.x, at.y + size.y);
    const unsigned primary = player.primary_color & 0xffffff;
    const unsigned dark = 0x071321;
    const unsigned light = 0xffffff;
    /* Keep the actual club hue. Only blend it toward the neutral card shadow
     * to lower contrast; do not introduce another hue into the team palette. */

    list->AddRectFilled(at, end, mix(primary, dark, .70f), radius);
    list->PushClipRect(at, end, true);

    /* Vertical team-colour treatment, drawn in strips so it works with the
     * game's existing ImGui/DX11 path and introduces no shader dependency. */
    constexpr int bands = 28;
    for (int i = 0; i < bands; ++i) {
        float t0 = (float)i / bands, t1 = (float)(i + 1) / bands;
        float shade = .52f + t0 * .22f;
        ImDrawFlags corners = i == 0 ? ImDrawFlags_RoundCornersTop :
            i == bands - 1 ? ImDrawFlags_RoundCornersBottom : ImDrawFlags_RoundCornersNone;
        list->AddRectFilled(ImVec2(at.x, at.y + size.y * t0),
            ImVec2(end.x, at.y + size.y * t1 + .6f), mix(primary, dark, shade), radius,
            corners);
    }

    /* Quiet geometric engraving in the club colour, like a broadcast card. */
    ImU32 ornament = mix(primary, light, .48f, 16);
    float ox = at.x + size.x * .78f, oy = at.y + size.y * .36f;
    for (int i = 0; i < 4; ++i) {
        float r = size.x * (.10f + i * .075f);
        list->AddCircle(ImVec2(ox, oy), r, ornament, 48, std::max(1.f, scale));
    }
    list->AddLine(ImVec2(at.x + size.x * .57f, at.y + size.y * .08f),
        ImVec2(end.x - size.x * .05f, at.y + size.y * .48f), ornament, scale * 1.4f);
    list->AddLine(ImVec2(at.x + size.x * .48f, at.y + size.y * .12f),
        ImVec2(end.x - size.x * .11f, at.y + size.y * .51f), ornament, scale);

    /* Native transparent 3D bust: team-kit details remain supplied by FIFA. */
    if (face) {
        ImVec2 face_min(at.x + size.x * .02f, at.y + size.y * .16f);
        ImVec2 face_max(at.x + size.x * .98f, at.y + size.y * .93f);
        list->AddImage(face, face_min, face_max, ImVec2(0,0), ImVec2(1,1), IM_COL32_WHITE);
    } else {
        ImU32 ghost = IM_COL32(226, 236, 244, 140);
        list->AddCircleFilled(ImVec2(at.x + size.x * .5f, at.y + size.y * .48f),
            size.x * .17f, ghost);
        list->AddRectFilled(ImVec2(at.x + size.x * .25f, at.y + size.y * .64f),
            ImVec2(at.x + size.x * .75f, at.y + size.y * .96f), ghost,
            size.x * .12f, ImDrawFlags_RoundCornersTop);
    }

    /* Dark fade behind the name. Alpha strips avoid depending on a custom
     * gradient shader, so production screens and offline captures match. */
    const float fade_top = at.y + size.y * .73f;
    list->AddRectFilledMultiColor(ImVec2(at.x, fade_top), end,
        IM_COL32(4, 10, 19, 0), IM_COL32(4, 10, 19, 0),
        IM_COL32(4, 10, 19, 238), IM_COL32(4, 10, 19, 238));

    const float pad = size.x * .085f;
    /* The reference tile is about 96x123. Sizes below are proportional to
     * its 0.78:1 aspect, so scaling the card scales every label uniformly. */
    const float overall_size = std::max(7.f, size.y * .18f);
    const std::string rating = player.overall >= 0 && player.overall <= 99
        ? std::to_string(player.overall) : "-";
    const float overall_y = at.y + size.y * .05f;
    list->AddText(font, overall_size, ImVec2(at.x + pad, overall_y),
        IM_COL32(255, 255, 255, 255), rating.c_str());
    const char *position = player.position && player.position[0] ? player.position : "-";
    list->AddText(font, std::max(6.f, size.y * .095f),
        ImVec2(at.x + pad, overall_y + overall_size + size.y * .01f),
        IM_COL32(230, 239, 247, 242), position);

    const float name_size = std::max(7.f, size.y * .12f);
    const float name_y = at.y + size.y * .82f;
    const float logo_size = size.y * .13f;
    const float name_width = size.x - pad * 2.f - (crest ? logo_size + size.x * .035f : 0.f);
    std::string name = fitted_name(player.name, font, name_size, name_width);
    list->AddText(font, name_size, ImVec2(at.x + pad, name_y),
        IM_COL32(255, 255, 255, 255), name.c_str());
    if (crest) {
        ImVec2 logo_min(end.x - pad - logo_size, at.y + size.y * .81f);
        list->AddImage(crest, logo_min, ImVec2(logo_min.x + logo_size, logo_min.y + logo_size));
    }

    list->PopClipRect();
    list->AddRect(at, end, IM_COL32(255, 255, 255, 38), radius, 0, std::max(1.f, scale));
}
} // namespace fifa_player_card
