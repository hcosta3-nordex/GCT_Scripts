import os
import csv
import zipfile
import shutil
import stat
import xml.etree.ElementTree as ET
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox, Listbox, ttk

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

# Function to combine CSV files
def combine_csv(extract_to, output_file):
    print(f"Starting to combine CSV files from folder: {extract_to}")
    metadata_written = False
    headers_written = False

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter=';')  # Ensure semicolon delimiter

        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, newline='', encoding='utf-8') as infile:
                            reader = csv.reader(infile, delimiter=';')  # Ensure semicolon delimiter

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
                            reader = csv.reader(infile, delimiter=';')  # Ensure semicolon delimiter
                            
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

# Function to process combined CSV and XML data
def read_csv_xml(path_csv, xml_vars, selected_indices, final_path, final_name):
    try:
        with open(path_csv, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')  # Semicolon delimiter

            # Read metadata and skip combined headers
            first_metadata = next(reader, [])
            second_metadata = next(reader, [])
            next(reader, [])  # Skip combined headers

            # Define column indices
            column_indices = [0, 1] + [idx + 2 for idx in selected_indices]

            # Generate headers: $Date, Time, and mapped XML variables
            headers = ['$Date', 'Time']  # Start with $Date and Time
            for idx in selected_indices:
                if idx < len(xml_vars):  # Ensure valid XML variable index
                    headers.append(xml_vars[idx][1])  # Use XML variable description
                else:
                    print(f"Skipping invalid XML variable index {idx}.")

            # Collect and process rows
            processed_data = []
            for row_num, row in enumerate(reader, start=4):  # Start processing data rows
                valid_indices = [idx for idx in column_indices if idx < len(row)]
                selected_row = [row[idx] for idx in valid_indices]
                processed_data.append(selected_row)

                # Log skipped columns
                for idx in column_indices:
                    if idx >= len(row) and idx > 1:  # Exclude $Date and Time indices
                        print(f"Skipping column: {xml_vars[idx - 2][1]} (XML variable: {xml_vars[idx - 2][0]})")

        # Write the processed data to a new CSV file
        final_file_name = os.path.join(final_path, f"{final_name}.csv")
        with open(final_file_name, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=';')
            writer.writerow(first_metadata)
            writer.writerow(second_metadata)
            writer.writerow(headers)
            writer.writerows(processed_data)

        print(f"Data successfully written to {final_file_name}")

    except Exception as e:
        print(f"Error processing CSV and XML: {e}")


# GUI functions
def process_files():
    zip_file_path = zip_path_entry.get()
    xml_path = xml_entry.get()
    final_path = final_path_entry.get()
    final_name = final_name_entry.get()

    if not os.path.exists(zip_file_path) or not os.path.exists(xml_path):
        messagebox.showerror("Error", "Please select valid file paths.")
        return

    if not os.path.exists(final_path):
        os.makedirs(final_path)

    extract_to = 'extracted_files'
    extract_nested_zip(zip_file_path, extract_to)
    combined_csv_path = os.path.join(final_path, 'combined.csv')
    combine_csv(extract_to, combined_csv_path)
    delete_extracted_files(extract_to)

    read_csv_xml(combined_csv_path, xml_variables, selected_indices, final_path, final_name)
    os.remove(combined_csv_path)

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

