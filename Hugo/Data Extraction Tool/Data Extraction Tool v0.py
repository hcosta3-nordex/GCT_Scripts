import os
import csv
import zipfile
import shutil
import stat
import xml.etree.ElementTree as ET
from datetime import datetime
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox, Listbox, ttk, END
import time

selected_indices = []
xml_variables = []
filter_options = []
filter_signals = []

# ─────────────────────────────────────────────────────────── TSDL FUNCTIONS ─────────────────────────────────────────────────────────────

def get_ana_limit_index_tsdl(xml_path, prefix="ANA"):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        headers = [param.attrib['id'] for param in root.findall('.//text')]
        signal_indices = [i for i, header in enumerate(headers) if header.startswith(prefix)]
        return max(signal_indices, default=0) + 2
    except Exception as e:
        print(f"Error reading XML: {e}")
        return None

def combine_csv_tsdl(extract_to, output_file):
    metadata_written = False
    headers_written = False
    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=';')
        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, newline='', encoding='utf-8') as infile:
                            reader = csv.reader(infile, delimiter=';')
                            first_line = next(reader, [])
                            second_line = next(reader, [])
                            headers = next(reader, [])
                            if not metadata_written:
                                writer.writerow(first_line)
                                writer.writerow(second_line)
                                metadata_written = True
                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True
                            for row in reader:
                                writer.writerow(row)
                    except UnicodeDecodeError:
                        with open(file_path, newline='', encoding='iso-8859-1') as infile:
                            reader = csv.reader(infile, delimiter=';')
                            first_line = next(reader, [])
                            second_line = next(reader, [])
                            headers = next(reader, [])
                            if not metadata_written:
                                writer.writerow(first_line)
                                writer.writerow(second_line)
                                metadata_written = True
                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True
                            for row in reader:
                                writer.writerow(row)

def create_raw_file_tsdl(combined_csv, xml_path, raw_output_file, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl(xml_path, prefix)
    if ana_limit_index is None:
        return
    try:
        with open(combined_csv, 'r', encoding='utf-8') as infile, open(raw_output_file, 'w', encoding='utf-8', newline='') as outfile:
            reader = csv.reader(infile, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')
            for _ in range(3):
                next(reader)
            for row in reader:
                raw_data = row[:ana_limit_index+1]
                binary_values = []
                for value in row[ana_limit_index+1:]:
                    try:
                        int_value = int(float(value))
                        binary_representation = f"{int_value:016b}"[::-1]
                        binary_values.extend(binary_representation)
                    except ValueError:
                        continue
                raw_data.extend(binary_values)
                writer.writerow(raw_data)
    except Exception as e:
        print(f"Error processing raw file: {e}")

def create_final_file_tsdl(combined_csv, raw_file, xml_variables, selected_indices, final_output):
    try:
        with open(combined_csv, 'r', encoding='utf-8') as combined, open(raw_file, 'r', encoding='utf-8') as raw, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            combined_reader = csv.reader(combined, delimiter=';')
            raw_reader = csv.reader(raw, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')
            first_metadata = next(combined_reader, [])
            second_metadata = next(combined_reader, [])
            if not selected_indices:
                return
            chosen_headers = ["Date", "Time"] + [f"{xml_variables[idx][0]} {xml_variables[idx][1]}" for idx in selected_indices]
            adjusted_indices = [0, 1] + [idx + 2 for idx in selected_indices]
            writer.writerow(first_metadata)
            writer.writerow(second_metadata)
            writer.writerow(chosen_headers)
            for raw_row in raw_reader:
                filtered_data = [raw_row[idx] for idx in adjusted_indices]
                writer.writerow(filtered_data)
    except Exception as e:
        print(f"Error creating final file: {e}")

# ─────────────────────────────────────────────────────────── OPCLOGGER ──────────────────────────────────────────────────────────────────

def get_ana_limit_index_opc(xml_path,prefix="ANA"):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        headers = [param.attrib['id'] for param in root.findall('.//text')]
        ana_indices = [i for i, header in enumerate(headers) if header.startswith(prefix)]
        return max(ana_indices, default=0) + 1
    except Exception as e:
        print(f"Error reading XML: {e}")
        return None

def combine_csv_opc(extract_to, output_file):
    headers_written = False
    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=',')
        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, newline='', encoding='utf-8') as infile:
                            reader = csv.reader(infile, delimiter=',')
                            headers = next(reader, [])
                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True
                            for row in reader:
                                writer.writerow(row)
                    except UnicodeDecodeError:
                        with open(file_path, newline='', encoding='iso-8859-1') as infile:
                            reader = csv.reader(infile, delimiter=',')
                            headers = next(reader, [])
                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True
                            for row in reader:
                                writer.writerow(row)

def create_raw_file_opc(combined_csv, xml_path, raw_output_file,prefix="ANA"):
    ana_limit_index = get_ana_limit_index_opc(xml_path,prefix)
    if ana_limit_index is None:
        return
    try:
        with open(combined_csv, 'r', encoding='utf-8') as infile, open(raw_output_file, 'w', encoding='utf-8', newline='') as outfile:
            reader = csv.reader(infile, delimiter=',')
            writer = csv.writer(outfile, delimiter=',')
            headers = next(reader)
            for row in reader:
                try:
                    epoch_time = int(float(row[0]))
                    dt_obj = datetime.utcfromtimestamp(epoch_time)
                    formatted_dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                    raw_data = [formatted_dt] + row[1:ana_limit_index+1]
                    conversion_start_index = ana_limit_index * 2 + 1
                    binary_values = []
                    for value in row[conversion_start_index:]:
                        try:
                            int_value = int(float(value))
                            binary_representation = f"{int_value:016b}"[::-1]
                            binary_values.extend(binary_representation)
                        except ValueError:
                            continue
                    raw_data.extend(binary_values)
                    writer.writerow(raw_data)
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error processing raw file: {e}")

def create_final_file_opc(combined_csv, raw_file, xml_variables, selected_indices, final_output):
    try:
        with open(raw_file, 'r', encoding='utf-8') as raw, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            raw_reader = csv.reader(raw, delimiter=',')
            writer = csv.writer(outfile, delimiter=',')
            first_row = next(raw_reader, None)
            if not selected_indices or not first_row:
                return
            adjusted_indices = [idx + 1 for idx in selected_indices]
            chosen_headers = ["Date Time"] + [f"{xml_variables[idx][0]} {xml_variables[idx][1]}" for idx in selected_indices]
            writer.writerow(chosen_headers)
            writer.writerow([first_row[0]] + [first_row[idx] for idx in adjusted_indices])
            for raw_row in raw_reader:
                writer.writerow([raw_row[0]] + [raw_row[idx] for idx in adjusted_indices])
    except Exception as e:
        print(f"Error creating final file: {e}")

# ──────────────────────────────────────────────────────────────── GUI functions ─────────────────────────────────────────────────────────

def extract_nested_zip(zipped_file, extract_to='.'):
    try:
        if not zipfile.is_zipfile(zipped_file):
            return
        with zipfile.ZipFile(zipped_file, 'r') as zfile:
            zfile.extractall(path=extract_to)
            for filename in zfile.namelist():
                nested_file_path = os.path.join(extract_to, filename)
                if zipfile.is_zipfile(nested_file_path):
                    extract_nested_zip(nested_file_path, extract_to)
    except Exception as e:
        print(f"Error extracting {zipped_file}: {e}")

def delete_extracted_files(extract_to):
    if os.path.exists(extract_to):
        try:
            shutil.rmtree(extract_to, onerror=lambda func, path, _: os.chmod(path, stat.S_IWRITE) or func(path))
        except Exception as e:
            print(f"Error deleting {extract_to}: {e}")

def get_xml_variables(path_xml):
    try:
        tree = ET.parse(path_xml)
        root = tree.getroot()
        return [(param.attrib['id'], param.text.strip()) for param in root.findall('.//text')]
    except Exception as e:
        print(f"Error reading XML: {e}")
        return []

def load_filters():
    global filter_options, filter_signals
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "Filters.txt")
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"'Filters.txt' not found in: {script_dir}")
        return
    try:
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            filter_options = ["Manual"] + lines[0].split(',')
            filter_signals = [[]] + [line.split(',') for line in lines[1:]]
            filter_var['values'] = filter_options
            filter_var.set("Manual")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load Filters.txt: {e}")

def update_variable_choices():
    global xml_variables
    xml_path = xml_entry.get()
    xml_variables = get_xml_variables(xml_path)
    if not xml_variables:
        return

    for widget in vars_frame.winfo_children():
        widget.destroy()

    scrollbar = ttk.Scrollbar(vars_frame)
    scrollbar.pack(side='right', fill='y')

    var_listbox = Listbox(vars_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
    for var in xml_variables:
        var_listbox.insert('end', f"{var[0]}: {var[1]}")
    var_listbox.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=var_listbox.yview)

    def on_selection_change(event):
        global selected_indices
        selected_indices = var_listbox.curselection()

    var_listbox.bind('<<ListboxSelect>>', on_selection_change)

    def apply_filter_selection():
        selected_filter = filter_var.get()
        if not selected_filter or not xml_variables:
            return
        try:
            index = filter_options.index(selected_filter)
            if index == 0:
                return
            signals_to_select = filter_signals[index]
            matching_indices = [i for i, (id, _) in enumerate(xml_variables) if id in signals_to_select]
            var_listbox.selection_clear(0, 'end')
            for idx in matching_indices:
                var_listbox.selection_set(idx)
            global selected_indices
            selected_indices = matching_indices
        except Exception as e:
            print(f"Error applying filter: {e}")

    filter_var.bind("<<ComboboxSelected>>", lambda e: apply_filter_selection())

def process_files():
    zip_path = zip_path_entry.get()
    xml_path = xml_entry.get()
    final_path = final_path_entry.get()
    final_name = final_name_entry.get()
    mode_selected = mode_var.get()
    source_selected = source_var.get()

    if not zip_path or not xml_path or not final_path or not final_name:
        messagebox.showerror("Error", "Please select all required files and enter a final name.")
        return

    extract_to = "extracted_files"

    print("⏳ Extracting ZIP files...")
    t0 = time.time()
    extract_nested_zip(zip_path, extract_to)
    print(f"✅ Extraction completed in {time.time() - t0:.2f} seconds")

    if source_selected == "TSDL (Export CSV)":
        print("🔄 Combining CSV files...")
        t1 = time.time()
        combined_csv_path = os.path.join(final_path, "combined.csv")
        combine_csv_tsdl(extract_to, combined_csv_path)
        print(f"✅ Combined in {time.time() - t1:.2f} seconds")

        delete_extracted_files(extract_to)

        print("🔄 Creating raw file...")
        t2 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        raw_output_file = os.path.join(final_path, "raw_file.csv")
        create_raw_file_tsdl(combined_csv_path, xml_path, raw_output_file, prefix)
        print(f"✅ Raw file created in {time.time() - t2:.2f} seconds")

        print("🔄 Creating final file...")
        t3 = time.time()
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl(combined_csv_path, raw_output_file, xml_variables, selected_indices, final_output_file)
        print(f"✅ Final file created in {time.time() - t3:.2f} seconds")

    elif source_selected == "OPClogger":
        print("🔄 Combining CSV files...")
        t1 = time.time()
        combined_csv_path = os.path.join(final_path, "combined_opc.csv")
        combine_csv_opc(extract_to, combined_csv_path)
        print(f"✅ Combined in {time.time() - t1:.2f} seconds")

        delete_extracted_files(extract_to)

        print("🔄 Creating raw file...")
        t2 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        raw_output_file = os.path.join(final_path, "raw_opc.csv")
        create_raw_file_opc(combined_csv_path, xml_path, raw_output_file, prefix)
        print(f"✅ Raw file created in {time.time() - t2:.2f} seconds")

        print("🔄 Creating final file...")
        t3 = time.time()
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_opc(combined_csv_path, raw_output_file, xml_variables, selected_indices, final_output_file)
        print(f"✅ Final file created in {time.time() - t3:.2f} seconds")

    else:
        messagebox.showerror("Error", f"Unknown source selected: {source_selected}")
        return

    messagebox.showinfo("Success", f"Final file '{final_output_file}' created successfully.")
    try:
        os.remove(combined_csv_path)
        os.remove(raw_output_file)
    except Exception as e:
        print(f"Error deleting temporary files: {e}")

# ──────────────────────────────────────────────────────────────── GUI Window ────────────────────────────────────────────────────────────
root = Tk()
root.title("Data Extraction Tool")
root.geometry("1000x600")

Label(root, text="ZIP File:").grid(row=0, column=0, pady=(10, 0), padx=10)
zip_path_entry = Entry(root, width=60)
zip_path_entry.grid(row=0, column=1, pady=(10, 0))
Button(root, text="Browse...", command=lambda: [zip_path_entry.delete(0, END), zip_path_entry.insert(0, filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")]))]).grid(row=0, column=2, pady=(10, 0), padx=10)

Label(root, text="XML File:").grid(row=1, column=0, pady=(10, 0), padx=10)
xml_entry = Entry(root, width=60)
xml_entry.bind("<FocusOut>", lambda e: update_variable_choices())
xml_entry.grid(row=1, column=1, pady=(10, 0))
Button(root, text="Browse...", command=lambda: [xml_entry.delete(0, END), xml_entry.insert(0, filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])), update_variable_choices()]).grid(row=1, column=2, pady=(10, 0), padx=10)

selector_frame = ttk.Frame(root)
selector_frame.grid(row=2, column=1, padx=(210, 0), pady=(5, 0), sticky='w') 

Label(selector_frame, text="Source:").grid(row=0, column=0, padx=(0, 5))
mode_var = ttk.Combobox(selector_frame, values=["CWE", "WEA"], state="readonly", width=10)
mode_var.grid(row=0, column=1, padx=(0, 8))
mode_var.set("CWE")

Label(selector_frame, text="Export:").grid(row=0, column=2, padx=(5, 5))
source_var = ttk.Combobox(selector_frame, values=["TSDL (Export CSV)", "OPClogger"], state="readonly", width=16)
source_var.grid(row=0, column=3, padx=(0, 0))
source_var.set("TSDL (Export CSV)")

Label(root, text="Apply Filter:").grid(row=3, column=0, pady=(10, 0), padx=10)
filter_var = ttk.Combobox(root, state="readonly", width=20)
filter_var.grid(row=3, column=1, pady=(10, 0), sticky="w")
filter_var.set("Manual")

Label(root, text="Select Variables:").grid(row=4, column=0, pady=(10, 0), padx=10)
vars_frame = ttk.Frame(root)
vars_frame.grid(row=4, column=1, columnspan=2, pady=(10, 0), padx=10, sticky="nsew")
root.grid_rowconfigure(4, weight=1)
root.grid_columnconfigure(1, weight=1)

Label(root, text="Final Output Path:").grid(row=5, column=0, pady=(10, 0), padx=10)
final_path_entry = Entry(root, width=60)
final_path_entry.grid(row=5, column=1, pady=(10, 0))
Button(root, text="Browse...", command=lambda: [final_path_entry.delete(0, END), final_path_entry.insert(0, filedialog.askdirectory())]).grid(row=5, column=2, pady=(10, 0), padx=10)

Label(root, text="Final File Name (without .csv):").grid(row=6, column=0, pady=(10, 0), padx=10)
final_name_entry = Entry(root, width=60)
final_name_entry.grid(row=6, column=1, pady=(10, 0))

Button(root, text="Process Files", command=process_files).grid(row=7, column=1, pady=(20, 10))

load_filters()

root.mainloop()
