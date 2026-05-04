from simulator.cache import cache_make, cache_access_lw

# ------------------------------------------------------------
# CACHE TEST
# ------------------------------------------------------------

dmem = {0: 0x11111111, 4: 0x22222222}
cache = cache_make(assoc=2, num_sets=4, block_bytes=16)
log = []
stats = {"lw_total":0,"sw_total":0,"lw_hits":0,"lw_misses":0,"sw_hits":0,"sw_misses":0,"writebacks":0}

# first access should miss (addr never accessed)
val1 = cache_access_lw(dmem, cache, 0, log, stats, assoc=2, num_sets=4, block_bytes=16)
# second access should hit (now addr is cached)
val2 = cache_access_lw(dmem, cache, 0, log, stats, assoc=2, num_sets=4, block_bytes=16)

assert val1 == 0x11111111, f"Expected 0x11111111 got {val1:#010x}"
assert stats["lw_misses"] == 1
assert stats["lw_hits"] == 1
print("cache tests passed")
for line in log:
    print(line)