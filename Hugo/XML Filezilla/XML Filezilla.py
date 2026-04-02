import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def get_exe_dir():
    return os.path.dirname(
        sys.executable if getattr(sys, "frozen", False)
        else os.path.abspath(__file__)
    )

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

        self.left = self._build_panel(main, "Source", self.left_path, "left")
        self.right = self._build_panel(main, "Target", self.right_path, "right")

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        copy_frame = ttk.Frame(bottom)
        copy_frame.pack()

        ttk.Button(copy_frame, text="Copy →", command=self.copy_left_to_right)\
            .grid(row=0, column=0, padx=(0, 10))
        ttk.Button(copy_frame, text="← Copy", command=self.copy_right_to_left)\
            .grid(row=0, column=1, padx=(10, 0))

        back_frame = ttk.Frame(bottom)
        back_frame.pack(pady=(6, 0))

        ttk.Button(back_frame, text="← Back", command=self.undo_copy)\
            .pack()

    def _build_panel(self, parent, title, path_var, side):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=side, fill="both", expand=True, padx=5)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", padx=5, pady=5)

        entry = ttk.Entry(path_frame, textvariable=path_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e, s=side: self.refresh_one_side(s))
        entry.bind("<FocusOut>", lambda e, s=side: self.refresh_one_side(s))

        ttk.Button(
            path_frame, text="Browse",
            command=lambda v=path_var, s=side: self.browse_path(v, s)
        ).pack(side="left", padx=5)

        combo = ttk.Combobox(frame, state="readonly")
        combo.pack(fill="x", padx=5, pady=5)
        combo.bind("<<ComboboxSelected>>", lambda e, s=side: self.load_file(s))

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)

        text = tk.Text(text_frame, wrap="none")
        scroll = ttk.Scrollbar(text_frame)

        scroll.config(command=lambda *a: self.sync_scroll(*a))
        text.config(yscrollcommand=scroll.set)

        text.tag_configure("line_sel", background="#3399ff")
        text.tag_configure("diff", background="#ffb3b3")

        text.bind("<Double-Button-1>", self.select_line_both)
        text.bind("<Key>", lambda e: self.clear_selection())

        text.bind("<MouseWheel>", self.on_mousewheel)
        text.bind("<Button-4>", self.on_mousewheel)
        text.bind("<Button-5>", self.on_mousewheel)

        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        return {"path": path_var, "combo": combo, "text": text}

    def sync_scroll(self, *args):
        self.left["text"].yview(*args)
        self.right["text"].yview(*args)

    def on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            delta = -1
        else:
            delta = 1

        self.left["text"].yview_scroll(delta, "units")
        self.right["text"].yview_scroll(delta, "units")
        return "break"

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

    def snapshot(self):
        line = None
        if self.selected_range:
            line = int(self.selected_range[0].split(".")[0])
        return (
            self.left["text"].get("1.0", "end"),
            self.right["text"].get("1.0", "end"),
            line
        )

    def restore(self, snap):
        left_text, right_text, line = snap

        self.left["text"].delete("1.0", "end")
        self.right["text"].delete("1.0", "end")
        self.left["text"].insert("1.0", left_text)
        self.right["text"].insert("1.0", right_text)

        if line:
            start = f"{line}.0"
            end = f"{line}.end+1c"
            self.selected_range = (start, end)
            for panel in (self.left, self.right):
                t = panel["text"]
                t.tag_remove("line_sel", "1.0", "end")
                t.tag_add("line_sel", start, end)
                t.see(start)

        self.compare_lines()

    def copy_selected(self, src, dst):
        if not self.selected_range:
            messagebox.showinfo("Copy", "Double-click a line first.")
            return

        self.history.append(self.snapshot())

        start, end = self.selected_range
        dst.delete(start, end)
        dst.insert(start, src.get(start, end))
        self.compare_lines()

    def copy_left_to_right(self):
        self.copy_selected(self.left["text"], self.right["text"])

    def copy_right_to_left(self):
        self.copy_selected(self.right["text"], self.left["text"])

    def undo_copy(self):
        if not self.history:
            return
        self.restore(self.history.pop())

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
        if not name:
            return
        panel["text"].delete("1.0", "end")
        panel["text"].insert(
            "1.0",
            load_file(os.path.join(panel["path"].get(), name))
        )
        self.compare_lines()

if __name__ == "__main__":
    XMLFileZillaTextApp().mainloop()
