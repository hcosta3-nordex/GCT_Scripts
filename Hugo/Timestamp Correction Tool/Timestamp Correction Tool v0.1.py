import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import csv
from datetime import datetime, timedelta

def process_tsdl_csv(input_path, output_path, start_time_str, increment_ms):
    try:
        start_time = datetime.strptime(start_time_str, "%H:%M:%S.%f")
        increment = timedelta(milliseconds=int(increment_ms))
    except ValueError:
        messagebox.showerror("Error", "Invalid time format or increment.")
        return

    try:
        with open(input_path, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.reader(infile, delimiter=',')
            header = [next(reader) for _ in range(3)]
            data = list(reader)

        seen = set()
        unique_data = []
        for row in data:
            cleaned_row = [field.strip().strip('"') for field in row]
            row_tuple = tuple(cleaned_row)
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_data.append(row)

        with open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile, delimiter=',')
            for h in header:
                writer.writerow(h)

            for i, row in enumerate(unique_data):
                timestamp = start_time + i * increment
                formatted_time = timestamp.strftime("%H:%M:%S.%f")[:-3]
                if len(row) >= 2:
                    row[1] = f"'{formatted_time}'"
                writer.writerow(row)

        messagebox.showinfo("Success", f"TSDL CSV saved to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"TSDL processing failed:\n{str(e)}")

def process_tsdl_bin(input_path, output_path, start_time_str, increment_ms):
    try:
        start_time = datetime.strptime(start_time_str, "%H:%M:%S.%f")
        increment = timedelta(milliseconds=int(increment_ms))
    except ValueError:
        messagebox.showerror("Error", "Invalid time format or increment.")
        return

    try:
        with open(input_path, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.reader(infile, delimiter=',')
            header = [next(reader) for _ in range(1)]
            data = list(reader)

        seen = set()
        unique_data = []
        for row in data:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_data.append(row)

        with open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile, delimiter=',')
            for h in header:
                writer.writerow(h)

            for i, row in enumerate(unique_data):
                timestamp = start_time + i * increment
                formatted_time = timestamp.strftime("%H:%M:%S.%f")[:-3]
                if len(row) >= 2:
                    row[1] = f"'{formatted_time}'"
                writer.writerow(row)

        messagebox.showinfo("Success", f"TSDL CSV saved to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"TSDL processing failed:\n{str(e)}")

def process_opclogger(input_path, output_path, start_time_str):
    try:
        start_time = datetime.strptime(start_time_str, "%H:%M:%S")
        increment = timedelta(seconds=1)
    except ValueError:
        messagebox.showerror("Error", "Start time must be in format HH:MM:SS")
        return

    try:
        with open(input_path, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.reader(infile, delimiter=',')
            header = next(reader)
            data = list(reader)

        seen = set()
        unique_data = []
        for row in data:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_data.append(row)

        with open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile, delimiter=',')
            writer.writerow(header)

            for i, row in enumerate(unique_data):
                timestamp = start_time + i * increment
                formatted_time = timestamp.strftime("%H:%M:%S")
                if len(row) >= 2:
                    row[1] = f"'{formatted_time}'"
                writer.writerow(row)

        messagebox.showinfo("Success", f"OPCLogger CSV saved to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"OPCLogger processing failed:\n{str(e)}")

def browse_input():
    path = filedialog.askopenfilename(title="Select Input CSV", filetypes=[("CSV Files", "*.csv")])
    if path:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, path)

def browse_output():
    path = filedialog.asksaveasfilename(title="Save Output CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, path)

def toggle_mode(event=None):
    mode = mode_selector.get()

    input_entry.delete(0, tk.END)
    output_entry.delete(0, tk.END)
    time_entry.delete(0, tk.END)
    increment_entry.delete(0, tk.END)

    if mode in ["TSDL (Export CSV)", "TSDL (Export)"]:
        increment_label.grid()
        increment_entry.grid()
        time_label.config(text="Start Time (HH:MM:SS.mss):")

    else:
        increment_label.grid_remove()
        increment_entry.grid_remove()
        time_label.config(text="Start Time (HH:MM:SS):")

def run_processing():
    try:
        input_path = input_entry.get()
        output_path = output_entry.get()
        start_time = time_entry.get()
        increment = increment_entry.get()
        mode = mode_selector.get().strip()

        if not input_path or not output_path or not start_time:
            messagebox.showerror("Error", "Please fill in all required fields.")
            return

        if mode == "TSDL (Export CSV)":
            if not increment:
                messagebox.showerror("Error", "Please enter increment in milliseconds.")
                return
            process_tsdl_csv(input_path, output_path, start_time, increment)
        elif mode == "TSDL (Export)":
            if not increment:
                messagebox.showerror("Error", "Please enter increment in milliseconds.")
                return
            process_tsdl_bin(input_path, output_path, start_time, increment)
        elif mode == "OPCLogger":
            process_opclogger(input_path, output_path, start_time)
        else:
            messagebox.showerror("Error", f"Unknown mode: {mode}")
    except Exception as e:
        messagebox.showerror("Unexpected Error", str(e))

root = tk.Tk()
root.title("Timestamp Correction Tool v0.1")
root.geometry("800x300")
root.resizable(True, True)

top_frame = tk.Frame(root)
top_frame.pack(pady=10)
tk.Label(top_frame, text="Format:").pack(side=tk.LEFT, padx=5)
mode_selector = ttk.Combobox(top_frame, values=["TSDL (Export CSV)","TSDL (Export)","OPCLogger"], state="readonly", width=15)
mode_selector.pack(side=tk.LEFT)
mode_selector.current(0)
mode_selector.bind("<<ComboboxSelected>>", toggle_mode)

form_frame = tk.Frame(root)
form_frame.pack(fill="both", expand=True, padx=20)
form_frame.grid_columnconfigure(1, weight=1)

tk.Label(form_frame, text="Input CSV File:").grid(row=0, column=0, sticky="w", pady=5)
input_entry = tk.Entry(form_frame)
input_entry.grid(row=0, column=1, sticky="ew", padx=5)
tk.Button(form_frame, text="Browse", command=browse_input).grid(row=0, column=2, padx=5)

time_label = tk.Label(form_frame, text="Start Time (HH:MM:SS.sss):")
time_label.grid(row=1, column=0, sticky="w", pady=5)
time_entry = tk.Entry(form_frame)
time_entry.grid(row=1, column=1, sticky="ew", padx=5)

increment_label = tk.Label(form_frame, text="Increment (ms):")
increment_label.grid(row=2, column=0, sticky="w", pady=5)
increment_entry = tk.Entry(form_frame)
increment_entry.grid(row=2, column=1, sticky="ew", padx=5)

tk.Label(form_frame, text="Output CSV File:").grid(row=3, column=0, sticky="w", pady=5)
output_entry = tk.Entry(form_frame)
output_entry.grid(row=3, column=1, sticky="ew", padx=5)
tk.Button(form_frame, text="Browse", command=browse_output).grid(row=3, column=2, padx=5)

tk.Button(root, text="Process CSV", command=run_processing).pack(pady=20)

toggle_mode()
root.mainloop()
