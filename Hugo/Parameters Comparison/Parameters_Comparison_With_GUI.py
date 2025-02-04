import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

# Function to read file
def read_file(file_path):
    lines = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines[1:]  # Skip the header row

# Function to process files and display parameters
def process_files():
    e_file = e_file_entry.get()
    b_file = b_file_entry.get()

    if not os.path.exists(e_file) or not os.path.exists(b_file):
        messagebox.showerror("Error", "Please select valid file paths.")
        return

    e_files_variables = read_file(e_file)
    b_files_variables = read_file(b_file)

    e_parameters = []
    e_parameters_values = []
    b_parameters = []
    b_parameters_values = []

    for line in e_files_variables:
        elements = line.strip().split(',')
        e_parameters.append(elements[0])
        e_parameters_values.append(elements[1])

    for line1 in b_files_variables:
        elements1 = line1.strip().split(',')
        b_parameters.append(elements1[0])
        b_parameters_values.append(elements1[1])

    # Clear any previous entries in the treeview
    for item in output_tree.get_children():
        output_tree.delete(item)

    # Compare parameters and values
    matched_params = set()
    for i in range(len(e_parameters)):
        for j in range(len(b_parameters)):
            if e_parameters[i] == b_parameters[j]:
                matched_params.add(e_parameters[i])
                if e_parameters_values[i] != b_parameters_values[j]:
                    output_tree.insert("", "end", values=(e_parameters[i], b_parameters_values[j], e_parameters_values[i]))
                break

    # Add a separator row
    output_tree.insert("", "end", values=("--- Not Found in Both Files ---", "", ""))

    # Add unmatched parameters from the end file
    for i in range(len(e_parameters)):
        if e_parameters[i] not in matched_params:
            output_tree.insert("", "end", values=(e_parameters[i], "Not Present", e_parameters_values[i]))
    
    # Add unmatched parameters from the beginning file
    for j in range(len(b_parameters)):
        if b_parameters[j] not in matched_params:
            output_tree.insert("", "end", values=(b_parameters[j], b_parameters_values[j], "Not Present"))

def select_e_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        e_file_entry.delete(0, tk.END)
        e_file_entry.insert(0, file_path)

def select_b_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        b_file_entry.delete(0, tk.END)
        b_file_entry.insert(0, file_path)

# Create main window
root = tk.Tk()
root.title("Parameter Comparison")
root.geometry("600x400")

# Allow the window to be resizable
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(3, weight=1)

# Create file selection entries and buttons
tk.Label(root, text="End Alarms/Parameters File:").grid(row=0, column=0, pady=(10, 0), padx=10)
e_file_entry = tk.Entry(root, width=50)
e_file_entry.grid(row=0, column=1, pady=(10, 0), sticky='ew')
tk.Button(root, text="Browse...", command=select_e_file).grid(row=0, column=2, pady=(10, 0), padx=10)

tk.Label(root, text="Beginning Alarms/Parameters File:").grid(row=1, column=0, pady=(10, 0), padx=10)
b_file_entry = tk.Entry(root, width=50)
b_file_entry.grid(row=1, column=1, pady=(10, 0), sticky='ew')
tk.Button(root, text="Browse...", command=select_b_file).grid(row=1, column=2, pady=(10, 0), padx=10)

tk.Button(root, text="Process Files", command=process_files).grid(row=2, column=1, pady=10)

# Create treeview to display output with scrollbars
columns = ("Parameter/Alarm", "Value at the beginning", "Value at the end")
output_frame = tk.Frame(root)
output_frame.grid(row=3, column=0, columnspan=3, pady=(10, 20), padx=10, sticky='nsew')

output_tree = ttk.Treeview(output_frame, columns=columns, show="headings")
for col in columns:
    output_tree.heading(col, text=col)
    output_tree.column(col, anchor="center", stretch=True)

# Add vertical scrollbar
vsb = ttk.Scrollbar(output_frame, orient="vertical", command=output_tree.yview)
output_tree.configure(yscrollcommand=vsb.set)
vsb.pack(side='right', fill='y')

# Add horizontal scrollbar
hsb = ttk.Scrollbar(output_frame, orient="horizontal", command=output_tree.xview)
output_tree.configure(xscrollcommand=hsb.set)
hsb.pack(side='bottom', fill='x')

output_tree.pack(fill='both', expand=True)

# Run the application
root.mainloop()
