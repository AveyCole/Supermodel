    .text
    .globl private_direction_keys,private_direction_transport

/* Exact controller ABI: second stack argument is the native key event. */
private_direction_keys:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l 24(%sp),-(%sp)
    jsr private_direction_key
    addq.l #4,%sp
    tst.l %d0
    beq 1f
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    moveq #1,%d0
    rts
1:  movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    jmp direction_original_keys

/* Reset on stop, including MIDI Stop, before calling the existing warp gate. */
private_direction_transport:
    tst.l 0x40a7883c
    bne 2f
    tst.l 0x40a78874
    bne 2f
    clr.b a_pattern_running
2:  jmp direction_original_transport


    .globl private_direction_start
/* Native transport just cleared all six cursors. Replay the overwritten
 * word/long clears before running the normal transport start sequence. */
private_direction_start:
    clr.b a_pattern_running
    clr.w %d0
    clr.l 0x40a78840
    jmp 0x40055036
