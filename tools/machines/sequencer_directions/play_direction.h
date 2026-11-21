enum { PLAY_FORWARD, PLAY_REVERSE, PLAY_PING_PONG };
enum { PLAY_WRAPPED = 0x100 };

struct playback_direction {
    unsigned char mode, descending, last;
};

unsigned midi12_cycle_direction(unsigned track_mode, unsigned lane);
unsigned midi12_direction_next(struct playback_direction *state, unsigned len, unsigned width,
                              unsigned step);
unsigned midi12_direction_page_end(unsigned len, unsigned width, unsigned step);
