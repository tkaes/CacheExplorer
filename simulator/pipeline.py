from simulator.core import *
from simulator.cache import *

# ------------------------------------------------------------
# Stages: IF, ID, EX
# ------------------------------------------------------------
def stage_if(pc, imem):
    out = {}
    out["pc"] = u32(pc)
    out["pc_plus4"] = u32(pc + 4)
    out["instr"] = imem.get(u32(pc), None)
    return out


def stage_id(instr, regs):
    d = decode(instr)
    c = main_control(d)
    imm = select_imm(d, c)

    out = {}
    out["d"] = d
    out["c"] = c
    out["imm"] = imm
    out["rs1"] = d["rs1"]
    out["rs2"] = d["rs2"]
    out["rd"] = d["rd"]
    out["rs1_val"] = u32(regs[d["rs1"]])
    out["rs2_val"] = u32(regs[d["rs2"]])
    return out


def stage_ex(pc, pc_plus4, id_out):
    d = id_out["d"]
    c = id_out["c"]
    imm = id_out["imm"]

    rs1_val = id_out["rs1_val"]
    rs2_val = id_out["rs2_val"]

    alu_op = alu_control(c, d)
    alu_in2 = imm if c["ALUSrc"] else rs2_val
    alu_res = alu_exec(alu_op, rs1_val, alu_in2)

    next_pc = u32(pc_plus4)
    taken = False

    if c["Branch"] and c["BrType"] is not None:
        taken = branch_taken(c["BrType"], rs1_val, rs2_val)
        if taken:
            next_pc = u32(pc + imm)

    if c["Jump"]:
        taken = True
        if c["JumpReg"]:
            next_pc = u32((rs1_val + imm) & 0xFFFFFFFE)
        else:
            next_pc = u32(pc + imm)

    out = {}
    out["alu_op"] = alu_op
    out["alu_res"] = u32(alu_res)
    out["next_pc"] = u32(next_pc)
    out["taken"] = taken
    out["pc_plus4"] = u32(pc_plus4)
    out["rs2_val"] = u32(rs2_val)   # used for sw
    return out


# ------------------------------------------------------------
# Stages: Memory
# ------------------------------------------------------------
def stage_mem_with_cache(id_out, ex_out, cache, dmem, cache_lines_log, stats, assoc, num_sets, block_bytes):
    """
    - Determine if instruction is lw or sw using control signals:
        if c["MemRead"] -> lw
        if c["MemWrite"] -> sw
      (funct3==010 for word)
    - lw:
        mem_data = cache_access_lw(dmem, cache, addr, cache_lines_log, stats, assoc, num_sets, block_bytes)
        stats["lw_total"] += 1
    - sw:
        cache_access_sw(dmem, cache, addr, store_val, cache_lines_log, stats, assoc, num_sets, block_bytes)
        stats["sw_total"] += 1
    - Return dict:
        out["mem_data"]
        out["addr"]
        out["cache_event"] = "LW" or "SW" or "" (used by trace.log)

    IMPORTANT: mem_load_word/mem_store_word are NOT called here.
    """

    out = {}
    c   = id_out["c"]
    addr = u32(ex_out["alu_res"])

    out["mem_data"]    = 0
    out["addr"]        = addr
    out["cache_event"] = ""

    if c["MemRead"]:
        out["mem_data"]    = cache_access_lw(dmem, cache, addr, cache_lines_log, stats, assoc, num_sets, block_bytes)
        out["cache_event"] = "LW"
        stats["lw_total"] += 1

    elif c["MemWrite"]:
        store_val = ex_out["rs2_val"]
        cache_access_sw(dmem, cache, addr, store_val, cache_lines_log, stats, assoc, num_sets, block_bytes)
        out["cache_event"] = "SW"
        stats["sw_total"] += 1

    return out


# ------------------------------------------------------------
# Stages: WB
# ------------------------------------------------------------
def stage_wb(pc_plus4, id_out, ex_out, mem_out, regs):
    c = id_out["c"]
    rd = id_out["rd"]

    wb_val = ex_out["alu_res"]
    if c["MemToReg"]:
        wb_val = mem_out["mem_data"]

    if c["Jump"] and c["RegWrite"]:
        wb_val = u32(pc_plus4)

    did_write = False
    if c["RegWrite"] and rd != 0:
        regs[rd] = u32(wb_val)
        did_write = True

    regs[0] = 0

    out = {}
    out["wb_val"] = u32(wb_val)
    out["wb_rd"] = rd
    out["did_write"] = did_write
    return out


# ------------------------------------------------------------
# Trace Helpers
# ------------------------------------------------------------
def try_mnemonic(d):
    op = d["opcode"]
    f3 = d["funct3"]
    f7 = d["funct7"]

    if op == 0x33:
        if f3 == 0b000:
            return "sub" if f7 == 0b0100000 else "add"
        if f3 == 0b111:
            return "and"
        if f3 == 0b110:
            return "or"
        if f3 == 0b100:
            return "xor"
        if f3 == 0b001:
            return "sll"
        if f3 == 0b101:
            return "sra" if f7 == 0b0100000 else "srl"
        if f3 == 0b010:
            return "slt"
        if f3 == 0b011:
            return "sltu"
        return "r?"

    if op == 0x13:
        if f3 == 0b000:
            return "addi"
        if f3 == 0b111:
            return "andi"
        if f3 == 0b110:
            return "ori"
        if f3 == 0b100:
            return "xori"
        if f3 == 0b010:
            return "slti"
        if f3 == 0b011:
            return "sltiu"
        if f3 == 0b001:
            return "slli"
        if f3 == 0b101:
            return "srai" if f7 == 0b0100000 else "srli"
        return "i?"

    if op == 0x03 and f3 == 0b010:
        return "lw"
    if op == 0x23 and f3 == 0b010:
        return "sw"
    if op == 0x63:
        return {
            0b000: "beq",
            0b001: "bne",
            0b100: "blt",
            0b101: "bge",
            0b110: "bltu",
            0b111: "bgeu",
        }.get(f3, "b?")
    if op == 0x6F:
        return "jal"
    if op == 0x67:
        return "jalr"

    return "?"


def trace_line(step, if_out, id_out, ex_out, mem_out, wb_out):
    d = id_out["d"]
    c = id_out["c"]
    mnem = try_mnemonic(d)

    parts = []
    parts.append("step=%d" % step)
    parts.append("pc=0x%08X" % if_out["pc"])
    parts.append("instr=0x%08X" % d["instr"])
    parts.append("mn=%s" % mnem)

    parts.append("RegW=%d MemR=%d MemW=%d M2R=%d ALUSrc=%d Br=%d J=%d" % (
        c["RegWrite"], c["MemRead"], c["MemWrite"], c["MemToReg"], c["ALUSrc"], c["Branch"], c["Jump"]
    ))

    parts.append("alu=%s res=0x%08X" % (ex_out["alu_op"], ex_out["alu_res"]))

    if c["MemRead"] or c["MemWrite"]:
        parts.append("mem@0x%08X rdata=0x%08X" % (mem_out["addr"], mem_out["mem_data"]))
        if mem_out.get("cache_event", ""):
            parts.append("cache=%s" % mem_out["cache_event"])

    if wb_out["did_write"]:
        parts.append("wb=x%d<-0x%08X" % (wb_out["wb_rd"], wb_out["wb_val"]))

    parts.append("next_pc=0x%08X" % ex_out["next_pc"])
    return " | ".join(parts)


# ------------------------------------------------------------
# MAIN SIMULATION RUNNER
# ------------------------------------------------------------
def make_stats():
    return {
        "lw_total": 0,
        "sw_total": 0,
        "lw_hits": 0,
        "lw_misses": 0,
        "sw_hits": 0,
        "sw_misses": 0,
        "writebacks": 0,
    }


def run_simulation(imem, assoc, num_sets, block_bytes):
    """
    PARAMETERIZED so that sim runs with GIVEN CACHE CONFIGURATION.
    Returns a dict of all results so GUI can use them.
    """
    regs = [0] * 32
    dmem = {}

    cache = cache_make(assoc, num_sets, block_bytes)
    cache_lines_log = []
    trace_lines = []
    stats = make_stats()

    pc = 0
    steps = 0
    max_steps = 10_000_000

    while steps < max_steps:
        if_out = stage_if(pc, imem)
        if if_out["instr"] is None:
            break

        pc_plus4 = if_out["pc_plus4"]
        instr = if_out["instr"]

        id_out = stage_id(instr, regs)
        ex_out = stage_ex(if_out["pc"], pc_plus4, id_out)
        mem_out = stage_mem_with_cache(
            id_out, ex_out, cache, dmem,
            cache_lines_log, stats,
            assoc, num_sets, block_bytes
        )
        wb_out = stage_wb(pc_plus4, id_out, ex_out, mem_out, regs)

        trace_lines.append(trace_line(steps, if_out, id_out, ex_out, mem_out, wb_out))

        pc = u32(ex_out["next_pc"])
        regs[0] = 0
        steps += 1

    cache_flush_all(dmem, cache, cache_lines_log, stats, assoc, num_sets, block_bytes)

    return {
        "regs":           regs,
        "dmem":           dmem,
        "stats":          stats,
        "trace_lines":    trace_lines,
        "cache_lines_log": cache_lines_log,
        "steps":          steps,
        "final_pc":       u32(pc),
    }