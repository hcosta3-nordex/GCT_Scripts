import zipfile
import os
import csv
import shutil
from tkinter import Tk, filedialog, Button, Label, Entry, messagebox

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
                    with open(file_path, newline='', encoding='utf-8') as infile:
                        reader = csv.reader(infile)
                        if not header_written:
                            # Write header
                            headers = next(reader)
                            writer.writerow(headers)
                            header_written = True
                        else:
                            next(reader)  # Skip header
                        for row in reader:
                            writer.writerow(row)

# Function to delete extracted files
def delete_extracted_files(extract_to):
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)

# Function to handle the file selection
def select_file():
    file_path = filedialog.askopenfilename(title="Select the outer zip file", filetypes=[("Zip Files", "*.zip")])
    if file_path:
        path_entry.delete(0, 'end')
        path_entry.insert(0, file_path)

# Function to handle the directory selection
def select_directory():
    directory = filedialog.askdirectory(title="Select the output directory")
    if directory:
        output_path_entry.delete(0, 'end')
        output_path_entry.insert(0, directory)

# Function to process the file
def process_file():
    file_path = path_entry.get()
    if file_path:
        extract_to = 'extracted_files'
        
        # Extract the outer zip file
        extract_nested_zip(file_path, extract_to)
        
        output_path = output_path_entry.get()
        output_file = output_file_entry.get()
        if not output_file.endswith('.csv'):
            output_file += '.csv'
        final_output = os.path.join(output_path, output_file)
        
        # Combine CSV files into a single CSV file
        combine_csv(extract_to, final_output)
        
        # Delete extracted files after processing
        delete_extracted_files(extract_to)
        
        messagebox.showinfo("Information", f"Combined data saved to {final_output}")
    else:
        messagebox.showwarning("Warning", "No file selected.")

# Function to create the GUI
def create_gui():
    root = Tk()
    root.title("CSV Combiner")
    
    # Maximize the window and configure it to fit the screen size
    root.state('zoomed')
    root.grid_columnconfigure(1, weight=1)
    
    # Create and add widgets
    output_path_label = Label(root, text="Specify the output directory", anchor='w')
    output_path_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')
    
    global output_path_entry
    output_path_entry = Entry(root, width=50)
    output_path_entry.grid(row=0, column=1, padx=10, pady=10, sticky='ew')
    
    browse_dir_button = Button(root, text="Browse", command=select_directory)
    browse_dir_button.grid(row=0, column=2, padx=10, pady=10)
    
    output_file_label = Label(root, text="Specify the output file name (without .csv extension)", anchor='w')
    output_file_label.grid(row=1, column=0, padx=10, pady=10, sticky='w')
    
    global output_file_entry
    output_file_entry = Entry(root, width=50)
    output_file_entry.grid(row=1, column=1, padx=10, pady=10, sticky='ew')
    
    instruction_label = Label(root, text="Select .zip location", anchor='w')
    instruction_label.grid(row=2, column=0, padx=10, pady=10, sticky='w')
    
    global path_entry
    path_entry = Entry(root, width=50)
    path_entry.grid(row=2, column=1, padx=10, pady=10, sticky='ew')
    
    select_button = Button(root, text="Browse", command=select_file)
    select_button.grid(row=2, column=2, padx=10, pady=10)
    
    process_button = Button(root, text="Process File", command=process_file)
    process_button.grid(row=3, column=1, padx=10, pady=20)
    process_button.grid_columnconfigure(1, weight=1)

    root.mainloop()

# Run the GUI
create_gui()
