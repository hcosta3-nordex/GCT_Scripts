import os
import csv
import zipfile
import shutil
import stat
import re
from datetime import datetime
import xml.etree.ElementTree as ET
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox, Listbox, ttk

# Function to extract headers from XML and determine ANA limit index
def get_ana_limit_index(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        headers = [param.attrib['id'] for param in root.findall('.//text')]

        # Find last ANA index
        ana_indices = [i for i, header in enumerate(headers) if header.startswith("ANA")]
        latest_ana_index = max(ana_indices, default=0)
        ana_limit_index = latest_ana_index + 1  # Adding 1 for Date & Time column

        print(f"Latest ANA Signal Index: {latest_ana_index}")
        print(f"ANA Limit Index (Including Date & Time): {ana_limit_index}")

        return ana_limit_index
    except Exception as e:
        print(f"Error reading XML: {e}")
        return None

    
def combine_csv(extract_to, output_file):
    print(f"Starting to combine CSV files from folder: {extract_to}")
    headers_written = False

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=',')  # Changed delimiter to comma

        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, newline='', encoding='utf-8') as infile:
                            reader = csv.reader(infile, delimiter=',')  # Changed delimiter to comma
                            
                            headers = next(reader, [])  # Read header row

                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True  # Ensure only one header row is written

                            for row in reader:
                                writer.writerow(row)

                    except UnicodeDecodeError:
                        with open(file_path, newline='', encoding='iso-8859-1') as infile:
                            reader = csv.reader(infile, delimiter=',')  # Changed delimiter to comma

                            headers = next(reader, [])  # Read header row

                            if not headers_written:
                                writer.writerow(headers)
                                headers_written = True  # Ensure only one header row is written

                            for row in reader:
                                writer.writerow(row)
    
    print(f"Combined CSV file '{output_file}' created successfully.")

# Function to create raw file with processed data
def create_raw_file(combined_csv, xml_path, raw_output_file):
    ana_limit_index = get_ana_limit_index(xml_path)
    if ana_limit_index is None:
        print("Failed to determine ANA limit index. Aborting process.")
        return

    # Calculate the number of ANA signals (Excel columns 2 to 769 → Python indices 1 to 768)
    num_ana_signals = ana_limit_index  # Since it includes all 768 ANA signals

    try:
        with open(combined_csv, 'r', encoding='utf-8') as infile, open(raw_output_file, 'w', encoding='utf-8', newline='') as outfile:
            reader = csv.reader(infile, delimiter=',')
            writer = csv.writer(outfile, delimiter=',')

            # Read header row
            headers = next(reader)

            for row in reader:
                try:
                    epoch_time = int(float(row[0]))  # Convert safely to int
                    dt_obj = datetime.utcfromtimestamp(epoch_time)
                    formatted_dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S")

                    raw_data = [formatted_dt]  # Store formatted Date Time as first column

                    # Store ANA signals only once (skip duplicates in combined file)
                    raw_data.extend(row[1:ana_limit_index])  

                    # Determine starting index for binary conversion (Skipping Excel columns 770-1537 → Python indices 769-1536)
                    conversion_start_index = 1537  
                    print(f"Starting binary conversion at index: {conversion_start_index}")  # Debugging output

                    # Convert values **after** ANA signals to binary (each bit stored separately)
                    binary_values = []
                    for idx, value in enumerate(row[conversion_start_index:]):  
                        try:
                            int_value = int(float(value))  # Convert properly
                            binary_representation = f"{int_value:016b}"[::-1]  # Reverse binary for LSB first
                            binary_values.extend(binary_representation)  # Store each bit separately
                        except ValueError:
                            print(f"Skipping non-numeric value at index {conversion_start_index + idx}: '{value}'")
                            continue

                    raw_data.extend(binary_values)  # Append binary values **after** ANA signals

                    writer.writerow(raw_data)

                except ValueError:
                    print(f"Skipping invalid epoch timestamp: {row[0]}")
                    continue

            print(f"Raw file '{raw_output_file}' created successfully.")

    except Exception as e:
        print(f"Error processing raw file: {e}")


# Function to create final file using metadata, chosen headers, and raw file data
def create_final_file(combined_csv, raw_file, xml_variables, selected_indices, final_output):
    try:
        with open(raw_file, 'r', encoding='utf-8') as raw, open(final_output, 'w', encoding='utf-8', newline='') as outfile:
            raw_reader = csv.reader(raw, delimiter=',')
            writer = csv.writer(outfile, delimiter=',')

            # Read first row of raw file to check actual column count
            first_row = next(raw_reader, None)
            if first_row:
                print(f"Total columns in raw file: {len(first_row)}")

            # Ensure selected indices exist and are valid
            if not selected_indices:
                print("Error: No selected indices provided.")
                return

            # Adjust selected indices to account for Date Time being in column 1
            adjusted_indices = [idx + 1 for idx in selected_indices]  # Shift indices for Date Time

            # Construct headers: Date Time + selected XML variables
            chosen_headers = ["Date Time"] + [f"{xml_variables[idx][0]} {xml_variables[idx][1]}" for idx in selected_indices]

            # Validate indices don't exceed actual columns in raw file
            max_columns = len(first_row)
            for idx in adjusted_indices:
                if idx >= max_columns:
                    print(f"Error: Index {idx} is out of bounds! Raw file has {max_columns} columns.")
                    return

            # Write headers to final file
            writer.writerow(chosen_headers)

            # Process remaining data rows
            for raw_row in raw_reader:
                filtered_data = [raw_row[0]]  # Keep Date Time column
                filtered_data += [raw_row[idx] for idx in adjusted_indices]  # Select indexed columns

                writer.writerow(filtered_data)

        print(f"Final file '{final_output}' created successfully.")

    except Exception as e:
        print(f"Error creating final file: {e}")


# GUI functions
# Function to delete extracted files
def handle_remove_readonly(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def delete_extracted_files(extract_to):
    if os.path.exists(extract_to):
        try:
            shutil.rmtree(extract_to, onerror=handle_remove_readonly)
            print(f"Successfully deleted {extract_to}")
        except Exception as e:
            print(f"Error deleting {extract_to}: {e}")

# Function to read XML and get variable names
def get_xml_variables(path_xml):
    try:
        tree = ET.parse(path_xml)
        root = tree.getroot()
        return [(param.attrib['id'], param.text.strip()) for param in root.findall('.//text')]
    except Exception as e:
        print(f"Error reading XML: {e}")
        return []


def process_files():
    zip_path = zip_path_entry.get()
    xml_path = xml_entry.get()
    final_path = final_path_entry.get()
    final_name = final_name_entry.get()

    if not zip_path or not xml_path or not final_path or not final_name:
        messagebox.showerror("Error", "Please select all required files and enter a final name.")
        return

    extract_to = "extracted_files"

    # Step 1: Extract nested zip files
    print("Starting to extract ZIP files...")
    extract_nested_zip(zip_path, extract_to)

    # Step 2: Combine CSV files
    combined_csv_path = os.path.join(final_path, "combined.csv")
    print(f"Starting to combine CSV files from folder: {extract_to}")
    combine_csv(extract_to, combined_csv_path)

    # Step 3: Delete extracted files
    delete_extracted_files(extract_to)

    # Step 4: Create raw file
    raw_output_file = os.path.join(final_path, "raw_file.csv")
    print("Generating raw file...")
    create_raw_file(combined_csv_path, xml_path, raw_output_file)

    # Step 5: Process final file
    final_output_file = os.path.join(final_path, f"{final_name}.csv")

    # Debug print for verification
    print(f"Final output file path: {final_output_file}")
    print(f"Selected indices for final file processing: {selected_indices}")

    try:
        create_final_file(combined_csv_path, raw_output_file, xml_variables, selected_indices, final_output_file)
        messagebox.showinfo("Success", f"Final file '{final_output_file}' created successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create final file: {e}")
        print(f"Error creating final file: {e}")


def select_zip_file():
    file_path = filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")])
    if file_path:
        zip_path_entry.delete(0, 'end')
        zip_path_entry.insert(0, file_path)

def select_xml_file():
    file_path = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
    if file_path:
        xml_entry.delete(0, 'end')
        xml_entry.insert(0, file_path)
        update_variable_choices()

def select_final_path():
    directory = filedialog.askdirectory()
    if directory:
        final_path_entry.delete(0, 'end')
        final_path_entry.insert(0, directory)

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

# Function to extract nested zip files
def extract_nested_zip(zipped_file, extract_to='.'):
    try:
        if not zipfile.is_zipfile(zipped_file):
            print(f"The file {zipped_file} is not a valid zip file.")
            return

        with zipfile.ZipFile(zipped_file, 'r') as zfile:
            zfile.extractall(path=extract_to)
            for filename in zfile.namelist():
                nested_file_path = os.path.join(extract_to, filename)
                if zipfile.is_zipfile(nested_file_path):
                    extract_nested_zip(nested_file_path, extract_to)
    except Exception as e:
        print(f"Error extracting {zipped_file}: {e}")


root = Tk()
root.title("CWE Data Preparation")
root.geometry("800x500")

# Labels and input fields
Label(root, text="CWE data .zip file:").grid(row=0, column=0, pady=(10, 0), padx=10)
zip_path_entry = Entry(root, width=60)
zip_path_entry.grid(row=0, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_zip_file).grid(row=0, column=2, pady=(10, 0), padx=10)

Label(root, text="XML File:").grid(row=1, column=0, pady=(10, 0), padx=10)
xml_entry = Entry(root, width=60)
xml_entry.grid(row=1, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_xml_file).grid(row=1, column=2, pady=(10, 0), padx=10)

Label(root, text="Select Variables:").grid(row=2, column=0, pady=(10, 0), padx=10)
vars_frame = ttk.Frame(root)
vars_frame.grid(row=2, column=1, pady=(10, 0), padx=10, sticky="nsew")
root.grid_rowconfigure(2, weight=1)
root.grid_columnconfigure(1, weight=1)

Label(root, text="Final Output Path:").grid(row=3, column=0, pady=(10, 0), padx=10)
final_path_entry = Entry(root, width=60)
final_path_entry.grid(row=3, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_final_path).grid(row=3, column=2, pady=(10, 0), padx=10)

Label(root, text="Final File Name (without .csv):").grid(row=4, column=0, pady=(10, 0), padx=10)
final_name_entry = Entry(root, width=60)
final_name_entry.grid(row=4, column=1, pady=(10, 0))

# Process Files button placed closer
Button(root, text="Process Files", command=process_files).grid(row=5, column=1, pady=(20, 10))

root.mainloop()
