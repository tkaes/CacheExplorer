import os
from utils.loader import load_imem_from_file
from simulator.pipeline import run_simulation

# ------------------------------------------------------------
# PIPELINE TEST
# ------------------------------------------------------------

imem = load_imem_from_file("inputs/hex_inst.txt")
print("cwd:", os.getcwd())
print("imem size:", len(imem))

configs = [
    ("direct-mapped", 1, 8, 16),
    ("2-way",         2, 8, 16),
    ("4-way",         4, 8, 16),
]

for name, assoc, num_sets, block_bytes in configs:
    results = run_simulation(imem, assoc=assoc, num_sets=num_sets, block_bytes=block_bytes)
    s = results["stats"]
    total = s["lw_total"] + s["sw_total"]
    hits  = s["lw_hits"]  + s["sw_hits"]
    print(f"{name:15s} | hits={hits:3d} misses={total-hits:3d} writebacks={s['writebacks']:3d} hit_rate={hits/total:.2f}")