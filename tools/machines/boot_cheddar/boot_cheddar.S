/* Portrait Redux, dévoilé de gauche à droite par la tâche de démarrage native.
 * La tâche dispose de 16 Kio de pile. Les deux images temporaires en prennent 2.
 */
    .equ TIMER_ADD,0x40002144
    .equ TIMER_DEL,0x40002200
    .equ SEM_WAIT,0x40001aca
    .equ SEM_POST,0x40001c80
    .equ SEM_TAKE,0x40001b3e
    .equ TICK_CB,0x400539b8
    .equ SEM_TICK,0x40a78618
    .equ SEM_DONE,0x40a78620
    .equ GET_BUF,0x4008e728
    .equ FLUSH,0x4008e622
    .equ BLANK,0x4008e6ba
    .section .text.boot_anim,"ax"
    .globl ba_task
ba_task:
    jsr BLANK
    pea 2.w
    pea TICK_CB
    jsr TIMER_ADD
    addql #8,%sp
    lea %sp@(-2048),%sp
    lea portrait(%pc),%a0
    moveal %sp,%a1
    lea %sp@(1024),%a2

/* Flux LZ : [0..127] = 1..128 littéraux, [128..255] = 3..130
 * octets copiés à la distance indiquée par l'octet suivant + 1. */
.Ldecode:
    moveq #0,%d0
    moveb %a0@+,%d0
    btst #7,%d0
    bne.s .Lmatch
.Lliteral:
    moveb %a0@+,%a1@+
    subql #1,%d0
    bpl.s .Lliteral
    bra.s .Lnext
.Lmatch:
    moveq #0,%d1
    moveb %a0@+,%d1
    notl %d1
    lea %a1@(%d1:l),%a3
    andil #127,%d0
    addql #2,%d0
.Lcopy:
    moveb %a3@+,%a1@+
    subql #1,%d0
    bpl.s .Lcopy
.Lnext:
    cmpal %a2,%a1
    blo.s .Ldecode

/* Transpose les huit pages en colonnes de huit octets pour GET_BUF. */
    moveq #0,%d0
.Lcolumn:
    lea %sp@(%d0:l),%a0
    moveq #8,%d1
.Lpage:
    moveb %a0@,%a1@+
    lea %a0@(128),%a0
    subql #1,%d1
    bne.s .Lpage
    addql #1,%d0
    cmpil #128,%d0
    blo.s .Lcolumn

    moveq #8,%d7
.Lframe:
    jsr GET_BUF
    moveal %d0,%a0
    moveal %a2,%a1
    movel %d7,%d0
.Lshow:
    movel %a1@+,%a0@+
    subql #1,%d0
    bne.s .Lshow
    movel #256,%d0
    subl %d7,%d0
    beq.s .Lpresent
    moveq #-1,%d1
.Lhide:
    movel %d1,%a0@+
    subql #1,%d0
    bne.s .Lhide
.Lpresent:
    bsr.s .Lwait
    jsr FLUSH
    addql #8,%d7
    cmpil #256,%d7
    bls.s .Lframe
    lea %sp@(2048),%sp

    moveq #58,%d7
.Lhold:
    bsr.s .Lwait
    subql #1,%d7
    bne.s .Lhold
    pea SEM_DONE
    jsr SEM_POST
    pea TICK_CB
    jsr TIMER_DEL
    addql #8,%sp
.Ldone:
    pea SEM_TICK
    jsr SEM_TAKE
    addql #4,%sp
    bra.s .Ldone
.Lwait:
    pea SEM_TICK
    jsr SEM_WAIT
    addql #4,%sp
    rts
    .section .rodata.boot_anim,"a"
portrait:
    .incbin "cheddar-portrait.lz"
