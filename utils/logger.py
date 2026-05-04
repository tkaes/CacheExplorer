from simulator.core import u32, s32

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
def write_lines(path, lines):
    f = open(path, "w", encoding="utf-8")
    i = 0
    while i < len(lines):
        f.write(lines[i] + "\n")
        i += 1
    f.close()


def write_regs_log(regs, path):
    f = open(path, "w", encoding="utf-8")
    for i in range(32):
        f.write("x%-2d = 0x%08X (%d)\n" % (i, u32(regs[i]), s32(regs[i])))
    f.close()


def write_dmem_log(dmem, path):
    f = open(path, "w", encoding="utf-8")
    for a in sorted(dmem.keys()):
        f.write("0x%08X : 0x%08X (%d)\n" % (u32(a), u32(dmem[a]), s32(dmem[a])))
    f.close()


def write_cache_stats(path, stats, assoc, num_sets, block_bytes):
    """
    Create cache_stats.log
    Cache config is passed in.
    """
    cache_size = assoc * num_sets * block_bytes

    total    = stats["lw_total"] + stats["sw_total"]
    hits     = stats["lw_hits"]  + stats["sw_hits"]
    misses   = stats["lw_misses"] + stats["sw_misses"]
    hit_rate = (hits / total) if total > 0 else 0.0

    lines = [
        "Cache config: size=%dB block=%dB assoc=%d sets=%d" % (
            cache_size, block_bytes, assoc, num_sets),
        "",
        "Total accesses: %d" % total,
        "Loads:          %d" % stats["lw_total"],
        "Stores:         %d" % stats["sw_total"],
        "",
        "Hits:           %d" % hits,
        "Misses:         %d" % misses,
        "",
        "Hit rate:       %.2f" % hit_rate,
        "",
        "Writebacks:     %d" % stats["writebacks"],
    ]

    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")