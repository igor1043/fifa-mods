struct PreviewRow {
    int player_id, team_id, number, position, age, overall;
    int head_type, head_class, hair_type, hair_color, skin_tone, skin_type;
    int facial_hair_type, facial_hair_color, shoe_type, shoe_design;
    int gender, height, weight, body_type;
    int eye_color, eyebrow, sideburns, sleeve_length, jersey_fit, jersey_style;
    int sock_length, short_style, glove_type;
    unsigned club_colors[3]; int club_colors_valid;
    int attributes[CLUB_PLAYER_ATTRIBUTE_COUNT];
    char name[128];
    int captain, squad_position, secondary_positions[3], secondary_positions_valid;
};
static_assert(sizeof(PreviewRow) == 420, "offline roster fixture ABI");

static ClubPlayerRow upgrade(const PreviewRow &old) {
    ClubPlayerRow row{};
    std::memcpy(&row, &old, offsetof(ClubPlayerRow, head_type));
    row.birthdate_raw = row.join_team_date_raw = row.career_date = -1;
    row.retiring = row.weekly_wage = -1;
    row.career_data_valid = 0;
    std::memcpy(reinterpret_cast<unsigned char*>(&row) + offsetof(ClubPlayerRow, head_type),
        reinterpret_cast<const unsigned char*>(&old) + offsetof(PreviewRow, head_type),
        sizeof(old) - offsetof(PreviewRow, head_type));
    return row;
}

static bool read_fixture(const fs::path &path, std::vector<ClubPlayerRow> &rows,
    int &team_id, unsigned colors[3], bool roster=false) {
    std::ifstream in(path, std::ios::binary);
    char magic[8] = {}, name[128] = {};
    uint32_t count = 0, team = 0, stride = 0;
    in.read(magic, 8); in.read(reinterpret_cast<char*>(&count), 4);
    in.read(reinterpret_cast<char*>(&team), 4); in.read(reinterpret_cast<char*>(&stride), 4);
    in.read(name, sizeof(name));
    if (!in || std::memcmp(magic, "C3DQA003", 8) || (roster?(count<1||count>100):count!=11) || !team ||
        stride != sizeof(PreviewRow)) return false;
    std::vector<PreviewRow> old(count);
    in.read(reinterpret_cast<char*>(old.data()), static_cast<std::streamsize>(old.size()*sizeof(old[0])));
    if (!in || in.peek() != std::char_traits<char>::eof()) return false;
    std::set<int> ids;
    for (const auto &item : old) {
        if (item.team_id != static_cast<int>(team) || item.player_id <= 0 ||
            item.height < 130 || item.height > 230 || item.squad_position < 0 || item.squad_position > (roster?99:27) ||
            !ids.insert(item.player_id).second) return false;
        rows.push_back(upgrade(item));
    }
    if (!old.front().club_colors_valid) return false;
    std::copy(std::begin(old.front().club_colors), std::end(old.front().club_colors), colors);
    team_id = static_cast<int>(team);
    return true;
}
