import csv
import tkinter as tk
from tkinter import filedialog, messagebox

# Function to convert HH:MM:SS time string to an integer for comparison
def time_to_int(time_str):
    try:
        hh, mm, ss = map(int, time_str.split(':'))
        return hh * 10000 + mm * 100 + ss  # Convert to HHMMSS format as an integer
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

# Function to filter rows in the CSV file
def filter_csv():
    try:
        start_time = start_time_var.get().strip()
        end_time = end_time_var.get().strip()

        with open(input_file_var.get(), mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')  # Use comma as delimiter
            filtered_data = []

            # Read and keep header
            header = next(reader)
            filtered_data.append(header)

            for row in reader:
                if len(row) < 1:
                    continue

                datetime_part = row[0].strip()  # First column contains date and time

                # Extract only the time part from the first column
                if " " in datetime_part:
                    time_str = datetime_part.split(" ")[1].split(",")[0]  # Keep only the time portion before any commas
                else:
                    continue  # Skip malformed rows

                time_int = time_to_int(time_str)

                if time_int is None:
                    continue

                if is_within_time_range(time_str, start_time, end_time):
                    filtered_data.append(row)

        # Ensure the filtered data isn't empty before writing
        if len(filtered_data) > 1:
            with open(output_file_var.get(), mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')  # Use comma as delimiter
                writer.writerows(filtered_data)

            messagebox.showinfo("Success", f"Filtered data has been saved to {output_file_var.get()}")
        else:
            messagebox.showwarning("No Matches", "No rows matched the time filter.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Function to browse input file
def browse_file(var):
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        var.set(filepath)

# Function to save output file
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
tk.Label(window, text="Start Time (HH:mm:ss):").grid(row=1, column=0, padx=5, pady=5)
start_time_var = tk.StringVar(value="08:00:00")
tk.Entry(window, textvariable=start_time_var, width=20).grid(row=1, column=1, padx=5, pady=5)

# End time entry
tk.Label(window, text="End Time (HH:mm:ss):").grid(row=2, column=0, padx=5, pady=5)
end_time_var = tk.StringVar(value="12:00:00")
tk.Entry(window, textvariable=end_time_var, width=20).grid(row=2, column=1, padx=5, pady=5)

# Output file selection
tk.Label(window, text="Output File:").grid(row=3, column=0, padx=5, pady=5)
output_file_var = tk.StringVar()
tk.Entry(window, textvariable=output_file_var, width=40).grid(row=3, column=1, padx=5, pady=5)
tk.Button(window, text="Save As", command=lambda: save_file(output_file_var)).grid(row=3, column=2, padx=5, pady=5)

# Run button
tk.Button(window, text="Run", command=filter_csv).grid(row=4, column=1, pady=10)

window.mainloop()
