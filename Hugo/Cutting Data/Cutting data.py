import csv
import tkinter as tk
from tkinter import filedialog, messagebox
import re

# Function to convert time string to an integer for comparison
def time_to_int(time_str):
    try:
        hh, mm, ss_ms = time_str.split(':')
        ss, ms = ss_ms.split('.')
        return int(hh) * 10000000 + int(mm) * 100000 + int(ss) * 1000 + int(ms)  # Convert to HHMMSSMMM format
    except ValueError:
        return None

# Function to check if the time is within the range
def is_within_time_range(time_str, start_time_str, end_time_str):
    time_int = time_to_int(time_str)
    start_int = time_to_int(start_time_str)
    end_int = time_to_int(end_time_str)

    if time_int is None or start_int is None or end_int is None:
        return False

    return start_int <= time_int <= end_int

# Function to filter rows
def filter_csv():
    try:
        start_time = start_time_var.get().strip().replace('"', '').replace('\r', '').replace('\n', '')
        end_time = end_time_var.get().strip().replace('"', '').replace('\r', '').replace('\n', '')

        time_pattern = r"^\d{2}:\d{2}:\d{2}\.\d{3}$"
        if not re.match(time_pattern, start_time):
            raise ValueError(f"Invalid start time format: {start_time}")
        if not re.match(time_pattern, end_time):
            raise ValueError(f"Invalid end time format: {end_time}")

        with open(input_file_var.get(), mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            filtered_data = []

            # Always include the first three rows
            for i, row in enumerate(reader, start=1):
                if i <= 2:
                    filtered_data.append(row)
                    continue

                # Apply filtering logic to rows starting from the 4th row
                date_time = row[0]
                time_part = date_time.split(';')[1].strip().replace('"', '').replace('\r', '').replace('\n', '')

                if not re.match(time_pattern, time_part):
                    continue

                if is_within_time_range(time_part, start_time, end_time):
                    filtered_data.append(row)

        with open(output_file_var.get(), mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerows(filtered_data)

        messagebox.showinfo("Success", f"Filtered data has been saved to {output_file_var.get()}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Function to browse files
def browse_file(var):
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        var.set(filepath)

def save_file(var):
    filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if filepath:
        var.set(filepath)

# Create GUI window
window = tk.Tk()
window.title("CSV Filter Tool")

# Input file selection
tk.Label(window, text="Input File:").grid(row=0, column=0, padx=5, pady=5)
input_file_var = tk.StringVar()
tk.Entry(window, textvariable=input_file_var, width=40).grid(row=0, column=1, padx=5, pady=5)
tk.Button(window, text="Browse", command=lambda: browse_file(input_file_var)).grid(row=0, column=2, padx=5, pady=5)

# Start time entry
tk.Label(window, text="Start Time (hh:mm:ss.mmm):").grid(row=1, column=0, padx=5, pady=5)
start_time_var = tk.StringVar(value="10:00:00.000")
tk.Entry(window, textvariable=start_time_var, width=20).grid(row=1, column=1, padx=5, pady=5)

# End time entry
tk.Label(window, text="End Time (hh:mm:ss.mmm):").grid(row=2, column=0, padx=5, pady=5)
end_time_var = tk.StringVar(value="12:00:00.000")
tk.Entry(window, textvariable=end_time_var, width=20).grid(row=2, column=1, padx=5, pady=5)

# Output file selection
tk.Label(window, text="Output File:").grid(row=3, column=0, padx=5, pady=5)
output_file_var = tk.StringVar()
tk.Entry(window, textvariable=output_file_var, width=40).grid(row=3, column=1, padx=5, pady=5)
tk.Button(window, text="Save As", command=lambda: save_file(output_file_var)).grid(row=3, column=2, padx=5, pady=5)

# Run button
tk.Button(window, text="Run", command=filter_csv).grid(row=4, column=1, pady=10)

window.mainloop()
