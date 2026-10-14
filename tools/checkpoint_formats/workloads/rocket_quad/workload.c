/* Deterministic, self-checking RV64IMA workload. No printf, syscalls or libc.
 * Each hart owns 64 KiB, exceeding its L1D capacity. Phase markers are aids for
 * a native checkpoint observer; they do not establish cache/pipeline cut state.
 * All four harts must complete all phases before hart zero reports HTIF PASS.
 */
#include <stdint.h>

enum { HARTS = 4, WORDS = 8192, ROUNDS = 3 };
typedef struct __attribute__((aligned(64))) {
    volatile uint64_t phase;
    volatile uint64_t completed;
    volatile uint64_t checksum;
    volatile uint64_t failure;
} hart_status_t;

volatile uint64_t tohost __attribute__((section(".tohost"), aligned(64)));
volatile uint64_t fromhost __attribute__((section(".tohost"), aligned(64)));
volatile uint64_t data[HARTS][WORDS] __attribute__((aligned(64)));
hart_status_t hart_status[HARTS];
static volatile uint64_t arrivals;
static volatile uint64_t generation;

static uint64_t pattern(uint64_t hart, uint64_t index)
{
    return ((hart + 1) * UINT64_C(0x9e3779b97f4a7c15)) ^
           (index * UINT64_C(0xd1b54a32d192ed03));
}

static void barrier(void)
{
    uint64_t previous = __atomic_load_n(&generation, __ATOMIC_ACQUIRE);
    if (__atomic_fetch_add(&arrivals, 1, __ATOMIC_ACQ_REL) == HARTS - 1) {
        __atomic_store_n(&arrivals, 0, __ATOMIC_RELAXED);
        __atomic_store_n(&generation, previous + 1, __ATOMIC_RELEASE);
    } else {
        while (__atomic_load_n(&generation, __ATOMIC_ACQUIRE) == previous) {}
    }
}

void workload_main(uint64_t hart)
{
    uint64_t error = 0, checksum = 0;
    hart_status[hart].phase = 1; /* early: real initialization stores */
    for (uint64_t i = 0; i < WORDS; ++i)
        data[hart][i] = pattern(hart, i);
#ifdef CHECKPOINT_WORKLOAD_CORRUPT_HART
#if CHECKPOINT_WORKLOAD_CORRUPT_HART < 0 || CHECKPOINT_WORKLOAD_CORRUPT_HART >= 4
#error "corruption hart must be one of the four executing harts"
#endif
    /* Verification build only: corrupt real memory, then run every check. */
    if (hart == CHECKPOINT_WORKLOAD_CORRUPT_HART)
        data[hart][WORDS / 2] ^= UINT64_C(0x400000000);
#endif
    barrier();

    hart_status[hart].phase = 2; /* warm: sequential loads, validate every word */
    for (uint64_t i = 0; i < WORDS; ++i) {
        uint64_t value = data[hart][i];
        error |= value ^ pattern(hart, i);
        checksum += value;
    }
    barrier();

    hart_status[hart].phase = 3; /* memory: permutation of cache-line accesses */
    for (uint64_t round = 0; round < ROUNDS; ++round) {
        for (uint64_t i = 0; i < WORDS; ++i) {
            uint64_t index = (i * 2053 + hart * 17) & (WORDS - 1);
            uint64_t value = data[hart][index];
            error |= value ^ (pattern(hart, index) + round);
            data[hart][index] = value + 1;
            checksum ^= value + index;
        }
    }
    barrier();

    hart_status[hart].phase = 4; /* late: check writes, all harts still compute */
    for (uint64_t i = 0; i < WORDS; ++i)
        error |= data[hart][i] ^ (pattern(hart, i) + ROUNDS);
    hart_status[hart].checksum = checksum;
    hart_status[hart].failure = error;
    __atomic_store_n(&hart_status[hart].completed, 1, __ATOMIC_RELEASE);
    barrier();

    if (hart == 0) {
        uint64_t failed = 0;
        for (uint64_t h = 0; h < HARTS; ++h) {
            if (__atomic_load_n(&hart_status[h].completed, __ATOMIC_ACQUIRE) != 1 ||
                hart_status[h].phase != 4 || hart_status[h].failure != 0)
                failed |= UINT64_C(1) << h;
        }
        /* A bad actual load/store fails even if a future observer is absent. */
        tohost = (failed << 1) | 1;
        __asm__ volatile("fence rw, rw" ::: "memory");
    }
    for (;;) __asm__ volatile("wfi");
}
