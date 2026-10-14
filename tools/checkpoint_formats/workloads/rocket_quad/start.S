/* All four harts execute this entry, with separate stacks and no host runtime. */
    .section .text.init,"ax"
    .globl _start
_start:
    csrr a0, mhartid
    li t0, 4
    bgeu a0, t0, .Lpark
    csrw mie, zero
    csrw mstatus, zero
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    la sp, stacks_end
    slli t0, a0, 12
    sub sp, sp, t0
    bnez a0, .Lwait
    la t0, __bss_start
    la t1, __bss_end
.Lzero:
    bgeu t0, t1, .Lready
    sd zero, 0(t0)
    addi t0, t0, 8
    j .Lzero
.Lready:
    fence rw, rw
    la t0, boot_ready
    li t1, 1
    sd t1, 0(t0)
.Lwait:
    la t0, boot_ready
    ld t1, 0(t0)
    beqz t1, .Lwait
    fence r, rw
    call workload_main
.Lpark:
    wfi
    j .Lpark

    .section .data,"aw"
    .balign 64
boot_ready:
    .quad 0

    .section .bss.stacks,"aw",@nobits
    .balign 64
    .space 4 * 4096
stacks_end:
