import os
import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
from tkinter import ttk

# Function to read XML and get variable names
def get_xml_variables(path_xml):
    try:
        tree = ET.parse(path_xml)
        root = tree.getroot()
        return [f"{param.attrib['id']} {normalize_header(param.text)}" for param in root.findall('.//text')]
    except Exception as e:
        print(f"Error reading XML: {e}")
        return []

# Function to normalize header text for comparison
def normalize_header(header):
    # Remove any units in brackets and double quotes
    return header.split('[')[0].strip().replace('"', '')

# Function to read and process CSV and XML
def read_csv_xml(path_csv, path_xml, variables, final_path, final_name):
    try:
        with open(path_csv, 'r') as file:
            new_csv_lines = []

            # Read the first three lines for headers
            headers_line_1 = file.readline().strip()
            headers_line_2 = file.readline().strip()
            headers_line_3 = file.readline().strip()

            headers = headers_line_3.split(';')
            normalized_headers = [normalize_header(header) for header in headers]
            original_headers = [header for header in headers]

            # Extract text content from variables for comparison
            text_content_vars = [var.split(' ', 1)[1] for var in variables]

            # Always include the first two columns
            column_numbers = [0, 1]
            for i, header in enumerate(normalized_headers):
                if header in text_content_vars and i >= 2:  # Ensure first two columns are always included
                    column_numbers.append(i)

            # Add the headers to the new CSV lines
            new_csv_lines.append(headers_line_1)
            new_csv_lines.append(headers_line_2)
            new_csv_lines.append(';'.join([original_headers[i] for i in column_numbers]))

            print("Column Numbers:", column_numbers)

            # Process the data lines
            for line in file:
                columns = line.strip().split(';')
                new_line = [columns[i] for i in column_numbers]
                new_csv_lines.append(';'.join(new_line))

            # Debugging: Print the number of lines written to the output file
            print(f"Number of lines in output file (excluding header lines): {len(new_csv_lines) - 3}")

            final_file_name = os.path.join(final_path, f"{final_name}.csv")

            if not os.path.exists(final_path):
                print(f"The directory {final_path} does not exist.")
                return

            with open(final_file_name, 'w') as file:
                for line in new_csv_lines:
                    file.write(line + '\n')
            print(f"Data written successfully to {final_file_name}")
    except Exception as e:
        print(f"Error processing file: {e}")

# GUI functions
def process_files():
    path_csv = csv_entry.get()
    path_xml = xml_entry.get()
    selected_vars = [xml_variables[i] for i in selected_indices]
    final_path = final_path_entry.get()
    final_name = final_name_entry.get()

    if not os.path.exists(path_csv) or not os.path.exists(path_xml):
        messagebox.showerror("Error", "Please select valid file paths.")
        return

    read_csv_xml(path_csv, path_xml, selected_vars, final_path, final_name)

def select_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        csv_entry.delete(0, tk.END)
        csv_entry.insert(0, file_path)

def select_xml_file():
    file_path = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
    if file_path:
        xml_entry.delete(0, tk.END)
        xml_entry.insert(0, file_path)
        update_variable_choices()

def select_final_path():
    directory = filedialog.askdirectory()
    if directory:
        final_path_entry.delete(0, tk.END)
        final_path_entry.insert(0, directory)

def update_variable_choices():
    global xml_variables
    xml_path = xml_entry.get()
    xml_variables = get_xml_variables(xml_path)
    if not xml_variables:
        return

    for widget in vars_frame.winfo_children():
        widget.destroy()

    scrollbar = tk.Scrollbar(vars_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    var_listbox = tk.Listbox(vars_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
    for var in xml_variables:
        var_listbox.insert(tk.END, var)
    var_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=var_listbox.yview)

    def on_selection_change(event):
        global selected_indices
        selected_indices = var_listbox.curselection()
    
    var_listbox.bind('<<ListboxSelect>>', on_selection_change)

root = tk.Tk()
root.title("CSV and XML Processor")
root.geometry("800x600")

tk.Label(root, text="CSV File:").grid(row=0, column=0, pady=(10, 0), padx=10)
csv_entry = tk.Entry(root, width=60)
csv_entry.grid(row=0, column=1, pady=(10, 0))
tk.Button(root, text="Browse...", command=select_csv_file).grid(row=0, column=2, pady=(10, 0), padx=10)

tk.Label(root, text="XML File:").grid(row=1, column=0, pady=(10, 0), padx=10)
xml_entry = tk.Entry(root, width=60)
xml_entry.grid(row=1, column=1, pady=(10, 0))
tk.Button(root, text="Browse...", command=select_xml_file).grid(row=1, column=2, pady=(10, 0), padx=10)

# Variables selection frame
vars_frame = tk.LabelFrame(root, text="Select Variables", padx=10, pady=10)
vars_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), padx=10, sticky='nswe')

tk.Label(root, text="Final Save Path:").grid(row=3, column=0, pady=(10, 0), padx=10)
final_path_entry = tk.Entry(root, width=60)
final_path_entry.grid(row=3, column=1, pady=(10, 0))
tk.Button(root, text="Browse...", command=select_final_path).grid(row=3, column=2, pady=(10, 0), padx=10)

tk.Label(root, text="Final File Name (without .csv):").grid(row=4, column=0, pady=(10, 0), padx=10)
final_name_entry = tk.Entry(root, width=60)
final_name_entry.grid(row=4, column=1, pady=(10, 0))

tk.Button(root, text="Process Files", command=process_files).grid(row=5, column=1, pady=20)

selected_indices = []
xml_variables = []

# Make the window resizable
root.geometry("800x600")
root.grid_rowconfigure(2, weight=1)
root.grid_columnconfigure(1, weight=1)

root.mainloop()
