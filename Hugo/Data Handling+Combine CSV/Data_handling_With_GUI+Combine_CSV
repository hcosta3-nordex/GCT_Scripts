import zipfile
import os
import csv
import shutil
from tkinter import Tk, filedialog, Button, Label, Entry, messagebox, Listbox
import xml.etree.ElementTree as ET
from tkinter import ttk

# Function to extract nested zip files
def extract_nested_zip(zipped_file, extract_to='.'):
    with zipfile.ZipFile(zipped_file, 'r') as zfile:
        zfile.extractall(path=extract_to)
        for filename in zfile.namelist():
            if zipfile.is_zipfile(os.path.join(extract_to, filename)):
                extract_nested_zip(os.path.join(extract_to, filename), extract_to)

# Function to combine CSV files into a single CSV file
def combine_csv(extract_to, output_file):
    header_written = False

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)

        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, newline='', encoding='utf-8') as infile:
                            reader = csv.reader(infile)
                            if not header_written:
                                headers = [next(reader) for _ in range(3)]
                                for header in headers:
                                    writer.writerow(header)
                                header_written = True
                            else:
                                for _ in range(3):
                                    next(reader)
                            for row in reader:
                                writer.writerow(row)
                    except UnicodeDecodeError:
                        with open(file_path, newline='', encoding='iso-8859-1') as infile:
                            reader = csv.reader(infile)
                            if not header_written:
                                headers = [next(reader) for _ in range(3)]
                                for header in headers:
                                    writer.writerow(header)
                                header_written = True
                            else:
                                for _ in range(3):
                                    next(reader)
                            for row in reader:
                                writer.writerow(row)

# Function to delete extracted files
def delete_extracted_files(extract_to):
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)

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
    return header.split('[')[0].strip().replace('"', '')

# Function to read and process CSV and XML
def read_csv_xml(path_csv, path_xml, variables, final_path, final_name):
    try:
        with open(path_csv, 'r', encoding='utf-8') as file:
            new_csv_lines = []

            # Read the first three lines for headers
            headers_line_1 = file.readline().strip().replace('\r', '')
            headers_line_2 = file.readline().strip().replace('\r', '')
            headers_line_3 = file.readline().strip().replace('\r', '')

            headers = headers_line_3.split(';')
            normalized_headers = [normalize_header(header) for header in headers]
            original_headers = [header.replace('""', '"') for header in headers]  # Handle double quotes

            # Extract text content from variables for comparison
            text_content_vars = [var.split(' ', 1)[1] for var in variables]

            # Always include the first two columns
            column_numbers = [0, 1]
            for i, header in enumerate(normalized_headers):
                if header in text_content_vars and i >= 2:  # Ensure first two columns are always included
                    column_numbers.append(i)

            # Add the headers to the new CSV lines
            new_csv_lines.append(headers_line_1.replace('""', '"'))
            new_csv_lines.append(headers_line_2.replace('""', '"'))
            new_csv_lines.append(';'.join([original_headers[i] for i in column_numbers]))

            # Process the data lines
            line_count = 0
            for line in file:
                line_count += 1
                # Handle double quotes and ensure each line is properly formatted
                columns = line.strip().replace('\r', '').replace('""', '"').split(';')
                new_line = [columns[i] for i in column_numbers]
                new_csv_lines.append(';'.join(new_line))

            # Print the number of lines written to the output file
            print(f"Number of lines in output file (excluding header lines): {len(new_csv_lines) - 3}")

            final_file_name = os.path.join(final_path, f"{final_name}.csv")

            if not os.path.exists(final_path):
                print(f"The directory {final_path} does not exist.")
                return

            with open(final_file_name, 'w', encoding='utf-8', newline='\n') as file:
                for idx, line in enumerate(new_csv_lines):
                    file.write(line + '\n')  # Ensure each line ends with a newline character
                    print(f"Writing line {idx + 1}: {line}")  # Debugging: Print each line being written
            print(f"Data written successfully to {final_file_name}")
    except Exception as e:
        print(f"Error processing file: {e}")

# GUI functions
def process_files():
    zip_file_path = zip_path_entry.get()
    xml_path = xml_entry.get()
    selected_vars = [xml_variables[i] for i in selected_indices]
    final_path = final_path_entry.get()
    final_name = final_name_entry.get()

    if not os.path.exists(zip_file_path) or not os.path.exists(xml_path):
        messagebox.showerror("Error", "Please select valid file paths.")
        return

    # Extract and combine CSV files
    extract_to = 'extracted_files'
    extract_nested_zip(zip_file_path, extract_to)
    combined_csv_path = os.path.join(final_path, 'combined.csv')
    combine_csv(extract_to, combined_csv_path)
    delete_extracted_files(extract_to)

    # Process combined CSV with XML
    read_csv_xml(combined_csv_path, xml_path, selected_vars, final_path, final_name)
    os.remove(combined_csv_path)  # Remove the temporary combined CSV file

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
        var_listbox.insert('end', var)
    var_listbox.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=var_listbox.yview)

    def on_selection_change(event):
        global selected_indices
        selected_indices = var_listbox.curselection()
    
    var_listbox.bind('<<ListboxSelect>>', on_selection_change)

root = Tk()
root.title("CSV and XML Processor")
root.geometry("800x600")

Label(root, text="CWE data .zip file:").grid(row=0, column=0, pady=(10, 0), padx=10)
zip_path_entry = Entry(root, width=60)
zip_path_entry.grid(row=0, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_zip_file).grid(row=0, column=2, pady=(10, 0), padx=10)

Label(root, text="XML File:").grid(row=1, column=0, pady=(10, 0), padx=10)
xml_entry = Entry(root, width=60)
xml_entry.grid(row=1, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_xml_file).grid(row=1, column=2, pady=(10, 0), padx=10)

# Variables selection frame
vars_frame = ttk.LabelFrame(root, text="Select Variables")
vars_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), padx=10, sticky='nswe')

Label(root, text="Final Save Path:").grid(row=3, column=0, pady=(10, 0), padx=10)
final_path_entry = Entry(root, width=60)
final_path_entry.grid(row=3, column=1, pady=(10, 0))
Button(root, text="Browse...", command=select_final_path).grid(row=3, column=2, pady=(10, 0), padx=10)

Label(root, text="Final File Name (without .csv):").grid(row=4, column=0, pady=(10, 0), padx=10)
final_name_entry = Entry(root, width=60)
final_name_entry.grid(row=4, column=1, pady=(10, 0))

Button(root, text="Process Files", command=process_files).grid(row=5, column=1, pady=20)

selected_indices = []
xml_variables = []

# Make the window resizable
root.geometry("800x600")
root.grid_rowconfigure(2, weight=1)
root.grid_columnconfigure(1, weight=1)

root.mainloop()
