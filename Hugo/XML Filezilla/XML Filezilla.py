import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def get_exe_dir():
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

def list_xml_files(path):
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if f.lower().endswith(".xml"))

def load_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

class XMLFileZillaTextApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XML Filezilla")
        self.geometry("1200x700")

        base = get_exe_dir()
        self.left_path = tk.StringVar(value=os.path.join(base, "namespaces"))
        self.right_path = tk.StringVar(value=os.path.join(base, "namespaces"))

        self.selected_range = None
        self.history = []

        self._build_ui()
        self._refresh_all()

        self.bind_all("<Control-z>", lambda e: self.undo_copy())

    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self.left = self._build_panel(main, "File 1", self.left_path, "left")
        self.right = self._build_panel(main, "File 2", self.right_path, "right")

        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.sync_scroll)
        scrollbar.pack(side="right", fill="y")

        self.left["text"].config(yscrollcommand=scrollbar.set)
        self.right["text"].config(yscrollcommand=scrollbar.set)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        btns = ttk.Frame(bottom)
        btns.pack()

        ttk.Button(btns, text="Copy →", command=self.copy_left_to_right).grid(row=0, column=0, padx=10)
        ttk.Button(btns, text="← Copy", command=self.copy_right_to_left).grid(row=0, column=1, padx=10)
        ttk.Button(bottom, text="← Back", command=self.undo_copy).pack(pady=6)

    def _build_panel(self, parent, title, path_var, side):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=side, fill="both", expand=True, padx=5)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", padx=5, pady=5)

        entry = ttk.Entry(path_frame, textvariable=path_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e, s=side: self.refresh_one_side(s))
        entry.bind("<FocusOut>", lambda e, s=side: self.refresh_one_side(s))

        ttk.Button(path_frame, text="Browse", command=lambda v=path_var, s=side: self.browse_path(v, s)).pack(side="left", padx=5)

        combo = ttk.Combobox(frame, state="readonly")
        combo.pack(fill="x", padx=5)
        combo.bind("<<ComboboxSelected>>", lambda e, s=side: self.load_file(s))

        search_var = tk.StringVar()
        search = ttk.Entry(frame, textvariable=search_var)
        search.pack(fill="x", padx=5, pady=(4, 2))
        search.bind("<KeyRelease>", lambda e, sv=search_var, s=side: self.search_text(s, sv.get()))

        text = tk.Text(frame, wrap="none", undo=True)
        text.pack(fill="both", expand=True, padx=5, pady=5)

        text.tag_configure("line_sel", background="#3399ff")
        text.tag_configure("diff", background="#ffb3b3")
        text.tag_configure("search", background="#ffff66")

        text.bind("<Double-Button-1>", self.select_line_both)
        text.bind("<Key>", lambda e: self.clear_selection())
        text.bind("<<Modified>>", self.on_text_modified)

        text.bind("<MouseWheel>", self.on_mousewheel)
        text.bind("<Button-4>", self.on_mousewheel)
        text.bind("<Button-5>", self.on_mousewheel)

        return {"path": path_var, "combo": combo, "text": text, "search": search_var}

    def sync_scroll(self, *args):
        self.left["text"].yview(*args)
        self.right["text"].yview(*args)

    def on_mousewheel(self, event):
        delta = -1 if event.num == 4 or event.delta > 0 else 1
        self.left["text"].yview_scroll(delta, "units")
        self.right["text"].yview_scroll(delta, "units")
        return "break"

    def on_text_modified(self, event):
        event.widget.edit_modified(False)
        self.compare_lines()

    def select_line_both(self, event):
        widget = event.widget
        line = int(widget.index(f"@{event.x},{event.y}").split(".")[0])
        start = f"{line}.0"
        end = f"{line}.end+1c"
        self.selected_range = (start, end)

        for panel in (self.left, self.right):
            t = panel["text"]
            t.tag_remove("line_sel", "1.0", "end")
            t.tag_add("line_sel", start, end)
            t.see(start)
        return "break"

    def clear_selection(self):
        self.selected_range = None
        for panel in (self.left, self.right):
            panel["text"].tag_remove("line_sel", "1.0", "end")

    def search_text(self, side, pattern):
        panel = self.left if side == "left" else self.right
        text = panel["text"]

        for p in (self.left, self.right):
            p["text"].tag_remove("search", "1.0", "end")

        if not pattern:
            return

        idx = text.search(pattern, "1.0", nocase=True, stopindex="end")
        if not idx:
            return

        line = idx.split(".")[0]

        for p in (self.left, self.right):
            t = p["text"]
            cur = "1.0"
            while True:
                hit = t.search(pattern, cur, nocase=True, stopindex="end")
                if not hit:
                    break
                t.tag_add("search", hit, f"{hit}+{len(pattern)}c")
                cur = f"{hit}+{len(pattern)}c"
            t.see(f"{line}.0")

    def compare_lines(self):
        l = self.left["text"].get("1.0", "end").splitlines()
        r = self.right["text"].get("1.0", "end").splitlines()

        for t in (self.left["text"], self.right["text"]):
            t.tag_remove("diff", "1.0", "end")

        for i in range(max(len(l), len(r))):
            if (l[i] if i < len(l) else "") != (r[i] if i < len(r) else ""):
                ln = i + 1
                self.left["text"].tag_add("diff", f"{ln}.0", f"{ln}.end")
                self.right["text"].tag_add("diff", f"{ln}.0", f"{ln}.end")

    def snapshot(self):
        return (
            self.left["text"].get("1.0", "end"),
            self.right["text"].get("1.0", "end"),
            self.left["text"].yview(),
            self.right["text"].yview()
        )

    def restore(self, snap):
        left, right, ly, ry = snap

        self.left["text"].delete("1.0", "end")
        self.right["text"].delete("1.0", "end")

        self.left["text"].insert("1.0", left)
        self.right["text"].insert("1.0", right)

        self.left["text"].yview_moveto(ly[0])
        self.right["text"].yview_moveto(ry[0])

        self.clear_selection()
        self.compare_lines()

    def copy_selected(self, src, dst):
        if not self.selected_range:
            messagebox.showinfo("Copy", "Double-click a line first.")
            return
        self.history.append(self.snapshot())
        start, end = self.selected_range
        dst.delete(start, end)
        dst.insert(start, src.get(start, end))
        self.clear_selection()
        self.compare_lines()

    def copy_left_to_right(self):
        self.copy_selected(self.left["text"], self.right["text"])

    def copy_right_to_left(self):
        self.copy_selected(self.right["text"], self.left["text"])

    def undo_copy(self):
        if self.history:
            self.restore(self.history.pop())

    def browse_path(self, var, side):
        folder = filedialog.askdirectory(initialdir=var.get())
        if folder:
            var.set(folder)
            self.refresh_one_side(side)

    def refresh_one_side(self, side):
        panel = self.left if side == "left" else self.right
        files = list_xml_files(panel["path"].get())
        panel["combo"]["values"] = files
        if files:
            panel["combo"].current(0)
            self.load_file(side)
        else:
            panel["text"].delete("1.0", "end")

    def _refresh_all(self):
        self.refresh_one_side("left")
        self.refresh_one_side("right")

    def load_file(self, side):
        panel = self.left if side == "left" else self.right
        name = panel["combo"].get()
        if name:
            panel["text"].delete("1.0", "end")
            panel["text"].insert("1.0", load_file(os.path.join(panel["path"].get(), name)))
        self.compare_lines()

if __name__ == "__main__":
    XMLFileZillaTextApp().mainloop()
