import os
import csv
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Label, PhotoImage
from tkinterdnd2 import TkinterDnD, DND_FILES
import sys
import base64
import io
from PIL import Image, ImageTk
import tkinter.font as tkfont

e_file_entry = None
b_file_entry = None
file_entries = []
file_types = []
save_button = None

def read_nc2_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    return lines[2:]

def read_pcms_zip(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for name in zip_ref.namelist():
            if "_para" in name and name.endswith(".csv"):
                with zip_ref.open(name) as file:
                    raw_bytes = file.read()
                    for encoding in ['utf-8', 'latin1', 'cp1252']:
                        try:
                            content = raw_bytes.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        return []
                    lines = content.splitlines()
                    return lines[1:]
    return []

def process_files():
    mode = mode_var.get()
    e_file = e_file_entry.get()
    b_file = b_file_entry.get()

    if not os.path.exists(e_file) or not os.path.exists(b_file):
        messagebox.showerror("Error", "Please select valid file paths.")
        return

    if mode == "NC2-NC2":
        e_lines = read_nc2_file(e_file)
        b_lines = read_nc2_file(b_file)
        e_index, b_index = 1, 1
    elif mode == "NC2-PCMS":
        e_lines = read_nc2_file(e_file)
        b_lines = read_pcms_zip(b_file)
        e_index, b_index = 1, 5
    elif mode == "PCMS-PCMS":
        e_lines = read_pcms_zip(e_file)
        b_lines = read_pcms_zip(b_file)
        e_index, b_index = 5, 5
    else:
        messagebox.showerror("Error", "Invalid mode selected.")
        return

    e_parameters, e_values = [], []
    b_parameters, b_values = [], []
    parameters_names = []

    for line in e_lines:
        elements = line.strip().split(';')
        if len(elements) > e_index:
            param = elements[0].strip().strip('"')
            param = param.replace("P", "P ") if param.startswith("P") and not param.startswith("P ") else param
            e_parameters.append(param)
            e_values.append(elements[e_index].strip())
            if mode == "PCMS-PCMS":
                parameters_names.append(elements[1].strip().strip('"') if len(elements) > 1 else "")
            else:
                parameters_names.append(elements[6].strip() if len(elements) > 6 else "")

    for line in b_lines:
        elements = line.strip().split(';')
        if len(elements) > b_index:
            param = elements[0].strip().strip('"')
            param = param.replace("P", "P ") if param.startswith("P") and not param.startswith("P ") else param
            b_parameters.append(param)
            b_values.append(elements[b_index].strip())

    output_tree.delete(*output_tree.get_children())
    matched_params = set()

    for i in range(len(e_parameters)):
        for j in range(len(b_parameters)):
            if e_parameters[i].lower() == b_parameters[j].lower():
                matched_params.add(e_parameters[i])
                try:
                    if float(e_values[i]) != float(b_values[j]):
                        if mode == "NC2-NC2":
                            output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], b_values[j], e_values[i]))
                        else:
                            output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], e_values[i], b_values[j]))
                except ValueError:
                    if e_values[i] != b_values[j]:
                        if mode == "NC2-NC2":
                            output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], b_values[j], e_values[i]))
                        else:
                            output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], e_values[i], b_values[j]))
                break

    output_tree.insert("", "end", values=("--- Not Found in Both Files ---", "", "", ""))

    if save_button:
        save_button.config(state=tk.NORMAL)

    for i in range(len(e_parameters)):
        if e_parameters[i] not in matched_params:
            if mode == "NC2-NC2":
                output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], "Not Present", e_values[i]))
            else:
                output_tree.insert("", "end", values=(e_parameters[i], parameters_names[i], e_values[i], "Not Present"))
    for j in range(len(b_parameters)):
        if b_parameters[j] not in matched_params:
            if mode == "NC2-NC2":
                output_tree.insert("", "end", values=(b_parameters[j], "", b_values[j], "Not Present"))
            else:
                output_tree.insert("", "end", values=(b_parameters[j], "", "Not Present", b_values[j]))

    adjust_columns()
    try:
        _update_inputs_scrollregion()
        _size_inputs_canvas_to_content()
    except Exception:
        pass

def select_e_file():
    mode = mode_var.get()
    filetypes = [("ZIP Files", "*.zip")] if mode == "PCMS-PCMS" else [("CSV Files", "*.csv")]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        e_file_entry.delete(0, tk.END)
        e_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())
        adjust_columns()

def select_b_file():
    mode = mode_var.get()
    filetypes = [("ZIP Files", "*.zip")] if mode in ["NC2-PCMS", "PCMS-PCMS"] else [("CSV Files", "*.csv")]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        b_file_entry.delete(0, tk.END)
        b_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())
        adjust_columns()

def handle_e_drop(event):
    file_path = event.data.strip('{}')
    e_file_entry.delete(0, tk.END)
    e_file_entry.insert(0, file_path)
    output_tree.delete(*output_tree.get_children())
    adjust_columns()

def handle_b_drop(event):
    file_path = event.data.strip('{}')
    b_file_entry.delete(0, tk.END)
    b_file_entry.insert(0, file_path)
    output_tree.delete(*output_tree.get_children())
    adjust_columns()

def update_treeview_columns(mode):
    output_tree["columns"] = ()
    for col in output_tree["columns"]:
        output_tree.heading(col, text="")
        output_tree.column(col, width=0)

    if mode == "NC2-NC2":
        columns = ("Parameter", "Description", "Value at the beginning", "Value at the end")
    elif mode == "NC2-PCMS":
        columns = ("Parameter", "Description", "NC2 value", "PCMS value")
    else:
        columns = ("Parameter", "Description", "PCMS File A value", "PCMS File B value")

    output_tree["columns"] = columns
    for col in columns:
        output_tree.heading(col, text=col)
        output_tree.column(col, anchor="center", width=140, stretch=False)

    adjust_columns()

def save(output_tree):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("Excel", "*.csv"), ("All files", "*.*")]
    )
    if not file_path:
        return
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        columns = output_tree["columns"]
        writer.writerow(columns)
        for row_id in output_tree.get_children():
            row = output_tree.item(row_id)["values"]
            writer.writerow(row)
    messagebox.showinfo("Completed", "Saved successfully.")

def resource_path(relative_path):
    return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), relative_path)

def update_treeview_columns_n(labels):
    output_tree["columns"] = ("Parameter", "Description") + tuple(labels)
    for col in output_tree["columns"]:
        output_tree.heading(col, text=col)
        output_tree.column(col, anchor="center", width=140, stretch=False)
    adjust_columns()

def select_file(i):
    mode = mode_var.get()
    if mode == "NC2-NC2":
        filetypes = [("CSV", "*.csv")]
    elif mode == "PCMS-PCMS":
        filetypes = [("ZIP", "*.zip")]
    else:
        filetypes = [("CSV", "*.csv")] if file_types[i] == "CSV" else [("ZIP", "*.zip")]
    path = filedialog.askopenfilename(filetypes=filetypes)
    if path:
        file_entries[i].delete(0, tk.END)
        file_entries[i].insert(0, path)
        output_tree.delete(*output_tree.get_children())
        adjust_columns()

def handle_drop(i, event):
    path = event.data.strip('{}')
    file_entries[i].delete(0, tk.END)
    file_entries[i].insert(0, path)
    output_tree.delete(*output_tree.get_children())
    adjust_columns()

def process_n_files():
    mode = mode_var.get()
    if mode == "NC2-PCMS":
        n = csv_count_var.get() + zip_count_var.get()
    elif mode == "NC2-NC2":
        n = num_files_var.get()
    else:
        n = num_files_var_zip.get()

    paths = []
    for i in range(n):
        p = file_entries[i].get().strip()
        if not p:
            messagebox.showerror("Error", "Please select all file paths.")
            return
        if not os.path.exists(p):
            messagebox.showerror("Error", f"Path does not exist:\n{p}")
            return
        paths.append(p)

    maps = []
    for i, p in enumerate(paths):
        if mode == "NC2-NC2":
            lines = read_nc2_file(p)
            v_idx, d_idx = 1, 6
        elif mode == "PCMS-PCMS":
            lines = read_pcms_zip(p)
            v_idx, d_idx = 5, 1
        else:
            if file_types[i] == "CSV":
                lines = read_nc2_file(p)
                v_idx, d_idx = 1, 6
            else:
                lines = read_pcms_zip(p)
                v_idx, d_idx = 5, 1
        m = {}
        for line in lines:
            parts = [x.strip() for x in line.strip().split(';')]
            if len(parts) > v_idx:
                param = parts[0].strip().strip('"')
                if param.startswith("P") and not param.startswith("P "):
                    param = param.replace("P", "P ", 1)
                val = parts[v_idx].strip()
                desc = parts[d_idx].strip().strip('"') if len(parts) > d_idx else ""
                m[param] = (val, desc)
        maps.append(m)

    all_params = sorted(set().union(*[set(m.keys()) for m in maps]), key=sort_key_param)

    output_tree.delete(*output_tree.get_children())

    if mode == "NC2-NC2":
        header_labels = [f"Parameters CSV File {i+1}" for i in range(n)]
    elif mode == "PCMS-PCMS":
        header_labels = [f"PCMS ZIP File {i+1}" for i in range(n)]
    else:
        c = csv_count_var.get()
        z = zip_count_var.get()
        header_labels = [f"NC2 CSV File {i+1}" for i in range(c)] + [f"PCMS ZIP File {j+1}" for j in range(z)]

    update_treeview_columns_n(header_labels)

    for prm in all_params:
        desc = ""
        for m in maps:
            if prm in m and m[prm][1]:
                desc = m[prm][1]
                break
        vals = []
        present = []
        norm = []
        for m in maps:
            if prm in m:
                v = m[prm][0]
                vals.append(v)
                present.append(True)
                try:
                    norm.append((True, float(v)))
                except:
                    norm.append((False, v))
            else:
                vals.append("Not Present")
                present.append(False)
                norm.append((False, "Not Present"))
        mismatch = False
        if not all(present):
            mismatch = True
        else:
            first = norm[0]
            for k in range(1, len(norm)):
                if norm[k] != first:
                    mismatch = True
                    break
        if mismatch:
            output_tree.insert("", "end", values=(prm, desc, *vals))

    if save_button:
        save_button.config(state=tk.NORMAL)

    adjust_columns()
    try:
        _update_inputs_scrollregion()
        _size_inputs_canvas_to_content()
    except Exception:
        pass

def sort_key_param(p):
    s = str(p).strip().strip('"')
    if s.upper().startswith('P'):
        s = s[1:].strip()
        if s.startswith(' '):
            s = s.strip()
    token = s.split()[0] if s.split() else ""
    principal = float('inf')
    secondary = float('inf')
    try:
        parts = token.split('.')
        principal = int(parts[0])
        if len(parts) > 1 and parts[1] != '':
            secondary = int(parts[1])
        else:
            secondary = -1
    except:
        pass
    return (principal, secondary, s.lower())

def load_mode_specific_ui(*args):
    global e_file_entry, b_file_entry, file_entries, save_button, file_types
    for widget in dynamic_frame.winfo_children():
        widget.destroy()
    file_entries = []
    file_types = []

    mode = mode_var.get()
    dynamic_frame.grid_columnconfigure(1, weight=1)

    if mode == "NC2-NC2":
        n = num_files_var.get()
        for i in range(n):
            tk.Label(dynamic_frame, text=f"Parameters CSV File {i+1}:").grid(row=i, column=0, padx=10, pady=(10, 0), sticky='w')
            entry = tk.Entry(dynamic_frame)
            entry.grid(row=i, column=1, sticky='nsew', pady=(10, 0))
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind('<<Drop>>', lambda e, idx=i: handle_drop(idx, e))
            tk.Button(dynamic_frame, text="Browse...", command=lambda idx=i: select_file(idx)).grid(row=i, column=2, padx=10, pady=(10, 0))
            file_entries.append(entry)
            file_types.append("CSV")
        tk.Button(dynamic_frame, text="Process Files", command=process_n_files).grid(row=n, column=1, pady=10)
        save_button = tk.Button(dynamic_frame, text="Save", command=lambda: save(output_tree), state=tk.DISABLED)
        save_button.grid(row=n, column=2, pady=10)
        update_treeview_columns_n([f"Parameters CSV File {i+1}" for i in range(n)])
        output_tree.delete(*output_tree.get_children())
        adjust_columns()
        try:
            _update_inputs_scrollregion()
            _size_inputs_canvas_to_content()
        except Exception:
            pass
        return

    if mode == "PCMS-PCMS":
        n = num_files_var_zip.get()
        for i in range(n):
            tk.Label(dynamic_frame, text=f"PCMS ZIP File {i+1}:").grid(row=i, column=0, padx=10, pady=(10, 0), sticky='w')
            entry = tk.Entry(dynamic_frame)
            entry.grid(row=i, column=1, sticky='nsew', pady=(10, 0))
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind('<<Drop>>', lambda e, idx=i: handle_drop(idx, e))
            tk.Button(dynamic_frame, text="Browse...", command=lambda idx=i: select_file(idx)).grid(row=i, column=2, padx=10, pady=(10, 0))
            file_entries.append(entry)
            file_types.append("ZIP")
        tk.Button(dynamic_frame, text="Process Files", command=process_n_files).grid(row=n, column=1, pady=10)
        save_button = tk.Button(dynamic_frame, text="Save", command=lambda: save(output_tree), state=tk.DISABLED)
        save_button.grid(row=n, column=2, pady=10)
        update_treeview_columns_n([f"PCMS ZIP File {i+1}" for i in range(n)])
        output_tree.delete(*output_tree.get_children())
        adjust_columns()
        try:
            _update_inputs_scrollregion()
            _size_inputs_canvas_to_content()
        except Exception:
            pass
        return

    c = csv_count_var.get()
    z = zip_count_var.get()
    n = c + z
    for i in range(c):
        tk.Label(dynamic_frame, text=f"NC2 CSV File {i+1}:").grid(row=i, column=0, padx=10, pady=(10, 0), sticky='w')
        entry = tk.Entry(dynamic_frame)
        entry.grid(row=i, column=1, sticky='nsew', pady=(10, 0))
        entry.drop_target_register(DND_FILES)
        entry.dnd_bind('<<Drop>>', lambda e, idx=i: handle_drop(idx, e))
        tk.Button(dynamic_frame, text="Browse...", command=lambda idx=i: select_file(idx)).grid(row=i, column=2, padx=10, pady=(10, 0))
        file_entries.append(entry)
        file_types.append("CSV")
    for j in range(z):
        idx = c + j
        tk.Label(dynamic_frame, text=f"PCMS ZIP File {j+1}:").grid(row=idx, column=0, padx=10, pady=(10, 0), sticky='w')
        entry = tk.Entry(dynamic_frame)
        entry.grid(row=idx, column=1, sticky='nsew', pady=(10, 0))
        entry.drop_target_register(DND_FILES)
        entry.dnd_bind('<<Drop>>', lambda e, k=idx: handle_drop(k, e))
        tk.Button(dynamic_frame, text="Browse...", command=lambda k=idx: select_file(k)).grid(row=idx, column=2, padx=10, pady=(10, 0))
        file_entries.append(entry)
        file_types.append("ZIP")
    tk.Button(dynamic_frame, text="Process Files", command=process_n_files).grid(row=n, column=1, pady=10)
    save_button = tk.Button(dynamic_frame, text="Save", command=lambda: save(output_tree), state=tk.DISABLED)
    save_button.grid(row=n, column=2, pady=10)
    header_labels = [f"NC2 CSV File {i+1}" for i in range(c)] + [f"PCMS ZIP File {j+1}" for j in range(z)]
    update_treeview_columns_n(header_labels)
    output_tree.delete(*output_tree.get_children())
    adjust_columns()
    try:
        _update_inputs_scrollregion()
        _size_inputs_canvas_to_content()
    except Exception:
        pass

root = TkinterDnD.Tk()
try:
    icon_data = b"""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 j... (icon data unchanged)"""
    if icon_data:
        icon_stream = io.BytesIO(base64.b64decode(icon_data))
        icon_image = Image.open(icon_stream)
        icon_photo = ImageTk.PhotoImage(icon_image)
        root.iconphoto(False, icon_photo)
except Exception:
    pass

root.title("Parameter Comparison Tool v2")
root.geometry("900x600")
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(2, weight=1)

mode_frame = tk.Frame(root)
mode_frame.grid(row=0, column=0, columnspan=3, pady=(20, 10))
tk.Label(mode_frame, text="Select Mode:").pack(side="left", padx=(0, 5))
mode_var = tk.StringVar(value="NC2-NC2")
mode_menu = ttk.Combobox(mode_frame, textvariable=mode_var, values=["NC2-NC2", "NC2-PCMS", "PCMS-PCMS"], state="readonly", width=15)
mode_menu.pack(side="left")

num_files_var = tk.IntVar(master=root, value=2)
num_files_var_zip = tk.IntVar(master=root, value=2)
csv_count_var = tk.IntVar(master=root, value=1)
zip_count_var = tk.IntVar(master=root, value=1)

mode_extras_frame = tk.Frame(mode_frame)
mode_extras_frame.pack(side="left")

def on_mode_change(*_):
    for w in mode_extras_frame.winfo_children():
        w.destroy()
    if mode_var.get() == "NC2-PCMS":
        tk.Label(mode_extras_frame, text="NC2 CSV Files:").grid(row=0, column=0, padx=(15, 5))
        csv_spin_top = ttk.Spinbox(mode_extras_frame, from_=1, to=10, textvariable=csv_count_var, width=5, state="readonly")
        csv_spin_top.grid(row=0, column=1)
        tk.Label(mode_extras_frame, text="PCMS ZIP Files:").grid(row=0, column=2, padx=(15, 5))
        zip_spin_top = ttk.Spinbox(mode_extras_frame, from_=1, to=10, textvariable=zip_count_var, width=5, state="readonly")
        zip_spin_top.grid(row=0, column=3)
    elif mode_var.get() == "PCMS-PCMS":
        tk.Label(mode_extras_frame, text="Number of files:").grid(row=0, column=0, padx=(15, 5))
        num_files_spin_local = ttk.Spinbox(mode_extras_frame, from_=2, to=20, textvariable=num_files_var_zip, width=5, state="readonly")
        num_files_spin_local.grid(row=0, column=1)
    else:
        tk.Label(mode_extras_frame, text="Number of files:").grid(row=0, column=0, padx=(15, 5))
        num_files_spin_local = ttk.Spinbox(mode_extras_frame, from_=2, to=20, textvariable=num_files_var, width=5, state="readonly")
        num_files_spin_local.grid(row=0, column=1)
    load_mode_specific_ui()

mode_var.trace_add("write", on_mode_change)
num_files_var.trace_add("write", load_mode_specific_ui)
num_files_var_zip.trace_add("write", load_mode_specific_ui)
csv_count_var.trace_add("write", load_mode_specific_ui)
zip_count_var.trace_add("write", load_mode_specific_ui)

inputs_container = tk.Frame(root)
inputs_container.grid(row=1, column=0, columnspan=3, padx=10, sticky='ew')
inputs_container.grid_columnconfigure(0, weight=1)
inputs_container.grid_rowconfigure(0, weight=0)

inputs_canvas = tk.Canvas(inputs_container, highlightthickness=0)
inputs_scroll_y = tk.Scrollbar(inputs_container, orient="vertical", command=inputs_canvas.yview)
inputs_canvas.grid(row=0, column=0, sticky="ew")
inputs_scroll_y.grid(row=0, column=1, sticky="ns")
inputs_canvas.configure(yscrollcommand=inputs_scroll_y.set)

dynamic_frame = tk.Frame(inputs_canvas)
dynamic_frame_id = inputs_canvas.create_window((0, 0), window=dynamic_frame, anchor="nw")
dynamic_frame.grid_columnconfigure(1, weight=1)

def _update_inputs_scrollregion(event=None):
    """Update canvas scrollregion to match dynamic_frame size and keep width synced."""
    inputs_canvas.configure(scrollregion=inputs_canvas.bbox("all"))
    try:
        canvas_w = inputs_canvas.winfo_width()
        inputs_canvas.itemconfig(dynamic_frame_id, width=canvas_w)
    except Exception:
        pass

def _size_inputs_canvas_to_content(max_height=260):
    """
    Size the inputs canvas to the content height (up to max_height),
    so the scrollbar height matches the form and the output tree begins right after it.
    """
    try:
        dynamic_frame.update_idletasks()
        req_h = dynamic_frame.winfo_reqheight()
        h = min(max(req_h, 1), max_height)
        inputs_canvas.configure(height=h)
    except Exception:
        pass

dynamic_frame.bind("<Configure>", lambda e: (_update_inputs_scrollregion(), _size_inputs_canvas_to_content()))
inputs_canvas.bind("<Configure>", _update_inputs_scrollregion)

output_frame = tk.Frame(root)
output_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=(10, 20), sticky='nsew')
output_frame.grid_rowconfigure(0, weight=1)
output_frame.grid_columnconfigure(0, weight=1)

tree_container = tk.Frame(output_frame)
tree_container.grid(row=0, column=0, sticky='nsew')

output_tree = ttk.Treeview(tree_container, show="headings")
output_tree.grid(row=0, column=0, sticky="nsew")

tree_scroll_y = tk.Scrollbar(tree_container, orient="vertical", command=output_tree.yview)
tree_scroll_y.grid(row=0, column=1, sticky="ns")
output_tree.configure(yscrollcommand=tree_scroll_y.set)

tree_scroll_x = tk.Scrollbar(tree_container, orient="horizontal", command=output_tree.xview)
tree_scroll_x.grid(row=1, column=0, sticky="ew")
output_tree.configure(xscrollcommand=tree_scroll_x.set)

tree_container.grid_rowconfigure(0, weight=1)
tree_container.grid_columnconfigure(0, weight=1)

def _estimate_row_height():
    """Estimate Treeview row height using style or font metrics."""
    style = ttk.Style()
    rh = style.lookup("Treeview", "rowheight")
    try:
        rh = int(rh)
    except Exception:
        rh = None
    if not rh or rh <= 0:
        font_name = style.lookup("Treeview", "font")
        try:
            f = tkfont.nametofont(font_name) if font_name else tkfont.nametofont("TkDefaultFont")
        except Exception:
            f = tkfont.nametofont("TkDefaultFont")
        rh = max(f.metrics("linespace") + 6, 18)
    return rh

def _update_tree_min_rows(event=None):
    """Set tree height to fill available space but keep at least 15 visible rows."""
    try:
        available_px = tree_container.winfo_height()
        if available_px <= 0:
            return
        row_h = _estimate_row_height()
        header_px = 24
        usable_px = max(available_px - header_px, 0)
        rows_fit = max(15, int(usable_px / row_h))
        current_h = int(output_tree.cget("height") or 0)
        if rows_fit != current_h:
            output_tree.configure(height=rows_fit)
    except Exception:
        pass

tree_container.bind("<Configure>", _update_tree_min_rows)
output_tree.bind("<Configure>", _update_tree_min_rows)

def adjust_columns():
    cols = output_tree["columns"]
    if not cols:
        return
    style = ttk.Style()
    font_name = style.lookup("Treeview", "font")
    try:
        font = tkfont.nametofont(font_name) if font_name else tkfont.nametofont("TkDefaultFont")
    except Exception:
        font = tkfont.nametofont("TkDefaultFont")

    vbar_w = tree_scroll_y.winfo_width() or 16
    available_width = output_tree.winfo_width()
    if available_width < 100:
        available_width = max(tree_container.winfo_width() - vbar_w, 100)
    else:
        available_width = max(available_width - vbar_w, 100)

    measured_widths = []
    for col in cols:
        header_text = (output_tree.heading(col).get("text") or "")
        w = font.measure(str(header_text)) + 24
        measured_widths.append(max(w, 80))

    total_required = sum(measured_widths)
    if available_width >= total_required and total_required > 0:
        scaled = [int(w * available_width / total_required) for w in measured_widths]
        remainder = available_width - sum(scaled)
        i = 0
        while remainder > 0 and i < len(scaled):
            scaled[i] += 1
            remainder -= 1
            i += 1
        for col, w in zip(cols, scaled):
            output_tree.column(col, width=max(w, 50), stretch=True)
    else:
        for col, w in zip(cols, measured_widths):
            output_tree.column(col, width=int(w), stretch=False)

tree_container.bind("<Configure>", lambda e: adjust_columns())

script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "logo.png")
try:
    logo = PhotoImage(file=logo_path)
    logo = logo.subsample(2, 2)
    logo_label = Label(root, image=logo)
    logo_label.image = logo
    logo_label.place(relx=0.98, rely=0.01, anchor="ne")
except Exception as e:
    print(f"Logo not found or failed to load: {e}")

logo_POT_path = os.path.join(script_dir, "logo_POT.png")
try:
    logo_POT = PhotoImage(file=logo_POT_path)
    logo_POT = logo_POT.subsample(3, 3)
    logo_POT_label = Label(root, image=logo_POT)
    logo_POT_label.image = logo_POT
    logo_POT_label.place(relx=0.1, rely=0.01, anchor="ne")
except Exception as e:
    print(f"Logo not found or failed to load: {e}")

try:
    on_mode_change()
    _update_inputs_scrollregion()
    _size_inputs_canvas_to_content()
except Exception as e:
    messagebox.showerror("Startup Error", str(e))

root.mainloop()
