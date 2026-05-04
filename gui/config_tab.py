import tkinter as tk
from tkinter import ttk
from gui import LARGE_FONT, MID_FONT, REG_FONT

class ConfigTab:
    def __init__(self, parent, results):
        # ---------- DATA SERIALIZATION ----------
        stats = results["stats"]
        total    = stats["lw_total"] + stats["sw_total"]
        hits     = stats["lw_hits"]  + stats["sw_hits"]
        misses   = total - hits
        hit_rate = (hits / total) if total > 0 else 0.0

        # ---------- PARENT GRID CONFIG ----------
        parent.columnconfigure(0, weight=0)  # stats table
        parent.columnconfigure(1, weight=2)  # dmem and cache scrollboxes
        parent.columnconfigure(2, weight=2)  # regs and trace scrollboxes
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=0, minsize=500)
        parent.rowconfigure(3, weight=1)  # buffer row

        # ---------- INFO LABEL: row 0, col 0 ----------
        info = (f"CONFIG: assoc={results['assoc']}  "
                f"sets={results['num_sets']}  "
                f"block={results['block_bytes']}B  "
                f"size={results['assoc'] * results['num_sets'] * results['block_bytes']}B")
        tk.Label(parent, text=info, font=("TkDefaultFont", LARGE_FONT, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="", padx=16, pady=(12, 4))

        # ---------- STATS TABLE: row 1, col 0 ----------
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)

        rows = [
            ("Total Accesses", total),
            ("Loads",          stats["lw_total"]),
            ("Stores",         stats["sw_total"]),
            ("Hits",           hits),
            ("Misses",         misses),
            ("LW Hits",        stats["lw_hits"]),
            ("LW Misses",      stats["lw_misses"]),
            ("SW Hits",        stats["sw_hits"]),
            ("SW Misses",      stats["sw_misses"]),
            ("Writebacks",     stats["writebacks"]),
            ("Hit Rate",       f"{hit_rate:.2%}"),
        ]

        # populate rows
        for i, (label, value) in enumerate(rows):
            bg = "#f0f0f0" if i % 2 == 0 else "white"
            tk.Label(frame, text=label, width=20, anchor="w",
                     bg=bg, font=("TkDefaultFont", MID_FONT, "bold")).grid(row=i, column=0, sticky="ew", padx=1, pady=1)
            tk.Label(frame, text=str(value), width=16, anchor="w",
                     bg=bg, font=("TkDefaultFont", MID_FONT)).grid(row=i, column=1, sticky="ew", padx=1, pady=1)

        # ---------- DMEM_FINAL: row 1, col 1 ----------
        self.generate_scrollbox(parent, row=1, col=1, label="dmem_final", lines=[
            "0x%08X : 0x%08X (%d)" % (addr, val & 0xFFFFFFFF, val)
            for addr, val in sorted(results["dmem"].items())
        ])

        # ---------- REGS_FINAL: row 1, col 2 ----------
        self.generate_scrollbox(parent, row=1, col=2, label="regs_final", lines=[
            "x%-2d = 0x%08X (%d)" % (i, val & 0xFFFFFFFF, val)
            for i, val in enumerate(results["regs"])
        ])

        # ---------- CACHE: row 2, col 1 ----------
        self.generate_scrollbox(parent, row=2, col=1, label="cache.log",
                                lines=results["cache_lines_log"])
        
        # ---------- TRACE: row 2, col 2 ----------
        self.generate_scrollbox(parent, row=2, col=2, label="trace.log",
                                lines=results["trace_lines"])
        
    # ------------------------------------------------------------
    # HELPER METHOD: generate scrollboxes
    # ------------------------------------------------------------
    def generate_scrollbox(self, parent, row, col, label, lines):
        outer = ttk.Frame(parent)
        outer.grid(row=row, column=col, sticky="nsew", padx=(0, 8), pady=4)
        outer.grid_propagate(False)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        tk.Label(outer, text=label, font=("TkDefaultFont", REG_FONT, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))

        scrollbar = ttk.Scrollbar(outer, orient="vertical")
        scrollbar.grid(row=1, column=1, sticky="ns")

        text = tk.Text(outer, yscrollcommand=scrollbar.set,
                       wrap="none", font=("Courier", REG_FONT), state="disabled")
        text.grid(row=1, column=0, sticky="nsew")
        scrollbar.config(command=text.yview)

        text.config(state="normal")
        for line in lines:
            text.insert("end", line + "\n")
        text.config(state="disabled")