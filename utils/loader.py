from simulator.core import MASK32
import os

# ------------------------------------------------------------
# IMEM LOADER
# ------------------------------------------------------------
def load_imem_from_file(path):
    imem = {}
    pc = 0
    if not os.path.exists(path):
        raise FileNotFoundError(f"Instruction file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                continue
            if s.lower().startswith("0x"):
                s = s[2:]
            instr = int(s, 16) & MASK32
            imem[pc] = instr
            pc += 4
    return imem