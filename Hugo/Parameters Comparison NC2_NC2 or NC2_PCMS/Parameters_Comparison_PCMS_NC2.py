import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

e_file_entry = None
b_file_entry = None

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
    else:
        messagebox.showerror("Error", "Invalid mode selected.")
        return

    e_parameters, e_values = [], []
    b_parameters, b_values = [], []

    for line in e_lines:
        elements = line.strip().split(';')
        if len(elements) > e_index:
            e_parameters.append(elements[0].strip())
            e_values.append(elements[e_index].strip())

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
                        output_tree.insert("", "end", values=(e_parameters[i], b_values[j], e_values[i]) if mode == "NC2-NC2" else (e_parameters[i], e_values[i], b_values[j]))
                except ValueError:
                    if e_values[i] != b_values[j]:
                        output_tree.insert("", "end", values=(e_parameters[i], b_values[j], e_values[i]) if mode == "NC2-NC2" else (e_parameters[i], e_values[i], b_values[j]))
                break

    output_tree.insert("", "end", values=("--- Not Found in Both Files ---", "", ""))

    for i in range(len(e_parameters)):
        if e_parameters[i] not in matched_params:
            output_tree.insert("", "end", values=(e_parameters[i], "Not Present", e_values[i]) if mode == "NC2-NC2" else (e_parameters[i], e_values[i], "Not Present"))

    for j in range(len(b_parameters)):
        if b_parameters[j] not in matched_params:
            output_tree.insert("", "end", values=(b_parameters[j], b_values[j], "Not Present") if mode == "NC2-NC2" else (b_parameters[j], "Not Present", b_values[j]))

def select_e_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        e_file_entry.delete(0, tk.END)
        e_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())

def select_b_file():
    mode = mode_var.get()
    filetypes = [("ZIP Files", "*.zip")] if mode == "NC2-PCMS" else [("CSV Files", "*.csv")]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        b_file_entry.delete(0, tk.END)
        b_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())

def update_treeview_columns(mode):
    output_tree["columns"] = ()
    for col in output_tree["columns"]:
        output_tree.heading(col, text="")
        output_tree.column(col, width=0)

    if mode == "NC2-NC2":
        columns = ("Parameter", "Value at the beginning", "Value at the end")
    else:
        columns = ("Parameter", "NC2 value", "PCMS value")

    output_tree["columns"] = columns
    for col in columns:
        output_tree.heading(col, text=col)
        output_tree.column(col, anchor="center", stretch=True)

def load_mode_specific_ui(*args):
    global e_file_entry, b_file_entry

    for widget in dynamic_frame.winfo_children():
        widget.destroy()

    mode = mode_var.get()
    dynamic_frame.grid_columnconfigure(1, weight=1)

    if mode == "NC2-NC2":
        tk.Label(dynamic_frame, text="End Parameters CSV File:").grid(row=0, column=0, padx=10, pady=(10, 0), sticky='w')
        e_file_entry = tk.Entry(dynamic_frame)
        e_file_entry.grid(row=0, column=1, sticky='nsew', pady=(10, 0))
        tk.Button(dynamic_frame, text="Browse...", command=select_e_file).grid(row=0, column=2, padx=10, pady=(10, 0))

        tk.Label(dynamic_frame, text="Beginning Parameters CSV File:").grid(row=1, column=0, padx=10, pady=(10, 0), sticky='w')
        b_file_entry = tk.Entry(dynamic_frame)
        b_file_entry.grid(row=1, column=1, sticky='nsew', pady=(10, 0))
        tk.Button(dynamic_frame, text="Browse...", command=select_b_file).grid(row=1, column=2, padx=10, pady=(10, 0))

    elif mode == "NC2-PCMS":
        tk.Label(dynamic_frame, text="NC2 Parameter CSV File:").grid(row=0, column=0, padx=10, pady=(10, 0), sticky='w')
        e_file_entry = tk.Entry(dynamic_frame)
        e_file_entry.grid(row=0, column=1, sticky='nsew', pady=(10, 0))
        tk.Button(dynamic_frame, text="Browse...", command=select_e_file).grid(row=0, column=2, padx=10, pady=(10, 0))

        tk.Label(dynamic_frame, text="PCMS ZIP File:").grid(row=1, column=0, padx=10, pady=(10, 0), sticky='w')
        b_file_entry = tk.Entry(dynamic_frame)
        b_file_entry.grid(row=1, column=1, sticky='nsew', pady=(10, 0))
        tk.Button(dynamic_frame, text="Browse...", command=select_b_file).grid(row=1, column=2, padx=10, pady=(10, 0))

    tk.Button(dynamic_frame, text="Process Files", command=process_files).grid(row=2, column=1, pady=10)
    update_treeview_columns(mode)
    output_tree.delete(*output_tree.get_children())

root = tk.Tk()
root.title("Parameter Comparison")
root.geometry("800x600")
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)

mode_frame = tk.Frame(root)
mode_frame.grid(row=0, column=0, columnspan=3, pady=(20, 10))
tk.Label(mode_frame, text="Select Mode:").pack(side="left", padx=(0, 5))
mode_var = tk.StringVar(value="NC2-NC2")
mode_menu = ttk.Combobox(mode_frame, textvariable=mode_var, values=["NC2-NC2", "NC2-PCMS"], state="readonly", width=15)
mode_menu.pack(side="left")
mode_var.trace_add("write", load_mode_specific_ui)

dynamic_frame = tk.Frame(root)
dynamic_frame.grid(row=1, column=0, columnspan=3, sticky='nsew')
dynamic_frame.grid_columnconfigure(1, weight=1)

output_frame = tk.Frame(root)
output_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(10, 20), sticky='nsew')
output_frame.grid_rowconfigure(0, weight=1)
output_frame.grid_columnconfigure(0, weight=1)

output_tree = ttk.Treeview(output_frame, show="headings")
output_tree.pack(fill='both', expand=True)

vsb = ttk.Scrollbar(output_frame, orient="vertical", command=output_tree.yview)
output_tree.configure(yscrollcommand=vsb.set)
vsb.pack(side='right', fill='y')

hsb = ttk.Scrollbar(output_frame, orient="horizontal", command=output_tree.xview)
output_tree.configure(xscrollcommand=hsb.set)
hsb.pack(side='bottom', fill='x')

load_mode_specific_ui()
root.mainloop()
