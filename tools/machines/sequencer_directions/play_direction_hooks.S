    .text
    .globl midi12_direction_prepare_hook,midi12_direction_advance_hook

/* Run before the existing queue validator and the native step reads. */
midi12_direction_prepare_hook:
    lea -24(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.w %sr,%d0
    move.l %d0,16(%sp)
    jsr midi12_a_direction_prepare
    move.l midi12_direction_scheduler,%d0
    move.l %d0,20(%sp)
    move.w 18(%sp),%d0
    move.w %d0,%sr
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 20(%sp),%sp
    rts

/* D1 is the step just read, D2 the lane, A4 the native next-step byte. */
midi12_direction_advance_hook:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l 0x40a7887c,-(%sp)
    jsr midi12_a_direction_advance
    lea 12(%sp),%sp
    tst.l %d0
    bmi 1f
    move.b %d0,(%a4)
    btst #8,%d0
    beq 2f
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    /* The native conditional loop counter advances without clearing A4. */
    jmp 0x40055360
1:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    jmp pl_step_hook
2:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    jmp 0x40055368

    .globl midi12_direction_loop_hook
midi12_direction_loop_hook:
    move.w (%a2),%d1
    bne 3f
    lea -12(%sp),%sp
    movem.l %d0/%a0-%a1,(%sp)
    moveq #0,%d1
    move.b -119(%a0),%d1
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr midi12_a_loop_step
    addq.l #8,%sp
    move.l %d0,%d1
    movem.l (%sp),%d0/%a0-%a1
    lea 12(%sp),%sp
3:
    clr.b %d6
    move.b %d1,(%a3,%d0.l)
    jmp 0x400558be

    .data
    .balign 4
    .globl midi12_direction_scheduler
midi12_direction_scheduler: .long 0
