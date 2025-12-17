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
    icon_data = """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"""
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
