import os
import csv
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Label , PhotoImage
from tkinterdnd2 import TkinterDnD, DND_FILES
import sys
import base64
import io
from PIL import Image, ImageTk

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

def select_e_file():
    mode = mode_var.get()
    filetypes = [("ZIP Files", "*.zip")] if mode == "PCMS-PCMS" else [("CSV Files", "*.csv")]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        e_file_entry.delete(0, tk.END)
        e_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())

def select_b_file():
    mode = mode_var.get()
    filetypes = [("ZIP Files", "*.zip")] if mode in ["NC2-PCMS", "PCMS-PCMS"] else [("CSV Files", "*.csv")]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        b_file_entry.delete(0, tk.END)
        b_file_entry.insert(0, file_path)
        output_tree.delete(*output_tree.get_children())

def handle_e_drop(event):
    file_path = event.data.strip('{}')
    e_file_entry.delete(0, tk.END)
    e_file_entry.insert(0, file_path)
    output_tree.delete(*output_tree.get_children())

def handle_b_drop(event):
    file_path = event.data.strip('{}')
    b_file_entry.delete(0, tk.END)
    b_file_entry.insert(0, file_path)
    output_tree.delete(*output_tree.get_children())

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
        e_file_entry.drop_target_register(DND_FILES)
        e_file_entry.dnd_bind('<<Drop>>', handle_e_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_e_file).grid(row=0, column=2, padx=10, pady=(10, 0))

        tk.Label(dynamic_frame, text="Beginning Parameters CSV File:").grid(row=1, column=0, padx=10, pady=(10, 0), sticky='w')
        b_file_entry = tk.Entry(dynamic_frame)
        b_file_entry.grid(row=1, column=1, sticky='nsew', pady=(10, 0))
        b_file_entry.drop_target_register(DND_FILES)
        b_file_entry.dnd_bind('<<Drop>>', handle_b_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_b_file).grid(row=1, column=2, padx=10, pady=(10, 0))

    elif mode == "NC2-PCMS":
        tk.Label(dynamic_frame, text="NC2 Parameter CSV File:").grid(row=0, column=0, padx=10, pady=(10, 0), sticky='w')
        e_file_entry = tk.Entry(dynamic_frame)
        e_file_entry.grid(row=0, column=1, sticky='nsew', pady=(10, 0))
        e_file_entry.drop_target_register(DND_FILES)
        e_file_entry.dnd_bind('<<Drop>>', handle_e_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_e_file).grid(row=0, column=2, padx=10, pady=(10, 0))

        tk.Label(dynamic_frame, text="PCMS ZIP File:").grid(row=1, column=0, padx=10, pady=(10, 0), sticky='w')
        b_file_entry = tk.Entry(dynamic_frame)
        b_file_entry.grid(row=1, column=1, sticky='nsew', pady=(10, 0))
        b_file_entry.drop_target_register(DND_FILES)
        b_file_entry.dnd_bind('<<Drop>>', handle_b_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_b_file).grid(row=1, column=2, padx=10, pady=(10, 0))

    elif mode == "PCMS-PCMS":
        tk.Label(dynamic_frame, text="PCMS ZIP File A:").grid(row=0, column=0, padx=10, pady=(10, 0), sticky='w')
        e_file_entry = tk.Entry(dynamic_frame)
        e_file_entry.grid(row=0, column=1, sticky='nsew', pady=(10, 0))
        e_file_entry.drop_target_register(DND_FILES)
        e_file_entry.dnd_bind('<<Drop>>', handle_e_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_e_file).grid(row=0, column=2, padx=10, pady=(10, 0))

        tk.Label(dynamic_frame, text="PCMS ZIP File B:").grid(row=1, column=0, padx=10, pady=(10, 0), sticky='w')
        b_file_entry = tk.Entry(dynamic_frame)
        b_file_entry.grid(row=1, column=1, sticky='nsew', pady=(10, 0))
        b_file_entry.drop_target_register(DND_FILES)
        b_file_entry.dnd_bind('<<Drop>>', handle_b_drop)
        tk.Button(dynamic_frame, text="Browse...", command=select_b_file).grid(row=1, column=2, padx=10, pady=(10, 0))

    tk.Button(dynamic_frame, text="Process Files", command=process_files).grid(row=2, column=1, pady=10)

    global save_button
    save_button = tk.Button(dynamic_frame, text="Save", command=lambda: save(output_tree), state=tk.DISABLED)
    save_button.grid(row=2, column=2, pady=10)

    update_treeview_columns(mode)
    output_tree.delete(*output_tree.get_children())

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

root = TkinterDnD.Tk()
icon_data = b"""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"""

icon_stream = io.BytesIO(base64.b64decode(icon_data))
icon_image = Image.open(icon_stream)

icon_photo = ImageTk.PhotoImage(icon_image)
root.iconphoto(False, icon_photo)

root.title("Parameter Comparison Tool v1")
root.geometry("900x600")
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)

mode_frame = tk.Frame(root)
mode_frame.grid(row=0, column=0, columnspan=3, pady=(20, 10))
tk.Label(mode_frame, text="Select Mode:").pack(side="left", padx=(0, 5))
mode_var = tk.StringVar(value="NC2-NC2")
mode_menu = ttk.Combobox(mode_frame, textvariable=mode_var, values=["NC2-NC2", "NC2-PCMS", "PCMS-PCMS"], state="readonly", width=15)
mode_menu.pack(side="left")
mode_var.trace_add("write", load_mode_specific_ui)

dynamic_frame = tk.Frame(root)
dynamic_frame.grid(row=1, column=0, columnspan=3, sticky='nsew')
dynamic_frame.grid_columnconfigure(1, weight=1)

output_frame = tk.Frame(root)
output_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(10, 20), sticky='nsew')
output_frame.grid_rowconfigure(0, weight=1)
output_frame.grid_columnconfigure(0, weight=1)

tree_container = tk.Frame(output_frame)
tree_container.grid(row=0, column=0, sticky='nsew')

output_tree = ttk.Treeview(tree_container, show="headings")
output_tree.pack(side="left", fill="both", expand=True)

tree_scroll_y = tk.Scrollbar(tree_container, orient="vertical", command=output_tree.yview)
tree_scroll_y.pack(side="right", fill="y")
output_tree.configure(yscrollcommand=tree_scroll_y.set)

script_dir = os.path.dirname(os.path.abspath(__file__))

logo_path = os.path.join(script_dir, "logo.png")
try:
    logo = PhotoImage(file=logo_path)
    logo = logo.subsample(2, 2)
    logo_label = Label(root, image=logo)
    logo_label.image = logo
    logo_label.place(relx=0.98, rely=0.07, anchor="se")
except Exception as e:
    print(f"Logo not found or failed to load: {e}")

logo_POT_path = os.path.join(script_dir, "logo_POT.png")
try:
    logo_POT = PhotoImage(file=logo_POT_path)
    logo_POT = logo_POT.subsample(3, 3)
    logo_POT_label = Label(root, image=logo_POT)
    logo_POT_label.image = logo_POT
    logo_POT_label.place(relx=0.1, rely=0.078, anchor="se")
except Exception as e:
    print(f"Logo not found or failed to load: {e}")

load_mode_specific_ui()
root.mainloop()