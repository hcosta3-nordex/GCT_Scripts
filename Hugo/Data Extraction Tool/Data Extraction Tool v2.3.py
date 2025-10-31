import os
import csv
import zipfile
import shutil
import stat
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox, Listbox, ttk, END, Frame, StringVar
import time
import struct
import io
from io import BytesIO
import re
import threading
import gc

selected_ids = set()
selected_indices = []
xml_variables = []
filter_options = []
filter_signals = []
created_files = []
cancel_requested = False
processing_thread = None
filters = {}

# ─────────────────────────────────────────────────────────── TSDL CSV FUNCTIONS ─────────────────────────────────────────────────────────────

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
    
def extract_datetime(filename):
    match = re.search(r'(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y_%m_%d_%H_%M_%S')
    return datetime.min

def create_raw_file_tsdl_from_nested_zip(zip_path, xml_path, raw_output_file, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl(xml_path, prefix)
    if ana_limit_index is None:
        print("ANA limit index not found. Aborting.")
        return

    metadata_written = False

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(raw_output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=';')

            bin_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.csv.zip')],
                key=extract_datetime
            )

            for filename in bin_zip_files:
                with outer_zip.open(filename) as nested_zip_bytes:
                    nested_zip_data = nested_zip_bytes.read()
                    with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                        for nested_file in nested_zip.infolist():
                            if nested_file.filename.lower().endswith('.csv'):
                                try:
                                    with nested_zip.open(nested_file) as csv_file:
                                        text_stream = io.TextIOWrapper(csv_file, encoding='utf-8')
                                        reader = csv.reader(text_stream, delimiter=';')

                                        first_line = next(reader, [])
                                        second_line = next(reader, [])
                                        _ = next(reader, []) 

                                        if not metadata_written:
                                            writer.writerow(first_line)
                                            writer.writerow(second_line)
                                            metadata_written = True

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

                                except UnicodeDecodeError:
                                    with nested_zip.open(nested_file) as csv_file:
                                        text_stream = io.TextIOWrapper(csv_file, encoding='iso-8859-1')
                                        reader = csv.reader(text_stream, delimiter=';')

                                        first_line = next(reader, [])
                                        second_line = next(reader, [])
                                        _ = next(reader, []) 

                                        if not metadata_written:
                                            writer.writerow(first_line)
                                            writer.writerow(second_line)
                                            metadata_written = True

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
        print(f"Error processing nested ZIPs: {e}")

def create_final_file_tsdl(raw_file, xml_path, xml_variables, selected_indices, final_output):
    try:
        with open(raw_file, 'r', encoding='utf-8') as raw, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            raw_reader = csv.reader(raw, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            first_metadata = next(raw_reader, [])
            second_metadata = next(raw_reader, [])
            writer.writerow(first_metadata)
            writer.writerow(second_metadata)

            if not selected_indices:
                return

            chosen_headers = ["Date", "Time"] + [f"{xml_variables[idx][0]} {xml_variables[idx][1]}" for idx in selected_indices]
            adjusted_indices = [0, 1] + [idx + 2 for idx in selected_indices]
            writer.writerow(chosen_headers)

            for raw_row in raw_reader:
                filtered_data = [raw_row[idx] for idx in adjusted_indices]
                writer.writerow(filtered_data)

    except Exception as e:
        print(f"Error creating final file: {e}")
        
# ─────────────────────────────────────────────────────────── OPCLOGGER ──────────────────────────────────────────────────────────────────────

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

def create_raw_file_opc_from_nested_zip(zip_path, xml_path, raw_output_file, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_opc(xml_path, prefix)
    if ana_limit_index is None:
        print("ANA limit index not found. Aborting.")
        return

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(raw_output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=',')

            csv_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.zip')],
                key=extract_datetime
            )

            for filename in csv_zip_files:
                with outer_zip.open(filename) as nested_zip_bytes:
                    nested_zip_data = nested_zip_bytes.read()
                    with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                        for nested_file in nested_zip.infolist():
                            if nested_file.filename.lower().endswith('.csv'):
                                try:
                                    with nested_zip.open(nested_file) as csv_file:
                                        text_stream = io.TextIOWrapper(csv_file, encoding='utf-8')
                                        reader = csv.reader(text_stream, delimiter=',')

                                        _ = next(reader, []) 

                                        for row in reader:
                                            try:
                                                epoch_time = int(float(row[0]))
                                                dt_obj = datetime.fromtimestamp(epoch_time, tz=timezone.utc)
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

                                except UnicodeDecodeError:
                                    with nested_zip.open(nested_file) as csv_file:
                                        text_stream = io.TextIOWrapper(csv_file, encoding='iso-8859-1')
                                        reader = csv.reader(text_stream, delimiter=',')

                                        _ = next(reader, []) 

                                        for row in reader:
                                            try:
                                                epoch_time = int(float(row[0]))
                                                dt_obj = datetime.fromtimestamp(epoch_time, tz=timezone.utc)
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
        print(f"Error processing nested ZIPs: {e}")

def create_final_file_opc(combined_csv, raw_file, xml_variables, selected_indices, final_output):
    try:
        with open(raw_file, 'r', encoding='utf-8') as raw, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            raw_reader = csv.reader(raw, delimiter=',')
            writer = csv.writer(outfile, delimiter=';')
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

# ─────────────────────────────────────────────────────────── TSDL BIN FUNCTIONS ─────────────────────────────────────────────────────────────

def get_ana_limit_index_tsdl_bin(xml_path, prefix="ANA"):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        headers = [param.attrib['id'] for param in root.findall('.//text')]
        signal_indices = [i for i, header in enumerate(headers) if header.startswith(prefix)]
        return max(signal_indices, default=0) + 1
    except Exception as e:
        print(f"Error reading XML: {e}")
        return None
    
def get_ana_fm_st_number(xml_path,prefix):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    headers = [param.attrib['id'] for param in root.findall('.//text')]
    num_ANA = sum(1 for h in headers if h.startswith(prefix))
    num_ST = sum(1 for h in headers if h.startswith("ST"))
    num_ST = int(num_ST / 16)
    num_FM = sum(1 for h in headers if h.startswith("FM"))
    num_FM = int(num_FM / 16)
    return num_ANA, num_ST, num_FM

def decode_custom_timestamp(chunk):
    seconds = int.from_bytes(chunk[:4], byteorder='little')
    millis = int.from_bytes(chunk[4:], byteorder='little')
    base = datetime(2010, 1, 1, tzinfo=timezone.utc)
    dt = base + timedelta(seconds=seconds, milliseconds=millis)
    return dt.strftime('%Y-%m-%d %H:%M:%S.') + f"{dt.microsecond // 1000:03d}"

def decode_floats(chunk):
    return [round(struct.unpack('<f', chunk[i:i+4])[0], 8) for i in range(0, len(chunk), 4)]

def decode_uint16(chunk):
    return [struct.unpack('<H', chunk[i:i+2])[0] for i in range(0, len(chunk), 2)]

def process_hybrid_bin(bin_stream, writer, num_ANA, num_ST, num_FM,prefix):
    num_float_signals = num_ANA
    num_uint16_signals = num_ST + num_FM
    if prefix == "ANA":
        record_size = 6 + num_float_signals * 4 + num_uint16_signals * 2
    else:
        record_size = 6 + num_float_signals * 4 + (num_uint16_signals + 48) * 2 #for now 48 signals (16bits combined into 1 int) are being written, if it ever changes just change the hardcoded 48

    raw = bin_stream.read()

    header_end = raw.find(b'\n')
    if header_end == -1:
        return

    header_line = raw[:header_end].decode('latin1').strip()
    header = header_line.split(',')

    data = raw[header_end + 1:]

    offset = 0
    record_count = 0
    while offset + record_size <= len(data):
        chunk = data[offset:offset + record_size]

        timestamp = decode_custom_timestamp(chunk[:6])
        float_data = decode_floats(chunk[6:6 + num_float_signals * 4])
        uint16_data = decode_uint16(chunk[6 + num_float_signals * 4:])
        writer.writerow([timestamp] + float_data + uint16_data)

        offset += record_size
        record_count += 1

def create_raw_file_tsdl_bin_from_nested_zip(zip_path, xml_path, raw_output_file, num_ANA, num_ST, num_FM, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl_bin(xml_path, prefix)
    if ana_limit_index is None:
        print("ANA limit index not found. Aborting.")
        return

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(raw_output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')

            bin_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.bin.zip')],
                key=extract_datetime
            )

            for filename in bin_zip_files:
                with outer_zip.open(filename) as nested_zip_bytes:
                    nested_zip_data = nested_zip_bytes.read()
                    with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                        for nested_file in nested_zip.infolist():
                            if nested_file.filename.lower().endswith('.bin'):
                                with nested_zip.open(nested_file) as bin_stream:
                                    raw = bin_stream.read()
                                    header_end = raw.find(b'\n')
                                    if header_end == -1:
                                        continue
                                    data_only = BytesIO(raw[header_end + 1:])
                                    process_hybrid_bin(data_only, writer, num_ANA, num_ST, num_FM, prefix)

    except Exception as e:
        print(f"Error processing nested ZIPs: {e}")

def create_final_file_tsdl_bin(raw_file, xml_variables, selected_indices, final_output):
    try:
        with open(raw_file, 'r', encoding='utf-8') as raw, \
             open(final_output, 'w', encoding='utf-8', newline='') as outfile:

            raw_reader = csv.reader(raw, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            if not selected_indices:
                print("No selected indices provided.")
                return

            # Write header
            chosen_headers = ["Date", "Time"] + [
                f"{xml_variables[idx][0]} {xml_variables[idx][1]}" for idx in selected_indices
            ]
            writer.writerow(chosen_headers)

            # Read first row for structure validation
            first_line = next(raw_reader, None)
            if not first_line:
                print("Raw file is empty.")
                return

            print(f"First raw row: {first_line}")

            # Validate selected indices
            max_required_index = max([idx + 1 for idx in selected_indices])
            if max_required_index >= len(first_line):
                print("❌ One or more selected indices are out of bounds.")
                return

            # Write first row
            date_time = first_line[0].split(' ', 1)
            date = date_time[0] if len(date_time) > 0 else ''
            time = date_time[1] if len(date_time) > 1 else ''
            selected_data = [first_line[idx + 1] for idx in selected_indices]
            writer.writerow([date, time] + selected_data)

            # Write remaining rows
            for raw_row in raw_reader:
                if len(raw_row) <= max_required_index + 1:
                    continue  # Skip malformed rows

                date_time = raw_row[0].split(' ', 1)
                date = date_time[0] if len(date_time) > 0 else ''
                time = date_time[1] if len(date_time) > 1 else ''
                selected_data = [raw_row[idx + 1] for idx in selected_indices]
                writer.writerow([date, time] + selected_data)

    except Exception as e:
        print(f"Error creating final file: {e}")

# ──────────────────────────────────────────────────────────────── GUI functions ─────────────────────────────────────────────────────────────

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
        result = []
        for param in root.findall('.//text'):
            param_id = param.attrib.get('id', '')
            if param_id.startswith('P'):
                break 
            result.append((param_id, param.text.strip()))
        return result
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
    global xml_variables, var_listbox, search_var
    xml_path = xml_entry.get()
    xml_variables = get_xml_variables(xml_path)
    if not xml_variables:
        return

    for widget in vars_frame.winfo_children():
        widget.destroy()

    search_var = StringVar()
    search_var.trace_add("write", lambda *args: update_listbox())  # <-- This line triggers updates
    search_entry = Entry(vars_frame, textvariable=search_var)
    search_entry.pack(fill='x', padx=5, pady=(0, 5))

    scrollbar = ttk.Scrollbar(vars_frame)
    scrollbar.pack(side='right', fill='y')

    var_listbox = Listbox(vars_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
    var_listbox.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=var_listbox.yview)

    full_variable_list = [f"{var[0]}: {var[1]}" for var in xml_variables]

    def update_listbox():
        query = search_var.get().strip().lower()
        var_listbox.delete(0, 'end')
        visible_items = []

        for item in full_variable_list:
            if query in item.lower():
                var_listbox.insert('end', item)
                visible_items.append(item)

        for i, item in enumerate(visible_items):
            var_id = item.split(":")[0].strip()
            if var_id in selected_ids:
                var_listbox.selection_set(i)

    update_listbox()

    def on_selection_change(event):
        visible_items = [var_listbox.get(i) for i in range(var_listbox.size())]
        visible_ids = {item.split(":")[0].strip() for item in visible_items}

        for var_id in visible_ids:
            selected_ids.discard(var_id)

        for i in var_listbox.curselection():
            item = var_listbox.get(i)
            var_id = item.split(":")[0].strip()
            selected_ids.add(var_id)

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

def start_processing_thread():
    global cancel_requested, processing_thread
    cancel_requested = False
    processing_thread = threading.Thread(target=process_files)
    processing_thread.start()

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

    if source_selected == "TSDL (Export CSV)":
        print("⏳ Processing nested ZIP files...")
        t0 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        raw_output_file = os.path.join(final_path, "raw_file.csv")

        create_raw_file_tsdl_from_nested_zip(zip_path, xml_path, raw_output_file, prefix)
        created_files.append(raw_output_file)
        print(f"✅ Raw file created in {time.time() - t0:.2f} seconds")
        if cancel_requested: return

        print("🔄 Creating final file...")
        t1 = time.time()
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl(raw_output_file, raw_output_file, xml_variables, selected_indices, final_output_file)
        created_files.append(final_output_file)
        print(f"✅ Final file created in {time.time() - t1:.2f} seconds")
        if cancel_requested: return

    elif source_selected == "OPClogger":
        print("⏳ Processing nested ZIP files...")
        t0 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        raw_output_file = os.path.join(final_path, "raw_file.csv")

        create_raw_file_opc_from_nested_zip(zip_path, xml_path, raw_output_file, prefix)
        created_files.append(raw_output_file)
        if cancel_requested: return
        print(f"✅ Raw file created in {time.time() - t0:.2f} seconds")

        print("🔄 Creating final file...")
        t1 = time.time()
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_opc(raw_output_file, raw_output_file, xml_variables, selected_indices, final_output_file)
        created_files.append(final_output_file)
        if cancel_requested: return
        print(f"✅ Final file created in {time.time() - t1:.2f} seconds")

    elif source_selected == "TSDL (Export)":
        print("⏳ Processing nested binary ZIP files...")
        t1 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        num_ANA, num_ST, num_FM = get_ana_fm_st_number(xml_path, prefix)
        raw_output_file = os.path.join(final_path, "raw_file.csv")

        create_raw_file_tsdl_bin_from_nested_zip(zip_path, xml_path, raw_output_file, num_ANA, num_ST, num_FM, prefix)
        created_files.append(raw_output_file)
        if cancel_requested: return
        print(f"✅ Raw file created in {time.time() - t1:.2f} seconds")

        print("🔄 Creating final file...")
        t2 = time.time()
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl_bin(raw_output_file, xml_variables, selected_indices, final_output_file)
        created_files.append(final_output_file)
        if cancel_requested: return
        print(f"✅ Final file created in {time.time() - t2:.2f} seconds")

    else:
        messagebox.showerror("Error", f"Unknown source selected: {source_selected}")
        return

    messagebox.showinfo("Success", f"Final file '{final_output_file}' created successfully.")
    try:
        #os.remove(combined_csv_path)
        os.remove(raw_output_file)
    except Exception as e:
        print(f"Error deleting temporary files: {e}")

def cancel_and_cleanup():
    global cancel_requested, processing_thread
    cancel_requested = True

    if processing_thread and processing_thread.is_alive():
        processing_thread.join(timeout=5)

    gc.collect()
    time.sleep(1) 

    deleted = []

    def safe_delete(path, retries=30, delay=0.5):
        for attempt in range(retries):
            try:
                if os.path.exists(path):
                    os.remove(path)
                    return True
            except PermissionError:
                time.sleep(delay)

        if os.path.exists(path):
            print(f"Error deleting {path}: file may still be in use.")
        return False


    for file_path in created_files:
        if safe_delete(file_path):
            deleted.append(file_path)

    extract_dir = "extracted_files"
    if os.path.exists(extract_dir):
        for _ in range(5):
            try:
                shutil.rmtree(extract_dir)
                deleted.append(extract_dir)
                break
            except PermissionError:
                time.sleep(0.5)
            except Exception as e:
                print(f"Error deleting folder {extract_dir}: {e}")
                break

    created_files.clear()
    messagebox.showinfo("Cancelled", f"Deleted {len(deleted)} item(s).")

def save_filter_to_file(filter_name):
    global filter_options, filter_signals

    if not filter_name:
        messagebox.showwarning("Missing Name", "Please enter a filter name.")
        return

    if not selected_ids:
        messagebox.showwarning("No Selection", "Please select at least one variable.")
        return

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "Filters.txt")

        if not os.path.exists(file_path):
            lines = ["Manual\n"]
        else:
            with open(file_path, "r") as f:
                lines = [line.strip() for line in f.readlines()]

        header = lines[0].split(",") if lines else ["Manual"]
        rows = lines[1:] if len(lines) > 1 else []

        while len(rows) < len(header):
            rows.append("")

        if filter_name in header:
            index = header.index(filter_name)
            rows[index] = ",".join(selected_ids)
        else:
            header.append(filter_name)
            rows.append(",".join(selected_ids))

        new_lines = [",".join(header) + "\n"] + [row + "\n" for row in rows]

        with open(file_path, "w") as f:
            f.writelines(new_lines)

        messagebox.showinfo("Success", f"Filter '{filter_name}' saved successfully.")
        load_filters()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to save filter: {e}")

def delete_filter(filter_name):
    if not filter_name or filter_name == "Manual":
        messagebox.showwarning("Invalid Filter", "Please enter a valid filter name to delete.")
        return

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "Filters.txt")

        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"'Filters.txt' not found in: {script_dir}")
            return

        with open(file_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        header = lines[0].split(",")
        rows = lines[1:]

        if filter_name not in header:
            messagebox.showerror("Error", f"Filter '{filter_name}' not found.")
            return

        index = header.index(filter_name)
        header.pop(index)
        if index < len(rows):
            rows.pop(index)

        with open(file_path, "w") as f:
            f.write(",".join(header) + "\n")
            for row in rows:
                f.write(row + "\n")

        messagebox.showinfo("Deleted", f"Filter '{filter_name}' deleted successfully.")
        load_filters()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete filter: {e}")

# ──────────────────────────────────────────────────────────────── GUI Window ────────────────────────────────────────────────────────────────
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
selector_frame.grid(row=2, column=1, padx=(100, 0), pady=(5, 0), sticky='w') 

Label(selector_frame, text="Source:").grid(row=0, column=0, padx=(0, 5))
mode_var = ttk.Combobox(selector_frame, values=["CWE", "WEA"], state="readonly", width=10)
mode_var.grid(row=0, column=1, padx=(0, 8))
mode_var.set("CWE")

Label(selector_frame, text="Export:").grid(row=0, column=2, padx=(5, 5))
source_var = ttk.Combobox(selector_frame, values=["TSDL (Export CSV)","TSDL (Export)", "OPClogger"], state="readonly", width=16)
source_var.grid(row=0, column=3, padx=(0, 0))
source_var.set("TSDL (Export CSV)")

filter_search_frame = Frame(root)
filter_search_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="ew")
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)

Label(filter_search_frame, text="Apply Filter:").grid(row=0, column=0, padx=(170, 5), sticky="e")

filter_var = ttk.Combobox(filter_search_frame, state="readonly", width=20)
filter_var.grid(row=0, column=1, padx=(0, 10))

Button(filter_search_frame, text="Load Filters", command=load_filters).grid(row=0, column=2, padx=(0, 10))

Label(filter_search_frame, text="Filter Name:").grid(row=0, column=3, padx=(10, 5), sticky="e")

filter_name_entry = Entry(filter_search_frame, width=20)
filter_name_entry.grid(row=0, column=4, padx=(0, 10))

Button(filter_search_frame, text="Save Filter", command=lambda: save_filter_to_file(filter_name_entry.get())).grid(row=0, column=5, padx=(0, 10))

Button(filter_search_frame,text="Delete Filter",command=lambda: delete_filter(filter_name_entry.get())).grid(row=0, column=6, padx=(0, 10))

Label(root, text="Select Variables:").grid(row=4, column=0, pady=(10, 0), padx=10)
vars_frame = Frame(root)
vars_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), padx=10, sticky="nsew")
root.grid_rowconfigure(4, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)

Label(root, text="Final Output Path:").grid(row=5, column=0, pady=(10, 0), padx=10)
final_path_entry = Entry(root, width=60)
final_path_entry.grid(row=5, column=1, pady=(10, 0))
Button(root, text="Browse...", command=lambda: [final_path_entry.delete(0, END), final_path_entry.insert(0, filedialog.askdirectory())]).grid(row=5, column=2, pady=(10, 0), padx=10)

Label(root, text="Final File Name (without .csv):").grid(row=6, column=0, pady=(10, 0), padx=10)
final_name_entry = Entry(root, width=60)
final_name_entry.grid(row=6, column=1, pady=(10, 0))

button_frame = Frame(root)
button_frame.grid(row=7, column=1, pady=(20, 10))
Button(button_frame, text="Process Files", command=start_processing_thread).grid(row=0, column=0, padx=(0, 10))
Button(button_frame, text="Cancel", command=cancel_and_cleanup).grid(row=0, column=1)

load_filters()

root.mainloop()