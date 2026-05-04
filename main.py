from utils.loader import load_imem_from_file
from utils.logger import write_lines, write_regs_log, write_dmem_log, write_cache_stats
from simulator.pipeline import run_simulation
from gui.app import CacheExplorer

# ------------------------------------------------------------
# EDITABLE INFORMATION
# ------------------------------------------------------------
INPUT_FILE = "inputs/assoc_demo.txt"
CONFIGS = [
    ("direct-mapped", 1, 8, 16),
    ("2-way",         2, 8, 16),
    ("4-way",         4, 8, 16),
]

def main():
    # ------------------------------------------------------------
    # RUN SIMULATION
    # ------------------------------------------------------------
    imem = load_imem_from_file(INPUT_FILE)

    all_results = []
    for name, assoc, num_sets, block_bytes in CONFIGS:
        results = run_simulation(imem, assoc, num_sets, block_bytes)
        results["name"]        = name
        results["assoc"]       = assoc
        results["num_sets"]    = num_sets
        results["block_bytes"] = block_bytes
        all_results.append(results)

        prefix = f"outputs/{name}"
        write_lines(f"{prefix}_trace.log",         results["trace_lines"])
        write_regs_log(results["regs"],            f"{prefix}_regs_final.log")
        write_dmem_log(results["dmem"],            f"{prefix}_dmem_final.log")
        write_lines(f"{prefix}_cache.log",         results["cache_lines_log"])
        write_cache_stats(f"{prefix}_cache_stats.log", results["stats"],
                          assoc, num_sets, block_bytes)

    # ------------------------------------------------------------
    # LAUNCH GUI, SEND RESULTS
    # ------------------------------------------------------------
    print("SIMULATIONS COMPLETE. LAUNCHING GUI.")
    app = CacheExplorer(all_results)
    app.root.mainloop()

if __name__ == "__main__":
    main()