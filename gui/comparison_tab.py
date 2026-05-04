import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from gui import MID_FONT

class ComparisonTab:
    def __init__(self, parent, all_results):
        # ---------- DATA SERIALIZATION ----------
        computed = []
        for result in all_results:
            stats = result["stats"]
            total    = stats["lw_total"] + stats["sw_total"]
            hits     = stats["lw_hits"]  + stats["sw_hits"]
            misses   = total - hits
            hit_rate = (hits / total) if total > 0 else 0.0
            computed.append({
                "name":       result["name"],
                "total":      total,
                "hits":       hits,
                "misses":     misses,
                "hit_rate":   hit_rate,
                "writebacks": stats["writebacks"],
            })

        names     = [c["name"]     for c in computed]
        hit_rates = [c["hit_rate"] for c in computed]
        hits      = [c["hits"]     for c in computed]
        misses    = [c["misses"]   for c in computed]

        # ---------- PARENT GRID CONFIG ----------
        parent.columnconfigure(0, weight=1)  # comparison table
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=0)
        parent.rowconfigure(1, weight=1)     # HR and H/M graphs

        # ---------- COMPARISON TABLE: row 0, col 0 ----------
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, columnspan=2, sticky="", padx=16, pady=4)

        # header row
        tk.Label(frame, text="Metric", width=14, anchor="w",
                font=("TkDefaultFont", MID_FONT, "bold")).grid(row=0, column=0, padx=1, pady=1)
        for col, c in enumerate(computed):
            tk.Label(frame, text=c["name"], width=16, anchor="w",
                    font=("TkDefaultFont", MID_FONT, "bold")).grid(row=0, column=col+1, padx=1, pady=1)

        # data rows
        rows = [
            ("Total Accesses", lambda c: c["total"]),
            ("Hits",           lambda c: c["hits"]),
            ("Misses",         lambda c: c["misses"]),
            ("Writebacks",     lambda c: c["writebacks"]),
            ("Hit Rate",       lambda c: f"{c['hit_rate']:.2%}"),
        ]

        # populate rows
        for i, (label, getter) in enumerate(rows):
            bg = "#f0f0f0" if i % 2 == 0 else "white"
            tk.Label(frame, text=label, width=14, anchor="w", bg=bg, font=("TkDefaultFont", MID_FONT, "bold")).grid(
                row=i+1, column=0, sticky="ew", padx=1, pady=1)
            for col, c in enumerate(computed):
                tk.Label(frame, text=str(getter(c)), width=16, anchor="w", bg=bg, font=("TkDefaultFont", MID_FONT)).grid(
                    row=i+1, column=col+1, sticky="ew", padx=1, pady=1)
                
        # ---------- HIT RATE GRAPH: row 1, col 0 ----------
        fig1, ax1 = plt.subplots(figsize=(4, 2))
        bars = ax1.bar(names, hit_rates)
        ax1.set_title("Hit Rate by Config")
        ax1.set_ylabel("Hit Rate")
        ax1.set_ylim(0, 1.0)
        for bar, rate in zip(bars, hit_rates):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                     f"{rate:.0%}", ha="center", va="bottom", fontsize=9)
        fig1.tight_layout()

        canvas1 = FigureCanvasTkAgg(fig1, master=parent)
        canvas1.draw()
        canvas1.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=(0, 16), pady=(16, 4))

        # ---------- HIT/MISS GRAPH: row 1, col 1 ----------
        fig2, ax2 = plt.subplots(figsize=(4, 2))
        y = range(len(names))
        ax2.barh(list(y), hits,   color="#55A868", label="Hits")
        ax2.barh(list(y), misses, left=hits, color="#C44E52", label="Misses")
        ax2.set_yticks(list(y))
        ax2.set_yticklabels(names)
        ax2.set_title("Hits/Misses by Config")
        ax2.set_xlabel("Memory Accesses")
        ax2.legend(loc="lower right")
        fig2.tight_layout()

        canvas2 = FigureCanvasTkAgg(fig2, master=parent)
        canvas2.draw()
        canvas2.get_tk_widget().grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(4, 16))