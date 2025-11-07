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
from io import TextIOWrapper


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

def create_final_file_tsdl_from_nested_zip(zip_path, xml_path, xml_variables, selected_indices, final_output, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl(xml_path, prefix)
    adjusted_indices = [i + 2 for i in selected_indices]
    if ana_limit_index is None:
        return

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=',')

            csv_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.csv.zip')],
                key=extract_datetime
            )

            metadata_written = False

            def process_csv_file(csv_file, encoding):
                nonlocal metadata_written
                text_stream = io.TextIOWrapper(csv_file, encoding=encoding)
                reader = csv.reader(text_stream, delimiter=';')

                first_line = next(reader, [])
                second_line = next(reader, [])
                _ = next(reader, [])

                if not metadata_written:
                    writer.writerow(first_line)
                    writer.writerow(second_line)
                    chosen_headers = ["Date", "Time"] + [
                        f"{xml_variables[idx][0]} {xml_variables[idx][1]}"
                        for idx in selected_indices
                    ]
                    cleaned_headers = [header.replace(',', '') for header in chosen_headers]
                    writer.writerow(cleaned_headers)
                    metadata_written = True

                for row in reader:
                    date_time = row[:2]
                    selected_values = []

                    for signal_index in adjusted_indices:
                        try:
                            if signal_index <= ana_limit_index:
                                value = row[signal_index]
                                selected_values.append(value)
                            else:
                                bit_source_index = (signal_index - 1 - ana_limit_index) // 16
                                bit_position = ((signal_index - 1 - ana_limit_index) % 16)
                                value_position = ana_limit_index + 1 + bit_source_index

                                if value_position >= len(row):
                                    selected_values.append('')
                                    continue

                                raw_value = row[value_position]
                                int_value = int(float(raw_value))
                                binary = f"{int_value:016b}"[::-1]
                                selected_bit = binary[bit_position]
                                selected_values.append(selected_bit)
                        except Exception:
                            selected_values.append('')

                    writer.writerow(date_time + selected_values)

            if csv_zip_files:
                for filename in csv_zip_files:
                    with outer_zip.open(filename) as nested_zip_bytes:
                        nested_zip_data = nested_zip_bytes.read()
                        with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                            for nested_file in nested_zip.infolist():
                                if nested_file.filename.lower().endswith('.csv'):
                                    try:
                                        with nested_zip.open(nested_file) as csv_file:
                                            process_csv_file(csv_file, 'utf-8')
                                    except UnicodeDecodeError:
                                        with nested_zip.open(nested_file) as csv_file:
                                            process_csv_file(csv_file, 'iso-8859-1')
            else:
                for file_info in outer_zip.infolist():
                    if file_info.filename.lower().endswith('.csv'):
                        try:
                            with outer_zip.open(file_info) as csv_file:
                                process_csv_file(csv_file, 'utf-8')
                        except UnicodeDecodeError:
                            with outer_zip.open(file_info) as csv_file:
                                process_csv_file(csv_file, 'iso-8859-1')

    except Exception as e:
        print(f"Error processing ZIPs: {e}")

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
    
def extract_datetime_opc(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})', filename)
    if match:
        date_str = match.group(1)
        hour_str = match.group(2)
        return datetime.strptime(f"{date_str}_{hour_str}", '%Y-%m-%d_%H')
    return datetime.min

def create_final_file_opc_from_nested_zip(zip_path, xml_path, xml_variables, selected_indices, final_output, prefix="ANA",mode_selected="CWE"):
    ana_limit_index = get_ana_limit_index_opc(xml_path, prefix)
    adjusted_indices = [i + 1 for i in selected_indices]  
    if ana_limit_index is None:
        print("ANA limit index not found. Aborting.")
        return

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=',')

            csv_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.zip')],
                key=extract_datetime_opc
            )

            metadata_written = False

            def process_csv(csv_file, encoding):
                nonlocal metadata_written
                text_stream = io.TextIOWrapper(csv_file, encoding=encoding)
                reader = csv.reader(text_stream, delimiter=',')

                _ = next(reader, [])  

                for row in reader:
                    try:
                        epoch_time = int(float(row[0]))
                        dt_obj = datetime.fromtimestamp(epoch_time, tz=timezone.utc)
                        formatted_dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                        selected_values = []

                        for signal_index in adjusted_indices:
                            try:
                                if signal_index <= ana_limit_index:
                                    value = row[signal_index]
                                    selected_values.append(value)
                                else:
                                    if mode_selected == "CWE":
                                        conversion_start_index = ana_limit_index * 2 + 1 #now ANA signals are written twice, if it ever changes, just remove the *2
                                    else:
                                        conversion_start_index = ana_limit_index + 1
                                    bit_source_index = (signal_index - 1 - ana_limit_index) // 16
                                    bit_position = ((signal_index - 1 - ana_limit_index) % 16)
                                    value_position = conversion_start_index + bit_source_index

                                    if value_position >= len(row):
                                        selected_values.append('')
                                        continue

                                    raw_value = row[value_position]
                                    int_value = int(float(raw_value))
                                    binary = f"{int_value:016b}"[::-1]
                                    selected_bit = binary[bit_position]
                                    selected_values.append(selected_bit)

                            except Exception:
                                selected_values.append('')

                        if not metadata_written:
                            chosen_headers = ["Date Time"] + [
                                f"{xml_variables[idx][0]} {xml_variables[idx][1]}"
                                for idx in selected_indices
                            ]
                            cleaned_headers = [header.replace(',', '') for header in chosen_headers]
                            writer.writerow(cleaned_headers)
                            metadata_written = True

                        writer.writerow([formatted_dt] + selected_values)

                    except ValueError:
                        continue

            if csv_zip_files:
                for filename in csv_zip_files:
                    with outer_zip.open(filename) as nested_zip_bytes:
                        nested_zip_data = nested_zip_bytes.read()
                        with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                            for nested_file in nested_zip.infolist():
                                if nested_file.filename.lower().endswith('.csv'):
                                    try:
                                        with nested_zip.open(nested_file) as csv_file:
                                            process_csv(csv_file, 'utf-8')
                                    except UnicodeDecodeError:
                                        with nested_zip.open(nested_file) as csv_file:
                                            process_csv(csv_file, 'iso-8859-1')
            else:
                for file_info in outer_zip.infolist():
                    if file_info.filename.lower().endswith('.csv'):
                        try:
                            with outer_zip.open(file_info) as csv_file:
                                process_csv(csv_file, 'utf-8')
                        except UnicodeDecodeError:
                            with outer_zip.open(file_info) as csv_file:
                                process_csv(csv_file, 'iso-8859-1')

    except Exception as e:
        print(f"Error processing ZIPs: {e}")

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

def create_final_file_tsdl_bin_from_nested_zip(zip_path, xml_path, xml_variables, selected_indices, final_output, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl_bin(xml_path, prefix)
    adjusted_indices = selected_indices
    if ana_limit_index is None:
        return

    num_ANA, num_ST, num_FM = get_ana_fm_st_number(xml_path, prefix)
    num_uint16_signals = num_ST + num_FM

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=',')

            bin_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.bin.zip')],
                key=extract_datetime
            )

            metadata_written = False
            printed_first_timestamp = False

            def process_bin(bin):
                nonlocal metadata_written, printed_first_timestamp

                raw = bin.read()
                first_newline = raw.find(b'\n')
                second_newline = raw.find(b'\n', first_newline + 1)
                if second_newline == -1:
                    return

                header_block = raw[:second_newline].decode('latin1', errors='replace').strip()
                data_only = BytesIO(raw[second_newline + 1:])

                if prefix == "ANA":
                    record_size = 6 + num_ANA * 4 + num_uint16_signals * 2
                else:
                    record_size = 6 + num_ANA * 4 + (num_uint16_signals + 48) * 2 #for now 48 signals (16bits combined into 1 int) are being written on WEA, if it ever changes just change the hardcoded 48

                while data_only.tell() + record_size <= len(data_only.getbuffer()):
                    chunk = data_only.read(record_size)

                    try:
                        timestamp_bytes = chunk[:6]
                        float_start = 6
                        float_end = float_start + num_ANA * 4
                        uint16_start = float_end

                        first_float_bytes = chunk[float_start:float_start + 4]
                        first_float = struct.unpack('<f', first_float_bytes)[0]

                        if not printed_first_timestamp:
                            printed_first_timestamp = True

                        float_data = decode_floats(chunk[float_start:float_end])
                        uint16_data = decode_uint16(chunk[uint16_start:])
                        timestamp = decode_custom_timestamp(timestamp_bytes)

                        date_time = timestamp.split(' ', 1)
                        date = date_time[0] if len(date_time) > 0 else ''
                        time = date_time[1] if len(date_time) > 1 else ''

                        selected_values = []
                        for signal_index in adjusted_indices:
                            try:
                                if signal_index < ana_limit_index:
                                    value = float_data[signal_index]
                                    selected_values.append(value)
                                else:
                                    bit_offset = signal_index - ana_limit_index
                                    bit_source_index = bit_offset // 16
                                    bit_position = bit_offset % 16

                                    if bit_source_index >= len(uint16_data):
                                        selected_values.append('')
                                        continue

                                    int_value = uint16_data[bit_source_index]
                                    binary = f"{int_value:016b}"[::-1]
                                    selected_bit = binary[bit_position]
                                    selected_values.append(selected_bit)
                            except Exception:
                                selected_values.append('')

                        if not metadata_written:
                            chosen_headers = ["Date", "Time"] + [
                                f"{xml_variables[idx][0]} {xml_variables[idx][1]}"
                                for idx in selected_indices
                            ]
                            cleaned_headers = [header.replace(',', '') for header in chosen_headers]
                            writer.writerow(cleaned_headers)
                            metadata_written = True

                        writer.writerow([date, time] + selected_values)

                    except Exception:
                        continue

            if bin_zip_files:
                for filename in bin_zip_files:
                    with outer_zip.open(filename) as nested_zip_bytes:
                        nested_zip_data = nested_zip_bytes.read()
                        with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                            for nested_file in nested_zip.infolist():
                                if nested_file.filename.lower().endswith('.bin'):
                                    with nested_zip.open(nested_file) as bin:
                                        process_bin(bin)
            else:
                for file_info in outer_zip.infolist():
                    if file_info.filename.lower().endswith('.bin'):
                        with outer_zip.open(file_info) as bin:
                            process_bin(bin)

    except Exception as e:
        print(f"Error processing ZIPs: {e}")

# ─────────────────────────────────────────────────────────── TSDL MFR FUNCTIONS ─────────────────────────────────────────────────────────────
def get_ana_limit_index_tsdl_mfr(xml_path, prefix="ANA"):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        headers = [param.attrib['id'] for param in root.findall('.//text')]
        signal_indices = [i for i, header in enumerate(headers) if header.startswith(prefix)]
        return max(signal_indices, default=0) 
    except Exception as e:
        print(f"Error reading XML: {e}")
        return None

def extract_datetime_mfr(filename):
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})', filename)
    if match:
        datetime_str = '_'.join(match.groups())
        return datetime.strptime(datetime_str, '%Y_%m_%d_%H_%M_%S')
    return datetime.min

def extract_base_timestamp_from_zip(zip_file):
    def search_cfg_in_zip(zf):
        for file_info in zf.infolist():
            if file_info.filename.lower().endswith('.cfg'):
                with zf.open(file_info) as config_file:
                    for line in TextIOWrapper(config_file, encoding='utf-8'):
                        line = line.strip()
                        try:
                            timestamp = datetime.strptime(line, "%d/%m/%Y,%H:%M:%S.%f")
                            return line 
                        except ValueError:
                            continue
        return None

    timestamp = search_cfg_in_zip(zip_file)
    if timestamp:
        return timestamp

    for file_info in zip_file.infolist():
        if file_info.filename.lower().endswith('.zip'):
            with zip_file.open(file_info) as nested_zip_bytes:
                nested_data = nested_zip_bytes.read()
                with zipfile.ZipFile(BytesIO(nested_data)) as nested_zip:
                    timestamp = search_cfg_in_zip(nested_zip)
                    if timestamp:
                        return timestamp

    raise ValueError("No config file with timestamp found in ZIP")

def create_final_file_tsdl_mfr(zip_path, xml_path, xml_variables, selected_indices, final_output, prefix="ANA"):
    ana_limit_index = get_ana_limit_index_tsdl_mfr(xml_path, prefix)
    adjusted_indices = [i + 1 for i in selected_indices]

    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            base_timestamp = extract_base_timestamp_from_zip(outer_zip)
            writer = csv.writer(outfile, delimiter=',')

            dat_zip_files = sorted(
                [f.filename for f in outer_zip.infolist() if f.filename.lower().endswith('.zip')],
                key=extract_datetime_mfr
            )

            headers_written = [False]

            def process_mfr(mfr, writer, xml_variables, adjusted_indices, base_timestamp_str, headers_written):
                reader = csv.reader(TextIOWrapper(mfr, encoding='utf-8'), delimiter=',')
                base_timestamp = datetime.strptime(base_timestamp_str, "%d/%m/%Y,%H:%M:%S.%f")
                current_timestamp = base_timestamp

                for row in reader:
                    if len(row) < max(adjusted_indices) + 1:
                        continue

                    if not headers_written[0]:
                        headers = ['Date', 'Time'] + [xml_variables[i][1].strip("()\"'") for i in selected_indices]
                        cleaned_headers = [header.replace(',', '') for header in headers]
                        writer.writerow(cleaned_headers)
                        headers_written[0] = True

                    selected_values = [row[i] for i in adjusted_indices]
                    date_str = current_timestamp.strftime("%d/%m/%Y")
                    time_str = current_timestamp.strftime("%H:%M:%S.%f")
                    writer.writerow([date_str, time_str] + selected_values)
                    current_timestamp += timedelta(microseconds=100)

            for filename in dat_zip_files:
                with outer_zip.open(filename) as nested_zip_bytes:
                    nested_zip_data = nested_zip_bytes.read()
                    with zipfile.ZipFile(BytesIO(nested_zip_data)) as nested_zip:
                        try:
                            base_timestamp = extract_base_timestamp_from_zip(nested_zip)
                        except ValueError as e:
                            continue

                        for nested_file in nested_zip.infolist():
                            if nested_file.filename.lower().endswith('.dat'):
                                with nested_zip.open(nested_file) as mfr:
                                    process_mfr(mfr, writer, xml_variables, adjusted_indices, base_timestamp, headers_written)

            else:
                for file_info in outer_zip.infolist():
                    if file_info.filename.lower().endswith('.dat'):
                        with outer_zip.open(file_info) as mfr:
                            process_mfr(mfr, writer, xml_variables, adjusted_indices, base_timestamp, headers_written)

    except Exception as e:
        print(f"Error processing ZIPs: {e}")

# ──────────────────────────────────────────────────────────────── GUI functions ─────────────────────────────────────────────────────────────

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
    search_var.trace_add("write", lambda *args: update_listbox()) 
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
        
        global selected_indices
        selected_indices = [i for i, (id, _) in enumerate(xml_variables) if id in selected_ids]

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

    if source_selected == "TSDL (Export CSV)":
        print("🔄 Processing and creating final file from TSDL (Export CSV) zip...")
        t0 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl_from_nested_zip(zip_path=zip_path,xml_path=xml_path,xml_variables=xml_variables,selected_indices=selected_indices,final_output=final_output_file,prefix=prefix)
        created_files.append(final_output_file)
        print(f"✅ Final file created in {time.time() - t0:.2f} seconds")
        if cancel_requested:
            return

    elif source_selected == "OPClogger" or source_selected == "MFR OPClogger":
        if source_selected == "OPClogger":
            print("🔄 Processing and creating final file from OPClogger zip...")
        else:
            print("🔄 Processing and creating final file from MFR OPClogger zip...")
        t0 = time.time()
        prefix = "ANA" if (mode_selected == "CWE" or mode_selected == "MFR")  else "TR"
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_opc_from_nested_zip(zip_path=zip_path,xml_path=xml_path,xml_variables=xml_variables,selected_indices=selected_indices,final_output=final_output_file,prefix=prefix, mode_selected = mode_selected)
        created_files.append(final_output_file)
        print(f"✅ Final file created in {time.time() - t0:.2f} seconds")
        if cancel_requested:
            return

    elif source_selected == "TSDL (Export)":
        print("🔄 Processing and creating final file from TSDL (Export) zip...")
        t0 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl_bin_from_nested_zip(zip_path=zip_path,xml_path=xml_path,xml_variables=xml_variables,selected_indices=selected_indices,final_output=final_output_file,prefix=prefix)
        created_files.append(final_output_file)
        print(f"✅ Final file created in {time.time() - t0:.2f} seconds")
        if cancel_requested:
            return
        
    elif source_selected == "MFR TSDL":
        print("🔄 Processing and creating final file from MFR TSDL zip...")
        t0 = time.time()
        prefix = "ANA" if mode_selected == "CWE" else "TR"
        final_output_file = os.path.join(final_path, f"{final_name}.csv")
        create_final_file_tsdl_mfr(zip_path=zip_path,xml_path=xml_path,xml_variables=xml_variables,selected_indices=selected_indices,final_output=final_output_file,prefix=prefix)
        created_files.append(final_output_file)
        print(f"✅ Final file created in {time.time() - t0:.2f} seconds")
        if cancel_requested:
            return

    else:
        messagebox.showerror("Error", f"Unknown source selected: {source_selected}")
        return

    messagebox.showinfo("Success", f"Final file '{final_output_file}' created successfully.")

def cancel_and_cleanup():
    global cancel_requested, processing_thread
    cancel_requested = True

    if processing_thread and processing_thread.is_alive():
        wait_time = 0
        while processing_thread.is_alive() and wait_time < 5:
            time.sleep(0.1)
            wait_time += 0.1

    gc.collect()
    messagebox.showinfo("Cancelled", "Processing was cancelled.")

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
root.title("Data Extraction Tool v5")
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
mode_var = ttk.Combobox(selector_frame, values=["CWE", "WEA","MFR"], state="readonly", width=10)
mode_var.grid(row=0, column=1, padx=(0, 8))
mode_var.set("CWE")

Label(selector_frame, text="Export:").grid(row=0, column=2, padx=(5, 5))
source_var = ttk.Combobox(selector_frame, values=["TSDL (Export CSV)","TSDL (Export)", "OPClogger","MFR OPClogger", "MFR TSDL"], state="readonly", width=16)
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
