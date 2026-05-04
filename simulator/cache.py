from simulator.core import u32, WORD_BYTES
from simulator.memory import mem_store_word, mem_load_word

# ------------------------------------------------------------
# CACHING
# ------------------------------------------------------------
def cache_make(assoc, num_sets, block_bytes):
    """
    Cache Data Structure:
      cache = list of NUM_SETS sets
      each set = list of ASSOC lines (ways)
      each line is a dict with:
        valid : 0/1
        dirty : 0/1
        tag   : int
        data  : list of WORDS_PER_BLOCK words (each 32-bit)
        lru   : integer counter used for LRU replacement
    
    - Initialize all lines invalid and not dirty.
    - data array should be filled with zeros initially.
    """

    cache = []
    for s in range(num_sets):
        set_ways = []
        for w in range(assoc):
            line = {
                "valid": 0,
                "dirty": 0,
                "tag":   0,
                "data":  [0] * (block_bytes // WORD_BYTES),
                "lru":   0,
            }
            set_ways.append(line)
        cache.append(set_ways)
    return cache


def cache_addr_parts(addr, num_sets, block_bytes):
    """
    Given a BYTE address, compute (tag, set_index, word_offset) for this cache.

    Standard mapping:
      offset_bytes = addr % BLOCK_BYTES
      block_addr   = addr // BLOCK_BYTES
      set_index    = block_addr % NUM_SETS
      tag          = block_addr // NUM_SETS
      word_offset  = offset_bytes // 4    (0..WORDS_PER_BLOCK-1)

    Return: (tag, set_index, word_offset)
    """

    offset_bytes = addr % block_bytes
    block_addr   = addr // block_bytes
    set_index    = block_addr % num_sets
    tag          = block_addr // num_sets
    word_offset  = offset_bytes // WORD_BYTES
    return tag, set_index, word_offset


def cache_block_base_addr(tag, set_index, num_sets, block_bytes):
    """
    Compute the byte base address of the block identified by (tag, set_index).

    Reverse mapping:
      block_addr = tag * NUM_SETS + set_index
      base_addr  = block_addr * BLOCK_BYTES

    Return base_addr (byte address).
    """

    block_addr = tag * num_sets + set_index
    base_addr  = block_addr * block_bytes
    return base_addr


def cache_touch_lru(cache, set_index, used_way, assoc):
    """
    Update LRU metadata so that (set_index, used_way) is MOST recently used.
      - let used_way.lru = max_lru_in_set + 1
      - victim selection chooses least-recently-used line among valid lines
      - accesses update recency
    """

    current_max = 0
    for w in range(assoc):
        if cache[set_index][w]["lru"] > current_max:
            current_max = cache[set_index][w]["lru"]
    cache[set_index][used_way]["lru"] = current_max + 1


def cache_choose_victim(cache, set_index, assoc):
    """
    Choose a victim way in the given set:
      - If any invalid line exists, return that way first.
      - Else return way with smallest lru value (least recently used).

    Return: victim_way (0..ASSOC-1)
    """

    # return invalid first
    for w in range(assoc):
        if not cache[set_index][w]["valid"]:
            return w
    # all valid — return way w/ lowest lru counter (least recently used)
    lru_way = 0
    lru_val = cache[set_index][0]["lru"]
    for w in range(1, assoc):
        if cache[set_index][w]["lru"] < lru_val:
            lru_val = cache[set_index][w]["lru"]
            lru_way = w
    return lru_way


def cache_writeback_if_needed(dmem, cache, set_index, way, cache_lines_log, stats, num_sets, block_bytes):
    """
    If the chosen line is valid AND dirty:
      - Write back the entire block to backing memory (dmem) word-by-word.
      - Record a log line into cache_lines_log such as:
          "WB | set=... way=... tag=... base=..."
      - Increment stats["writebacks"]
      - Clear dirty bit.

    Use:
      base_addr = cache_block_base_addr(old_tag, set_index)
      For each word i in block:
        mem_store_word(dmem, base_addr + i*4, line.data[i])
    """

    line = cache[set_index][way]
    if line["valid"] and line["dirty"]:
        old_tag   = line["tag"]
        base_addr = cache_block_base_addr(old_tag, set_index, num_sets, block_bytes)
        for i in range(block_bytes // WORD_BYTES):
            mem_store_word(dmem, base_addr + i * WORD_BYTES, line["data"][i])
        cache_lines_log.append(
            "WB      | set=%d way=%d tag=0x%X base=0x%08X" % (
                set_index, way, old_tag, base_addr)
        )
        stats["writebacks"] += 1
        line["dirty"] = 0


def cache_fill_block_from_mem(dmem, cache, set_index, way, tag, num_sets, block_bytes):
    """
    Fill a cache line from backing memory (read entire block):
      - base_addr = cache_block_base_addr(tag, set_index)
      - for each i in 0..WORDS_PER_BLOCK-1:
          line.data[i] = mem_load_word(dmem, base_addr + i*4)
      - set valid=1, dirty=0, tag=tag
    """

    line = cache[set_index][way]
    base_addr = cache_block_base_addr(tag, set_index, num_sets, block_bytes)
    for i in range(block_bytes // WORD_BYTES):
        line["data"][i] = mem_load_word(dmem, base_addr + i * WORD_BYTES)
    line["valid"] = 1
    line["dirty"] = 0
    line["tag"]   = tag


def cache_access_lw(dmem, cache, addr, cache_lines_log, stats, assoc, num_sets, block_bytes):
    """
    Cache read access for lw.

    - Enforce word alignment (addr % 4 == 0). If not aligned, raise ValueError.
    - Compute (tag, set_index, word_offset).

    - HIT:
        - stats["lw_hits"] += 1
        - update LRU
        - log: "LW HIT | addr=... set=... way=... tag=... woff=... val=..."
        - return the word from cache line.data[word_offset]
    
    - MISS (write-allocate):
        - stats["lw_misses"] += 1
        - choose victim (invalid first else LRU)
        - if victim valid: log eviction line (include dirty)
        - if victim dirty: write back (cache_writeback_if_needed)
        - fill victim from memory (cache_fill_block_from_mem)
        - update LRU
        - log: "LW MISS | addr=... set=... way=... tag=... woff=... val=..."
        - return loaded word
    """

    if addr % WORD_BYTES != 0:
        raise ValueError("Unaligned lw at address 0x%08X" % addr)

    tag, set_index, word_offset = cache_addr_parts(addr, num_sets, block_bytes)
    s = cache[set_index]

    # check for hit
    for w in range(assoc):
        line = s[w]
        if line["valid"] and line["tag"] == tag:
            # HIT
            stats["lw_hits"] += 1
            val = u32(line["data"][word_offset])
            cache_touch_lru(cache, set_index, w, assoc)
            cache_lines_log.append(
                "LW HIT  | addr=0x%08X set=%d way=%d tag=0x%X woff=%d val=0x%08X" % (
                    addr, set_index, w, tag, word_offset, val)
            )
            return val

    # MISS
    stats["lw_misses"] += 1
    victim = cache_choose_victim(cache, set_index, assoc)
    vline  = s[victim]

    # if valid, log evict, include dirty
    if vline["valid"]:
        cache_lines_log.append(
            "EVICT   | set=%d way=%d tag=0x%X dirty=%d" % (
                set_index, victim, vline["tag"], vline["dirty"])
        )
        cache_writeback_if_needed(dmem, cache, set_index, victim, cache_lines_log, stats, num_sets, block_bytes)

    cache_fill_block_from_mem(dmem, cache, set_index, victim, tag, num_sets, block_bytes)
    cache_touch_lru(cache, set_index, victim, assoc)

    val = u32(vline["data"][word_offset])
    cache_lines_log.append(
        "LW MISS | addr=0x%08X set=%d way=%d tag=0x%X woff=%d val=0x%08X" % (
            addr, set_index, victim, tag, word_offset, val)
    )
    return val


def cache_access_sw(dmem, cache, addr, value, cache_lines_log, stats, assoc, num_sets, block_bytes):
    """
    Cache write access for sw.

    - Enforce word alignment. If not aligned, raise ValueError.
    - Write-back + write-allocate policy.

    HIT:
      - stats["sw_hits"] += 1
      - update line.data[word_offset] = value
      - mark dirty=1
      - update LRU
      - log: "SW HIT | addr=... set=... way=... tag=... woff=... val=..."

    MISS (write-allocate):
      - stats["sw_misses"] += 1
      - choose victim (invalid first else LRU)
      - if victim valid: log eviction (dirty?)
      - if victim dirty: write back block
      - fill block from memory
      - perform store to cache line + set dirty=1
      - update LRU
      - log: "SW MISS | addr=... set=... way=... tag=... woff=... val=..."
    """

    if addr % WORD_BYTES != 0:
        raise ValueError("Unaligned sw at address 0x%08X" % addr)

    tag, set_index, word_offset = cache_addr_parts(addr, num_sets, block_bytes)
    s = cache[set_index]

    # check for hit
    for w in range(assoc):
        line = s[w]
        if line["valid"] and line["tag"] == tag:
            # HIT
            stats["sw_hits"] += 1
            line["data"][word_offset] = u32(value)
            line["dirty"] = 1
            cache_touch_lru(cache, set_index, w, assoc)
            cache_lines_log.append(
                "SW HIT  | addr=0x%08X set=%d way=%d tag=0x%X woff=%d val=0x%08X" % (
                    addr, set_index, w, tag, word_offset, u32(value))
            )
            return

    # MISS
    # write-allocate: fill block first, then write
    stats["sw_misses"] += 1
    victim = cache_choose_victim(cache, set_index, assoc)
    vline  = s[victim]

    if vline["valid"]:
        cache_lines_log.append(
            "EVICT   | set=%d way=%d tag=0x%X dirty=%d" % (
                set_index, victim, vline["tag"], vline["dirty"])
        )
        cache_writeback_if_needed(dmem, cache, set_index, victim, cache_lines_log, stats, num_sets, block_bytes)

    cache_fill_block_from_mem(dmem, cache, set_index, victim, tag, num_sets, block_bytes)
    vline["data"][word_offset] = u32(value)
    vline["dirty"] = 1
    cache_touch_lru(cache, set_index, victim, assoc)
    cache_lines_log.append(
        "SW MISS | addr=0x%08X set=%d way=%d tag=0x%X woff=%d val=0x%08X" % (
            addr, set_index, victim, tag, word_offset, u32(value))
    )


def cache_flush_all(dmem, cache, cache_lines_log, stats, assoc, num_sets, block_bytes):
    """
    Flush the cache at program end:
      - for every set and every way:
          write back if dirty (cache_writeback_if_needed)
      - log: "CACHE FLUSH DONE"
    """

    for set_index in range(num_sets):
        for way in range(assoc):
            cache_writeback_if_needed(dmem, cache, set_index, way, cache_lines_log, stats, num_sets, block_bytes)
    cache_lines_log.append("CACHE FLUSH DONE")