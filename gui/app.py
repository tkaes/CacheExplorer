import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from gui import LARGE_FONT, REG_FONT
from gui.comparison_tab import ComparisonTab
from gui.config_tab import ConfigTab

class CacheExplorer:
    def __init__(self, all_results):
        # ---------- CREATE ROOT/GEOMETRY ----------
        self.root = tk.Tk()
        self.root.title("Cache Explorer")
        self.root.geometry("1600x800")
        self.root.resizable(True, True)

        # ---------- FONT SCALING ----------
        tkfont.nametofont("TkDefaultFont").configure(size=REG_FONT)
        tkfont.nametofont("TkFixedFont").configure(size=REG_FONT)
        tkfont.nametofont("TkTextFont").configure(size=REG_FONT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both")

        # ---------- CREATE TABS ----------
        comparison_tab = ttk.Frame(notebook)
        notebook.add(comparison_tab, text="✱ COMPARISON")
        ComparisonTab(comparison_tab, all_results)

        for results in all_results:
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=results["name"].upper())
            ConfigTab(tab, results)

        # ---------- TAB STYLING ----------
        style = ttk.Style()
        style.configure("TNotebook.Tab", 
                font=("TkDefaultFont", LARGE_FONT),
                padding=[10, 4])