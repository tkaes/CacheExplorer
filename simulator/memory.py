from simulator.core import u32

# ------------------------------------------------------------
# MEMORY
# ------------------------------------------------------------
def mem_load_word(dmem, addr):
    """
    This is only used inside cache fill/writeback code.
    """
    if addr % 4 != 0:
        raise ValueError("Unaligned lw at address 0x%08X" % addr)
    return u32(dmem.get(addr, 0))


def mem_store_word(dmem, addr, value):
    """
    This is only used inside cache writeback code or cache flush.
    """
    if addr % 4 != 0:
        raise ValueError("Unaligned sw at address 0x%08X" % addr)
    dmem[addr] = u32(value)