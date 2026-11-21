#include "play_direction.h"

typedef unsigned int u32;
typedef unsigned char u8;

extern u32 pt_length(const u8 *, u32);
static volatile u8 track_directions[6];
static volatile u8 pattern_request;
static u8 was_track_mode;
static struct playback_direction a_state[6];
u8 a_pattern_running;
static u32 a_pattern_id;

u32 midi12_cycle_direction(u32 track_mode, u32 lane) {
    u32 mode = track_mode ? track_directions[lane] : pattern_request & 3u;
    if (++mode == 3) mode = PLAY_FORWARD;
    if (track_mode) track_directions[lane] = mode;
    /* Publish the shared direction and its anchor in a single byte. */
    pattern_request = (lane << 2) | mode;
    return mode;
}

u32 midi12_direction_page_end(u32 len, u32 width, u32 step) {
    u32 page = step & ~15u;
    u32 end = page + width;
    return (end < len ? end : len) - 1;
}

u32 midi12_direction_next(struct playback_direction *state, u32 len, u32 width, u32 step) {
    u32 last = midi12_direction_page_end(len, width, len - 1);
    if (!last) return PLAY_WRAPPED;
    u32 next = step + 1;
    if ((next & 15) >= width) next = (next + 15) & ~15u;
    u32 previous = (step & 15) ? step - 1 : step ? step - 16 + width - 1 : last;

    if (state->mode == PLAY_FORWARD) return next < len ? next : PLAY_WRAPPED;
    if (state->mode == PLAY_REVERSE) return previous | (step ? 0 : PLAY_WRAPPED);
    if (step == last) state->descending = 1;
    if (!step) state->descending = 0;
    return state->descending ? previous | (previous ? 0 : PLAY_WRAPPED) : next;
}

static u32 direction_first(u32 mode, struct playback_direction *state,
                           u32 len, u32 width, u32 next) {
    if (mode == state->mode) return next;
    if (mode == PLAY_PING_PONG) state->descending = state->mode == PLAY_REVERSE;
    state->mode = mode;
    if (!state->last) return mode == PLAY_REVERSE ? midi12_direction_page_end(len, width, len - 1) : 0;
    u32 step = state->last - 1;
    if (step >= len) step = len - 1;
    if ((step & 15) >= width) step = midi12_direction_page_end(len, width, step);
    return midi12_direction_next(state, len, width, step) & 63;
}

static u32 a_length(const u8 *pattern, u32 lane) {
    u32 offset = pattern[30667] == 1 ? 713 + 722 * lane : 30662;
    return (u32)pattern[offset] * 256 + pattern[offset + 1];
}

void midi12_a_direction_prepare(void) {
    /* Count-in can visit this hook before the stock start resets its cursors. */
    if (*(volatile u32 *)0x40a7883c != 1) return;
    const u8 *pattern = *(const u8 *volatile *)0x40a7887c;
    if (!pattern) return;
    volatile u8 *next = (volatile u8 *)0x40a78860;
    /* The scheduler can replace its audio buffer while playing the same slot. */
    u32 id = pattern[30709];
    u32 changed = !a_pattern_running || id != a_pattern_id;
    a_pattern_running = 1;
    a_pattern_id = id;
    u32 track_mode = pattern[30667] == 1;
    u32 scope_changed = track_mode != was_track_mode;
    was_track_mode = track_mode;
    if (changed) {
        for (u32 lane = 0; lane < 6; ++lane)
            a_state[lane] = (struct playback_direction){0};
    }

    if (!track_mode) {
        u32 request = pattern_request;
        u32 mode = request & 3u;
        if (!scope_changed && a_state[0].mode == mode) return;
        u32 lane = request >> 2;
        u32 len = a_length(pattern, lane);
        if (!len || len > 64) return;
        struct playback_direction state = a_state[lane];
        u32 step = direction_first(mode, &state, len, pt_length(pattern + 30642, lane), next[lane]);
        for (u32 i = 0; i < 6; ++i) {
            a_state[i] = state;
            next[i] = step;
        }
        return;
    }

    for (u32 lane = 0; lane < 6; ++lane) {
        struct playback_direction *state = &a_state[lane];
        u32 mode = track_directions[lane];
        if (state->mode == mode) continue;
        u32 len = a_length(pattern, lane);
        if (!len || len > 64) continue;
        next[lane] = direction_first(mode, state, len, pt_length(pattern + 30642, lane), next[lane]);
    }
}

/* The native pattern loop writes its default restart step after advancing
 * the lanes. Keep the step we already chose when the same slot loops. */
u32 midi12_a_loop_step(u32 lane, u32 next) {
    const u8 *pattern = *(const u8 *volatile *)0x40a7887c;
    if (lane >= 6 || !a_pattern_running || !pattern ||
        *(volatile u32 *)0x40a7883c != 1 || pattern[30709] != a_pattern_id ||
        pattern[30667] == 1 || !a_state[lane].mode)
        return 0;
    u32 len = a_length(pattern, lane);
    if (next >= len) return 0;
    return next;
}

u32 midi12_a_direction_advance(const u8 *pattern, u32 current, u32 lane) {
    current &= 255;
    if (lane >= 6 || current >= 64) return ~0u;
    struct playback_direction *state = &a_state[lane];
    state->last = current + 1;
    u32 result = ~0u;
    u32 len = 0;
    u32 width = 0;
    if (state->mode) {
        len = a_length(pattern, lane);
        if (len && len <= 64 && current < len) {
            width = pt_length(pattern + 30642, lane);
            result = midi12_direction_next(state, len, width, current);
        }
    }
    return result;
}

