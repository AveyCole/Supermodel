typedef unsigned int u32;
extern void fx_notice(const char *);
extern volatile u32 control_track_clean, control_track_second, control_track_armed;
extern volatile u32 control_back_clean, control_back_armed;
extern u32 midi12_cycle_direction(u32, u32);
static u32 track_down, back_owned;

/* Read the same editable scale header as FUNC + PAGE. The audio copy may
 * still hold the previous scale mode until the sequencer publishes it. */
static u32 track_scale(u32 root) {
    u32 pattern = ((u32 (*)(u32))0x4000f208)(root);
    u32 header = pattern ? ((u32 (*)(u32))0x4000d0dc)(pattern) : 0;
    u32 table = header ? *(const u32 *)header : 0;
    if (table && *(const u32 *)(table + 40)) {
        const unsigned char *raw = (const unsigned char *)
            ((u32 (*)(u32))(*(const u32 *)(table + 40)))(header);
        if (raw) return raw[25] == 1;
    }
    const unsigned char *active = *(const unsigned char *volatile *)0x40a7887c;
    return active && active[30667] == 1;
}

u32 private_direction_key(const u32 *event) {
    if (!event) return 0;
    u32 key = event[3], flags = event[4];
    if (key == 12 && back_owned) {
        if (!(flags & 33)) back_owned = 0;
        return 1;
    }
    if (flags & 32) return 0;
    if (key == 2) track_down = flags & 1;
    if (key != 12 || (flags & 11) != 1) return 0;

    u32 (*pressed)(u32) = (void *)0x4007faf4;
    if (!(track_down || pressed(2)) || pressed(1) || pressed(13)) return 0;
    u32 root = ((u32 (*)(void))0x400cf866)();
    if (!root) return 0;
    u32 track = ((u32 (*)(u32))0x40012412)(root + 48);
    if (track >= 6) return 0;

    static const char *const labels[] = {"FORWARD", "REVERSE", "PING PONG"};
    back_owned = 1;
    control_track_clean = control_track_second = control_track_armed = 0;
    control_back_clean = control_back_armed = 0;
    static const char *const pattern_labels[] = {"PTN FORWARD", "PTN REVERSE", "PTN PING PONG"};
    u32 track_mode = track_scale(root);
    u32 direction = midi12_cycle_direction(track_mode, track);
    fx_notice(track_mode ? labels[direction] : pattern_labels[direction]);
    return 1;
}

