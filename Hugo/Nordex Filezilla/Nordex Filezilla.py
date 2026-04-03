import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

TEXT_EXTENSIONS = ('.txt', '.csv', '.xml', '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.log', '.md')


def get_exe_dir():
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))


def list_files(path):
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if f.lower().endswith(TEXT_EXTENSIONS))


def load_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


class FileZillaTextApp(tk.Tk):
    def _yscroll(self, *args):
        self.vscroll.set(*args)
        for p in (self.left, self.right):
            p["text"].yview_moveto(args[0])
            p["lines"].yview_moveto(args[0])

    def auto_refresh(self):
        for side in ("left", "right"):
            panel = self.left if side == "left" else self.right
            path = panel["path"].get()
            if not os.path.isdir(path):
                continue
            files = list_files(path)
            combo = panel["combo"]
            if tuple(combo["values"]) != tuple(files):
                current = combo.get()
                combo["values"] = files
                if current in files:
                    combo.set(current)
                elif files:
                    combo.current(0)
                    self.load_file(side)
                else:
                    panel["text"].delete("1.0", "end")
        self.after(1000, self.auto_refresh)

    def raise_selection_tag(self):
        for p in (self.left, self.right):
            p["text"].tag_raise("line_sel")

    def sync_scroll_x(self, side, *args):
        if side == "left":
            self.left["text"].xview(*args)
            self.right["text"].xview_moveto(self.left["text"].xview()[0])
        else:
            self.right["text"].xview(*args)
            self.left["text"].xview_moveto(self.right["text"].xview()[0])

    def sync_scroll(self, *args):
        for p in (self.left, self.right):
            p["text"].yview(*args)
            p["lines"].yview(*args)

    def update_line_numbers(self, total):
        if total == self.total_lines:
            return
        self.total_lines = total
        nums = "\n".join(str(i) for i in range(1, total + 1)) + "\n"
        for p in (self.left, self.right):
            ln = p["lines"]
            ln.config(state="normal")
            ln.delete("1.0", "end")
            ln.insert("1.0", nums)
            ln.config(state="disabled")

    def update_diff_overview(self, diff_lines, total):
        c = self.diff_canvas
        c.delete("all")
        h = c.winfo_height()
        if total <= 0 or h <= 1:
            return
        diff_set = set(diff_lines)
        for i in range(total):
            if (i + 1) not in diff_set:
                continue
            y0 = int(i * h / total)
            y1 = int((i + 1) * h / total)
            if y1 <= y0:
                y1 = y0 + 1
            c.create_rectangle(2, y0, 8, y1, fill="red", outline="")

    def on_diff_click(self, event):
        h = self.diff_canvas.winfo_height()
        if h <= 1:
            return
        f = event.y / h
        self.left["text"].yview_moveto(f)
        self.right["text"].yview_moveto(f)

    def __init__(self):
        self.total_lines = 0
        super().__init__()
        self.title("Nordex Filezilla")
        self.geometry("1200x700")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        base = get_exe_dir()
        self.left_path = tk.StringVar(value=os.path.join(base, "namespaces"))
        self.right_path = tk.StringVar(value=os.path.join(base, "namespaces"))
        self.selected_ranges = set()
        self.history = []
        self._build_ui()
        self._refresh_all()
        self.auto_refresh()
        self.bind_all("<Control-z>", lambda e: self.undo_copy())

    def _on_diff_canvas_resize(self, event):
        self.compare_lines()

    def _build_ui(self):
        main = ttk.Frame(self)
        main.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.columnconfigure(2, weight=0)
        main.columnconfigure(3, weight=1)
        main.rowconfigure(0, weight=1)

        self.left = self._build_panel(main, "File 1", self.left_path, "left")
        self.left["frame"].grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.vscroll = ttk.Scrollbar(main, orient="vertical", command=self.sync_scroll)
        self.vscroll.grid(row=0, column=1, sticky="nsew")

        self.diff_canvas = tk.Canvas(main, width=10, highlightthickness=0)
        self.diff_canvas.grid(row=0, column=2, sticky="ns", pady=(18, 18))
        self.diff_canvas.bind("<Configure>", self._on_diff_canvas_resize)

        self.right = self._build_panel(main, "File 2", self.right_path, "right")
        self.right["frame"].grid(row=0, column=3, sticky="nsew", padx=(4, 0))

        for p in (self.left, self.right):
            p["text"].config(yscrollcommand=self._yscroll)
            p["lines"].config(yscrollcommand=self._yscroll)

        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))

        btns = ttk.Frame(bottom)
        btns.pack()
        ttk.Button(btns, text="Copy →", command=self.copy_left_to_right).grid(row=0, column=0, padx=10)
        ttk.Button(btns, text="← Copy", command=self.copy_right_to_left).grid(row=0, column=1, padx=10)
        ttk.Button(bottom, text="← Back", command=self.undo_copy).pack(pady=6)

    def _build_panel(self, parent, title, path_var, side):
        frame = ttk.LabelFrame(parent, text=title)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", padx=5, pady=5)

        entry = ttk.Entry(path_frame, textvariable=path_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e, s=side: self.refresh_one_side(s))
        entry.bind("<FocusOut>", lambda e, s=side: self.refresh_one_side(s))

        ttk.Button(path_frame, text="Browse",
                   command=lambda v=path_var, s=side: self.browse_path(v, s)).pack(side="left", padx=5)

        combo = ttk.Combobox(frame, state="readonly")
        combo.pack(fill="x", padx=5)
        combo.bind("<<ComboboxSelected>>", lambda e, s=side: self.load_file(s))

        search_var = tk.StringVar()
        search = ttk.Entry(frame, textvariable=search_var)
        search.pack(fill="x", padx=5, pady=(4, 2))
        search.bind("<KeyRelease>", lambda e, sv=search_var, s=side: self.search_text(s, sv.get()))

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)

        lines = tk.Text(text_frame, width=5, padx=5, pady=2,
                        takefocus=0, border=0, background="#f0f0f0", state="disabled")
        lines.grid(row=0, column=0, sticky="ns")

        text = tk.Text(text_frame, wrap="none", undo=True)
        text.grid(row=0, column=1, sticky="nsew")

        hscroll = ttk.Scrollbar(text_frame, orient="horizontal",
                                command=lambda *a, s=side: self.sync_scroll_x(s, *a))
        hscroll.grid(row=1, column=1, sticky="ew")
        text.config(xscrollcommand=hscroll.set)

        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text.tag_configure("line_sel", background="#3399ff")
        text.tag_configure("diff", background="#ffb3b3")
        text.tag_configure("search", background="#ffff66")

        text.bind("<Double-Button-1>", self.select_line_both)
        text.bind("<Key>", lambda e: None if e.keysym in ("Control_L", "Control_R") else self.clear_selection())
        text.bind("<<Modified>>", self.on_text_modified)
        text.bind("<MouseWheel>", self.on_mousewheel)
        text.bind("<Button-4>", self.on_mousewheel)
        text.bind("<Button-5>", self.on_mousewheel)

        return {"frame": frame, "path": path_var, "combo": combo,
                "text": text, "lines": lines, "search": search_var}

    def on_mousewheel(self, event):
        delta = -1 if event.num == 4 or event.delta > 0 else 1
        for p in (self.left, self.right):
            p["text"].yview_scroll(delta, "units")
            p["lines"].yview_scroll(delta, "units")
        return "break"

    def on_text_modified(self, event):
        event.widget.edit_modified(False)
        self.compare_lines()

    def _trim_trailing_blank_lines(self, text):
        while int(text.index("end-1c").split(".")[0]) > 1:
            if text.get("end-2l", "end-1l").strip():
                break
            text.delete("end-2l", "end-1l")

    def select_line_both(self, event):
        widget = event.widget
        line = int(widget.index(f"@{event.x},{event.y}").split(".")[0])
        start = f"{line}.0"
        end = f"{line}.end+1c"
        key = (start, end)

        ctrl = (event.state & 0x0004) != 0

        if not ctrl:
            self.selected_ranges.clear()
            for p in (self.left, self.right):
                p["text"].tag_remove("line_sel", "1.0", "end")

        if key in self.selected_ranges:
            self.selected_ranges.remove(key)
            for p in (self.left, self.right):
                p["text"].tag_remove("line_sel", start, end)
        else:
            self.selected_ranges.add(key)
            for p in (self.left, self.right):
                p["text"].tag_add("line_sel", start, end)
                p["text"].see(start)

        self.raise_selection_tag()
        return "break"

    def clear_selection(self):
        self.selected_ranges.clear()
        for p in (self.left, self.right):
            p["text"].tag_remove("line_sel", "1.0", "end")

    def search_text(self, side, pattern):
        for p in (self.left, self.right):
            p["text"].tag_remove("search", "1.0", "end")
        if not pattern:
            return
        first = None
        for p in (self.left, self.right):
            t = p["text"]
            cur = "1.0"
            while True:
                hit = t.search(pattern, cur, nocase=True, stopindex="end")
                if not hit:
                    break
                if first is None:
                    first = hit
                t.tag_add("search", hit, f"{hit}+{len(pattern)}c")
                cur = f"{hit}+{len(pattern)}c"
        if first:
            self.left["text"].see(first)
            self.right["text"].see(first)

    def compare_lines(self):
        ltxt = self.left["text"]
        rtxt = self.right["text"]

        l = ltxt.get("1.0", "end-1c").splitlines()
        r = rtxt.get("1.0", "end-1c").splitlines()

        total = max(len(l), len(r))

        if len(l) < total:
            ltxt.insert("end", "\n" * (total - len(l)))
        if len(r) < total:
            rtxt.insert("end", "\n" * (total - len(r)))

        for t in (ltxt, rtxt):
            t.tag_remove("diff", "1.0", "end")

        diff_lines = []
        for i in range(total):
            if (l[i] if i < len(l) else "") != (r[i] if i < len(r) else ""):
                ln = i + 1
                diff_lines.append(ln)
                ltxt.tag_add("diff", f"{ln}.0", f"{ln}.end")
                rtxt.tag_add("diff", f"{ln}.0", f"{ln}.end")

        self.update_diff_overview(diff_lines, total)
        self.raise_selection_tag()

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
        if not self.selected_ranges:
            messagebox.showinfo("Copy", "Double-click lines (use Ctrl for multi-select).")
            return
        self.history.append(self.snapshot())
        for start, end in sorted(self.selected_ranges):
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
        files = list_files(panel["path"].get())
        panel["combo"]["values"] = files
        if files:
            panel["combo"].current(0)
            self.load_file(side)
        else:
            panel["text"].delete("1.0", "end")
            self.total_lines = 0
            self.update_line_numbers(0)

    def _refresh_all(self):
        self.refresh_one_side("left")
        self.refresh_one_side("right")

    def load_file(self, side):
        panel = self.left if side == "left" else self.right
        name = panel["combo"].get()

        if name:
            panel["text"].delete("1.0", "end")
            panel["text"].insert("1.0", load_file(
                os.path.join(panel["path"].get(), name)
            ))
            self._trim_trailing_blank_lines(panel["text"])

        other = "right" if side == "left" else "left"
        other_panel = self.left if other == "left" else self.right
        other_name = other_panel["combo"].get()
        if other_name:
            other_panel["text"].delete("1.0", "end")
            other_panel["text"].insert("1.0", load_file(
                os.path.join(other_panel["path"].get(), other_name)
            ))
            self._trim_trailing_blank_lines(other_panel["text"])

        l_lines = int(self.left["text"].index("end-1c").split(".")[0])
        r_lines = int(self.right["text"].index("end-1c").split(".")[0])
        self.update_line_numbers(max(l_lines, r_lines))

        self.compare_lines()

if __name__ == "__main__":
    FileZillaTextApp().mainloop()
