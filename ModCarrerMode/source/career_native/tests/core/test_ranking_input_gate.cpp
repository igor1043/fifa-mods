/* Test the real COM/IAT filtering with fake devices, without opening FIFA or
 * moving the desktop mouse. No game files or memory are touched. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
static UINT input_option = 1;
static int option_reads, invalid_option_reads;
static UINT WINAPI test_profile_int(LPCSTR section, LPCSTR key, INT fallback, LPCSTR path)
{
    ++option_reads;
    if (strcmp(section, "overlay") || strcmp(key, "enabled") || fallback != 1 ||
        !strstr(path, "\\ModCarrerMode\\") || !strstr(path, "ranking_overlay.ini"))
        ++invalid_option_reads;
    return input_option;
}
#define GetPrivateProfileIntA test_profile_int
#include "../../src/platform/input/ranking_input_gate.cpp"
#undef GetPrivateProfileIntA
#include <stdio.h>
static BOOL capture;
extern "C" BOOL mod_screen_captures_input(void) { return capture; }
static int failures;
static void check(bool ok, const char *label) { if (!ok) { ++failures; printf("FAIL: %s\n", label); } }
struct FakeDevice {
    void **table;
    std::vector<unsigned char> raw;
    std::vector<DIDEVICEOBJECTDATA> queue;
    LONG low, high;
    HRESULT state_result;
    DWORD received_flags;
};
static FakeDevice *chosen;
static HRESULT WINAPI create_device(void *, REFGUID, void **out, IUnknown *) { *out = chosen; return DI_OK; }
static HRESULT WINAPI read_state(void *object, DWORD size, void *out)
{
    FakeDevice *device = (FakeDevice *)object;
    if (FAILED(device->state_result)) return device->state_result;
    if (size != device->raw.size()) return DIERR_INVALIDPARAM;
    memcpy(out, device->raw.data(), size); return device->state_result;
}
static HRESULT WINAPI read_events(void *object, DWORD stride, DIDEVICEOBJECTDATA *out, DWORD *count, DWORD flags)
{
    FakeDevice *device = (FakeDevice *)object;
    device->received_flags = flags;
    DWORD n = *count;
    if (n > device->queue.size()) n = (DWORD)device->queue.size();
    if (out) for (DWORD i = 0; i < n; ++i) memcpy((unsigned char *)out + size_t(i) * stride, &device->queue[i], stride);
    *count = n;
    if (!(flags & DIGDD_PEEK)) device->queue.erase(device->queue.begin(), device->queue.begin() + n);
    return DI_OK;
}
static HRESULT WINAPI set_format(void *object, const DIDATAFORMAT *format)
{
    ((FakeDevice *)object)->raw.assign(format->dwDataSize, 0); return DI_OK;
}
static HRESULT WINAPI read_property(void *object, REFGUID, DIPROPHEADER *header)
{
    FakeDevice *device = (FakeDevice *)object;
    DIPROPRANGE *range = (DIPROPRANGE *)header;
    range->lMin = device->low; range->lMax = device->high; return DI_OK;
}
static void configure(FakeDevice &device, DIOBJECTDATAFORMAT *objects, DWORD count, DWORD size, DWORD flags)
{
    DIDATAFORMAT format = {sizeof(DIDATAFORMAT), sizeof(DIOBJECTDATAFORMAT), flags, size, count, objects};
    check(SUCCEEDED(((DataFormatFn)device.table[11])(&device, &format)), "native format is retained");
}
static void value(FakeDevice &device, DWORD offset, LONG number) { memcpy(device.raw.data() + offset, &number, sizeof(number)); }
static LONG long_at(const unsigned char *bytes, DWORD offset) { LONG number; memcpy(&number, bytes + offset, 4); return number; }
static DIDEVICEOBJECTDATA event(DWORD offset, DWORD data) { DIDEVICEOBJECTDATA value = {}; value.dwOfs = offset; value.dwData = data; return value; }
static HMODULE fake_image()
{
    unsigned char *base = (unsigned char *)VirtualAlloc(NULL, 0x2000, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base; dos->e_magic = IMAGE_DOS_SIGNATURE; dos->e_lfanew = 0x80;
    IMAGE_NT_HEADERS64 *nt = (IMAGE_NT_HEADERS64 *)(base + 0x80);
    nt->Signature = IMAGE_NT_SIGNATURE; nt->OptionalHeader.Magic = IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress = 0x400;
    IMAGE_IMPORT_DESCRIPTOR *descriptor = (IMAGE_IMPORT_DESCRIPTOR *)(base + 0x400);
    descriptor->Name = 0x600; descriptor->FirstThunk = 0x800; descriptor->OriginalFirstThunk = 0x900;
    memcpy(base + 0x600, "USER32.dll", 11);
    ((IMAGE_THUNK_DATA64 *)(base + 0x800))->u1.Function = (uintptr_t)GetCursorPos;
    ((IMAGE_THUNK_DATA64 *)(base + 0x900))->u1.AddressOfData = 0xA00;
    memcpy(base + 0xA02, "GetCursorPos", 13); return (HMODULE)base;
}
int main()
{
    static void *input_table[12] = {}, *device_vtable[32] = {};
    struct { void **table; } input = {input_table};
    input_table[3] = (void *)create_device;
    device_vtable[5] = (void *)read_property;
    device_vtable[9] = (void *)read_state; device_vtable[10] = (void *)read_events; device_vtable[11] = (void *)set_format;
    FakeDevice keyboard = {}, mouse = {}, joystick = {};
    keyboard.table = mouse.table = joystick.table = device_vtable;
    static const GUID iid = {0xBF798030,0x483A,0x4DA2,{0xAA,0x99,0x5D,0x64,0xED,0x36,0x97,0x00}};
    GUID unknown = {};
    input_option = 0;
    ranking_input_attach_directinput(&input, &iid);
    check(input_table[3] == (void *)create_device && g_inputs.empty() && g_devices.empty(),
        "disabled overlay leaves DirectInput unhooked, including before the worker starts");
    check(device_vtable[9] == (void *)read_state && device_vtable[10] == (void *)read_events &&
        device_vtable[11] == (void *)set_format, "disabled overlay leaves native device methods untouched");
    input_option = 1;
    ranking_input_attach_directinput(&input, &unknown);
    check(input_table[3] == (void *)create_device, "unknown interface is not changed");
    ranking_input_attach_directinput(&input, &iid);
    ranking_input_attach_directinput(&input, &iid);
    void *out;
    chosen = &keyboard;
    check(SUCCEEDED(((CreateDeviceFn)input_table[3])(&input, unknown, &out, NULL)) && out == &keyboard, "CreateDevice return/identity preserved");
    chosen = &mouse; ((CreateDeviceFn)input_table[3])(&input, unknown, &out, NULL);
    chosen = &joystick; ((CreateDeviceFn)input_table[3])(&input, unknown, &out, NULL);
    DIOBJECTDATAFORMAT keys[2] = {{NULL, 1, DIDFT_PSHBUTTON, 0}, {NULL, 72, DIDFT_PSHBUTTON, 0}};
    configure(keyboard, keys, 2, 256, DIDF_RELAXIS);
    keyboard.raw[1] = keyboard.raw[72] = 0x80;
    unsigned char state[256] = {};
    DeviceStateFn poll = (DeviceStateFn)device_vtable[9];
    check(SUCCEEDED(poll(&keyboard, 256, state)) && state[1] == 0x80 && state[72] == 0x80, "closed overlay passes keyboard unchanged");
    capture = TRUE; poll(&keyboard, 256, state);
    check(state[1] == 0 && state[72] == 0 && keyboard.raw[72] == 0x80, "captured keyboard is neutral; raw state remains available");
    capture = FALSE; poll(&keyboard, 256, state);
    check(state[1] == 0 && state[72] == 0, "closing key does not leak into the Hub");
    keyboard.raw[1] = keyboard.raw[72] = 0; poll(&keyboard, 256, state);
    keyboard.raw[72] = 0x80; poll(&keyboard, 256, state);
    check(state[72] == 0x80, "keyboard returns after physical release");
    keyboard.state_result = DIERR_INPUTLOST;
    check(poll(&keyboard, 256, state) == DIERR_INPUTLOST, "native input errors are preserved");
    keyboard.state_result = DI_OK;
    DIOBJECTDATAFORMAT mouse_objects[4] = {{NULL,0,DIDFT_RELAXIS,0},{NULL,4,DIDFT_RELAXIS,0},{NULL,8,DIDFT_RELAXIS,0},{NULL,12,DIDFT_PSHBUTTON,0}};
    configure(mouse, mouse_objects, 4, 16, DIDF_RELAXIS);
    value(mouse,0,123); value(mouse,4,-70); value(mouse,8,120); mouse.raw[12] = 0x80;
    capture = TRUE; poll(&mouse,16,state);
    check(!long_at(state,0) && !long_at(state,4) && !long_at(state,8) && state[12] == 0, "mouse axes, wheel and buttons are captured");
    DIOBJECTDATAFORMAT axes[4] = {{NULL,0,DIDFT_ABSAXIS,0},{NULL,4,DIDFT_ABSAXIS,0},{NULL,8,DIDFT_POV,0},{NULL,12,DIDFT_PSHBUTTON,0}};
    configure(joystick,axes,4,16,DIDF_ABSAXIS);
    joystick.low = -1000; joystick.high = 1000; value(joystick,0,900); value(joystick,4,-900); value(joystick,8,4500); joystick.raw[12] = 0x80;
    poll(&joystick,16,state);
    check(long_at(state,0) == 0 && long_at(state,4) == 0 && long_at(state,8) == -1 && state[12] == 0, "joystick neutral uses axis ranges and no POV direction");
    joystick.low = 0; joystick.high = 65535; poll(&joystick,16,state);
    check(long_at(state,0) == 32767, "unsigned joystick axes are centered, not zeroed");
    mouse.queue = {event(12,0x80),event(8,120)};
    DIDEVICEOBJECTDATA events[4] = {}; DWORD count = 4;
    DeviceDataFn buffered = (DeviceDataFn)device_vtable[10];
    buffered(&mouse,sizeof(events[0]),events,&count,DIGDD_PEEK);
    check(count == 0 && mouse.queue.empty() && mouse.received_flags == 0, "captured buffered peek drains events without delivering them");
    capture = FALSE; count = 4; buffered(&mouse,sizeof(events[0]),events,&count,0);
    check(count == 0, "hidden clicks cannot replay after closing");
    mouse.queue = {event(12,0x80),event(12,0),event(8,120)}; count = 4;
    buffered(&mouse,sizeof(events[0]),events,&count,0);
    check(count == 1 && events[0].dwOfs == 8, "held mouse button is quarantined until release; other events return");
    mouse.queue = {event(12,0x80)}; count = 4; buffered(&mouse,sizeof(events[0]),events,&count,0);
    check(count == 1, "new click works after release");
    HMODULE frontend = fake_image(), gameplay = fake_image();
    check(ranking_input_install_cursor_import(frontend) && ranking_input_install_cursor_import(gameplay), "cursor import is gated in each FIFA image");
    check(ranking_input_install_cursor_import(frontend), "cursor interception is idempotent");
    POINT anchor = {1234,2345}, position; LONGLONG packed; memcpy(&packed,&anchor,sizeof(packed));
    InterlockedExchange64(&g_cursor_position,packed); InterlockedExchange(&g_cursor_seen,1);
    capture = TRUE;
    if (gated_cursor_position(&position)) check(position.x == anchor.x && position.y == anchor.y, "game cursor is frozen while overlay reads the real cursor");
    capture = FALSE;
    POINT real;
    if (GetCursorPos(&real) && gated_cursor_position(&position)) check(position.x == real.x && position.y == real.y, "cursor passes through after closing");
    VirtualFree(frontend,0,MEM_RELEASE); VirtualFree(gameplay,0,MEM_RELEASE);
    check(option_reads >= 3 && !invalid_option_reads, "DirectInput uses the same startup overlay option and path policy");
    printf("Ranking exclusive input gate: %s (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
