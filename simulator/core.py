# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
MASK32 = 0xFFFFFFFF
WORD_BYTES = 4

# ------------------------------------------------------------
# 32-bit Helpers
# ------------------------------------------------------------
def u32(x):
    return x & MASK32


def s32(x):
    x = x & MASK32
    if x & 0x80000000:
        return x - 0x100000000
    return x


def sign_extend(value, bits):
    mask = (1 << bits) - 1
    v = value & mask
    sign_bit = 1 << (bits - 1)
    if v & sign_bit:
        v = v - (1 << bits)
    return v


def get_bits(x, hi, lo):
    width = hi - lo + 1
    return (x >> lo) & ((1 << width) - 1)


# ------------------------------------------------------------
# Immediate Generators
# ------------------------------------------------------------
def imm_i(instr):
    return sign_extend(get_bits(instr, 31, 20), 12)


def imm_s(instr):
    hi = get_bits(instr, 31, 25)
    lo = get_bits(instr, 11, 7)
    return sign_extend((hi << 5) | lo, 12)


def imm_b(instr):
    b12 = get_bits(instr, 31, 31)
    b11 = get_bits(instr, 7, 7)
    b10_5 = get_bits(instr, 30, 25)
    b4_1 = get_bits(instr, 11, 8)
    val = (b12 << 12) | (b11 << 11) | (b10_5 << 5) | (b4_1 << 1)
    return sign_extend(val, 13)


def imm_u(instr):
    return get_bits(instr, 31, 12) << 12


def imm_j(instr):
    j20 = get_bits(instr, 31, 31)
    j10_1 = get_bits(instr, 30, 21)
    j11 = get_bits(instr, 20, 20)
    j19_12 = get_bits(instr, 19, 12)
    val = (j20 << 20) | (j19_12 << 12) | (j11 << 11) | (j10_1 << 1)
    return sign_extend(val, 21)


# ------------------------------------------------------------
# Decode + Control
# ------------------------------------------------------------
def decode(instr):
    d = {}
    d["instr"] = u32(instr)
    d["opcode"] = get_bits(instr, 6, 0)
    d["rd"] = get_bits(instr, 11, 7)
    d["funct3"] = get_bits(instr, 14, 12)
    d["rs1"] = get_bits(instr, 19, 15)
    d["rs2"] = get_bits(instr, 24, 20)
    d["funct7"] = get_bits(instr, 31, 25)

    d["imm_I"] = imm_i(instr)
    d["imm_S"] = imm_s(instr)
    d["imm_B"] = imm_b(instr)
    d["imm_U"] = imm_u(instr)
    d["imm_J"] = imm_j(instr)
    return d


def main_control(d):
    op = d["opcode"]
    f3 = d["funct3"]

    c = {
        "RegWrite": 0,
        "MemRead": 0,
        "MemWrite": 0,
        "MemToReg": 0,
        "ALUSrc": 0,
        "Branch": 0,
        "Jump": 0,
        "JumpReg": 0,
        "ALUOp": "ADDR",
        "ImmSel": None,
        "BrType": None,
    }

    if op == 0x33:  # R
        c["RegWrite"] = 1
        c["ALUSrc"] = 0
        c["ALUOp"] = "R"

    elif op == 0x13:  # I-ALU
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "I"
        c["ImmSel"] = "I"

    elif op == 0x03:  # lw
        c["RegWrite"] = 1
        c["MemRead"] = 1
        c["MemToReg"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "I"

    elif op == 0x23:  # sw
        c["MemWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "S"

    elif op == 0x63:  # branches
        c["Branch"] = 1
        c["ALUSrc"] = 0
        c["ALUOp"] = "BR"
        c["ImmSel"] = "B"
        if f3 == 0b000:
            c["BrType"] = "beq"
        elif f3 == 0b001:
            c["BrType"] = "bne"
        elif f3 == 0b100:
            c["BrType"] = "blt"
        elif f3 == 0b101:
            c["BrType"] = "bge"
        elif f3 == 0b110:
            c["BrType"] = "bltu"
        elif f3 == 0b111:
            c["BrType"] = "bgeu"

    elif op == 0x6F:  # jal
        c["Jump"] = 1
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "J"

    elif op == 0x67:  # jalr
        c["Jump"] = 1
        c["JumpReg"] = 1
        c["RegWrite"] = 1
        c["ALUSrc"] = 1
        c["ALUOp"] = "ADDR"
        c["ImmSel"] = "I"

    return c


def select_imm(d, c):
    sel = c["ImmSel"]
    if sel == "I":
        return d["imm_I"]
    if sel == "S":
        return d["imm_S"]
    if sel == "B":
        return d["imm_B"]
    if sel == "U":
        return d["imm_U"]
    if sel == "J":
        return d["imm_J"]
    return 0


def alu_control(c, d):
    op = c["ALUOp"]
    f3 = d["funct3"]
    f7 = d["funct7"]

    if op == "ADDR":
        return "ADD"
    if op == "BR":
        return "SUB"

    if op == "R":
        if f3 == 0b000:
            return "SUB" if f7 == 0b0100000 else "ADD"
        if f3 == 0b111:
            return "AND"
        if f3 == 0b110:
            return "OR"
        if f3 == 0b100:
            return "XOR"
        if f3 == 0b001:
            return "SLL"
        if f3 == 0b101:
            return "SRA" if f7 == 0b0100000 else "SRL"
        if f3 == 0b010:
            return "SLT"
        if f3 == 0b011:
            return "SLTU"
        return "ADD"

    if op == "I":
        if f3 == 0b000:
            return "ADD"
        if f3 == 0b111:
            return "AND"
        if f3 == 0b110:
            return "OR"
        if f3 == 0b100:
            return "XOR"
        if f3 == 0b010:
            return "SLT"
        if f3 == 0b011:
            return "SLTU"
        if f3 == 0b001:
            return "SLL"
        if f3 == 0b101:
            return "SRA" if f7 == 0b0100000 else "SRL"
        return "ADD"

    return "ADD"


def alu_exec(alu_op, a, b):
    a = u32(a)
    b = u32(b)
    shamt = b & 0x1F

    if alu_op == "ADD":
        return u32(a + b)
    if alu_op == "SUB":
        return u32(a - b)
    if alu_op == "AND":
        return u32(a & b)
    if alu_op == "OR":
        return u32(a | b)
    if alu_op == "XOR":
        return u32(a ^ b)
    if alu_op == "SLL":
        return u32(a << shamt)
    if alu_op == "SRL":
        return u32(a >> shamt)
    if alu_op == "SRA":
        return u32(s32(a) >> shamt)
    if alu_op == "SLT":
        return 1 if s32(a) < s32(b) else 0
    if alu_op == "SLTU":
        return 1 if u32(a) < u32(b) else 0

    return u32(a + b)


def branch_taken(br_type, rs1_val, rs2_val):
    if br_type == "beq":
        return u32(rs1_val) == u32(rs2_val)
    if br_type == "bne":
        return u32(rs1_val) != u32(rs2_val)
    if br_type == "blt":
        return s32(rs1_val) < s32(rs2_val)
    if br_type == "bge":
        return s32(rs1_val) >= s32(rs2_val)
    if br_type == "bltu":
        return u32(rs1_val) < u32(rs2_val)
    if br_type == "bgeu":
        return u32(rs1_val) >= u32(rs2_val)
    return False