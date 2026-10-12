#pragma once

// Read the installed T3DB at runtime when the frontend DB service is not yet
// available. Field/table identifiers and integer ranges come from its metadata;
// no club or country IDs are compiled into the DLL.
namespace installed_country_db {
struct Field { std::string name, shortName; int low = 0; };
struct Table { std::string name, shortName; std::vector<Field> fields; };
struct BinaryField { uint32_t kind = 0, bit = 0, depth = 0; int low = 0; bool found = false; };

static bool span(const std::vector<unsigned char>& data, size_t at, size_t length) {
    return at <= data.size() && length <= data.size() - at;
}
static bool u32(const std::vector<unsigned char>& data, size_t at, uint32_t& value) {
    if (!span(data, at, 4)) return false;
    memcpy(&value, data.data() + at, 4); return true;
}
static bool file_bytes(const std::wstring& path, size_t limit, std::vector<unsigned char>& data) {
    HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER length{}; FILETIME before{}, after{}; DWORD got = 0;
    bool okay = GetFileSizeEx(file, &length) && length.QuadPart > 0 &&
                (uint64_t)length.QuadPart <= limit && GetFileTime(file, nullptr, nullptr, &before);
    if (okay) {
        data.resize((size_t)length.QuadPart);
        okay = ReadFile(file, data.data(), (DWORD)data.size(), &got, nullptr) && got == data.size() &&
               GetFileTime(file, nullptr, nullptr, &after) && CompareFileTime(&before, &after) == 0;
    }
    CloseHandle(file); if (!okay) data.clear(); return okay;
}

static std::string attribute(const std::string& tag, const char* name) {
    // The metadata uses ordinary quoted ASCII attributes for these schema keys.
    // Walk complete attributes so a suffix (e.g. shortname) cannot match name.
    size_t at = tag.find_first_of(" \t\r\n");
    while (at != std::string::npos && at < tag.size()) {
        at = tag.find_first_not_of(" \t\r\n", at);
        if (at == std::string::npos || tag[at] == '/' || tag[at] == '>') break;
        const size_t end = tag.find_first_of("= \t\r\n", at);
        if (end == std::string::npos) break;
        size_t equal = tag.find_first_not_of(" \t\r\n", end);
        if (equal == std::string::npos || tag[equal] != '=') break;
        const size_t quote = tag.find_first_not_of(" \t\r\n", equal + 1);
        if (quote == std::string::npos || (tag[quote] != '"' && tag[quote] != '\'')) break;
        const size_t close = tag.find(tag[quote], quote + 1);
        if (close == std::string::npos) break;
        if (tag.compare(at, end - at, name) == 0) return tag.substr(quote + 1, close - quote - 1);
        at = close + 1;
    }
    return {};
}

static bool schema(const std::string& xml, const char* name, const char* idField, const char* valueField, Table& out) {
    size_t at = 0;
    while ((at = xml.find("<table ", at)) != std::string::npos) {
        const size_t tagEnd = xml.find('>', at), tableEnd = xml.find("</table>", at);
        if (tagEnd == std::string::npos || tableEnd == std::string::npos) return false;
        const std::string tag = xml.substr(at, tagEnd - at + 1);
        at = tableEnd + 8;
        if (attribute(tag, "name") != name) continue;
        out.name = name; out.shortName = attribute(tag, "shortname");
        if (out.shortName.size() != 4) return false;
        size_t fieldAt = tagEnd + 1;
        while ((fieldAt = xml.find("<field ", fieldAt)) != std::string::npos && fieldAt < tableEnd) {
            const size_t end = xml.find('>', fieldAt);
            if (end == std::string::npos || end > tableEnd) return false;
            const std::string fieldTag = xml.substr(fieldAt, end - fieldAt + 1);
            fieldAt = end + 1;
            const std::string fieldName = attribute(fieldTag, "name");
            if (fieldName != idField && fieldName != valueField) continue;
            Field field; field.name = fieldName; field.shortName = attribute(fieldTag, "shortname");
            const std::string low = attribute(fieldTag, "rangelow");
            char* rest = nullptr; const long long value = strtoll(low.c_str(), &rest, 10);
            if (field.shortName.size() != 4 || low.empty() || !rest || *rest || value < INT_MIN || value > INT_MAX) return false;
            field.low = (int)value; out.fields.push_back(field);
        }
        return out.fields.size() == 2;
    }
    return false;
}

static bool integer(const std::vector<unsigned char>& data, size_t record, uint32_t stride,
                    const BinaryField& field, int& value) {
    if ((field.kind != 3 && field.kind != 4) || !field.depth || field.depth > 32 ||
        (uint64_t)field.bit + field.depth > (uint64_t)stride * 8 || !span(data, record, stride)) return false;
    uint64_t raw = 0;
    for (uint32_t bit = 0; bit < field.depth; ++bit)
        raw |= (uint64_t)((data[record + (field.bit + bit) / 8] >> ((field.bit + bit) % 8)) & 1) << bit;
    const int64_t result = (int64_t)raw + field.low;
    if (result < INT_MIN || result > INT_MAX) return false;
    value = (int)result; return true;
}

static bool string_value(const std::vector<unsigned char>& data, size_t record, uint32_t stride,
                         size_t block, uint32_t length, const BinaryField& field, std::string& value) {
    value.clear();
    if (field.bit % 8 || (uint64_t)field.bit + field.depth > (uint64_t)stride * 8) return false;
    if (field.kind == 0) {
        if (field.depth % 8 || !span(data, record + field.bit / 8, field.depth / 8)) return false;
        const char* text = (const char*)data.data() + record + field.bit / 8;
        size_t count = 0; while (count < field.depth / 8 && text[count]) ++count;
        value.assign(text, count); return true;
    }
    if ((field.kind != 13 && field.kind != 14) || field.depth != 32 || !span(data, block, length)) return false;
    uint32_t pointer = 0; if (!u32(data, record + field.bit / 8, pointer)) return false;
    if (pointer == UINT32_MAX) return true;
    const unsigned prefix = field.kind == 14 ? 2U : 1U;
    if (pointer > length || prefix > length - pointer) return false;
    unsigned count = data[block + pointer];
    if (prefix == 2) count = count * 256 + data[block + pointer + 1];
    if (count > 4096) return false;
    size_t cursor = ((size_t)pointer + prefix) * 8;
    for (unsigned i = 0; i < count; ++i) {
        unsigned node = 0; bool decoded = false;
        for (unsigned depth = 0; depth < 32; ++depth) {
            if (cursor >= (size_t)length * 8 || node * 4U + 3U >= pointer) return false;
            const unsigned side = (data[block + cursor / 8] >> (7 - cursor % 8)) & 1U; ++cursor;
            const size_t childAt = block + node * 4U + side * 2U;
            const unsigned child = data[childAt];
            if (child) node = child;
            else { value.push_back((char)data[childAt + 1]); decoded = true; break; }
        }
        if (!decoded) return false;
    }
    return true;
}

static bool table_rows(const std::vector<unsigned char>& data, const Table& table, bool names,
                       std::vector<CountryRow>& rows) {
    rows.clear(); uint32_t tables = 0;
    if (data.size() < 28 || memcmp(data.data(), "DB\0\x08", 4) || !u32(data, 16, tables) ||
        !tables || tables > 4096 || !span(data, 24, (size_t)tables * 8 + 4)) return false;
    const size_t base = 28 + (size_t)tables * 8;
    for (uint32_t i = 0; i < tables; ++i) {
        const size_t directory = 24 + (size_t)i * 8;
        if (memcmp(data.data() + directory, table.shortName.data(), 4)) continue;
        uint32_t relative = 0, stride = 0, length = 0;
        if (!u32(data, directory + 4, relative)) return false;
        const size_t start = base + relative;
        if (!span(data, start, 36) || !u32(data, start + 4, stride) || !stride ||
            !u32(data, start + 12, length)) return false;
        uint16_t allocated = 0, count = 0;
        memcpy(&allocated, data.data() + start + 16, 2); memcpy(&count, data.data() + start + 18, 2);
        const unsigned fields = data[start + 24];
        const size_t records = start + 36 + (size_t)fields * 16;
        const size_t block = records + (size_t)allocated * stride;
        if (count > allocated || !span(data, start + 36, (size_t)fields * 16) ||
            !span(data, records, (size_t)allocated * stride) || !span(data, block, length)) return false;
        BinaryField selected[2]{};
        for (unsigned j = 0; j < fields; ++j) {
            const size_t at = start + 36 + (size_t)j * 16;
            for (unsigned k = 0; k < 2; ++k) {
                if (memcmp(data.data() + at + 8, table.fields[k].shortName.data(), 4)) continue;
                selected[k].found = u32(data, at, selected[k].kind) && u32(data, at + 4, selected[k].bit) &&
                                    u32(data, at + 12, selected[k].depth);
                selected[k].low = table.fields[k].low;
            }
        }
        if (!selected[0].found || !selected[1].found) return false;
        // Metadata order is not significant.
        const unsigned idIndex = table.fields[0].name == (names ? "nationid" : table.name == "leagues" ? "leagueid" : "teamid") ? 0U : 1U;
        const unsigned valueIndex = idIndex ^ 1U;
        rows.reserve(count);
        for (unsigned j = 0; j < count; ++j) {
            const size_t record = records + (size_t)j * stride;
            CountryRow row{};
            if (!integer(data, record, stride, selected[idIndex], row.id)) return false;
            if (names) {
                std::string name;
                if (!string_value(data, record, stride, block, length, selected[valueIndex], name)) return false;
                row.value = ultra_brazil_country(name.c_str()) ? 1 : 0;
            } else if (!integer(data, record, stride, selected[valueIndex], row.value)) return false;
            rows.push_back(row);
        }
        return true;
    }
    return false;
}

static bool load(std::unordered_map<int, bool>& clubs) {
    wchar_t exe[32768]{}; const DWORD length = GetModuleFileNameW(nullptr, exe, (DWORD)_countof(exe));
    if (!length || length >= _countof(exe)) return false;
    std::wstring directory(exe, length); const size_t slash = directory.find_last_of(L"\\/");
    if (slash == std::wstring::npos) return false;
    directory.resize(slash + 1); directory += L"data\\db\\";
    std::vector<unsigned char> data, metadata;
    if (!file_bytes(directory + L"fifa_ng_db.db", 128 * 1024 * 1024, data) ||
        !file_bytes(directory + L"fifa_ng_db-meta.xml", 16 * 1024 * 1024, metadata)) return false;
    const std::string xml(metadata.begin(), metadata.end());
    const char* tables[] = {"nations", "leagues", "leagueteamlinks", "rowteamnationlinks"};
    const char* ids[] = {"nationid", "leagueid", "teamid", "teamid"};
    const char* values[] = {"nationname", "countryid", "leagueid", "nationid"};
    std::unordered_map<int, bool> nations, leagues;
    std::vector<CountryRow> rows;
    for (unsigned index = 0; index < 4; ++index) {
        Table table;
        if (!schema(xml, tables[index], ids[index], values[index], table) ||
            !table_rows(data, table, index == 0, rows)) {
            if (index == 3) continue; // Optional Rest of World association.
            return false;
        }
        if (index < 3 && rows.empty()) return false;
        for (const CountryRow& row : rows) {
            if (index == 0) nations[row.id] = row.value != 0;
            else if (index == 1) leagues[row.id] = nations[row.value];
            else if (index == 2) clubs[row.id] = clubs[row.id] || leagues[row.value];
            else clubs[row.id] = clubs[row.id] || nations[row.value];
        }
    }
    return true;
}
} // namespace installed_country_db
