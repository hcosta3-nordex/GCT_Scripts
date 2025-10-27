import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re

window = tk.Tk()
window.title("Filter Signals Tool")

input_file_var = tk.StringVar()
output_file_var = tk.StringVar()
start_time_var = tk.StringVar()
end_time_var = tk.StringVar()
mode_var = tk.StringVar(value="TSDL (Export CSV)")
last_mode = [None]

def update_time_examples(*args):
    current_mode = mode_var.get()
    if current_mode != last_mode[0]:
        if current_mode in ["TSDL (Export CSV)", "TSDL v2 (Export CSV)"]:
            start_time_var.set("10:00:00.000")
            end_time_var.set("12:00:00.000")
        elif current_mode == "OPClogger":
            start_time_var.set("10:00:00")
            end_time_var.set("12:00:00")
        last_mode[0] = current_mode

mode_var.trace_add("write", update_time_examples)
update_time_examples()

def browse_file(var):
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        var.set(filepath)

def save_file(var):
    filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if filepath:
        var.set(filepath)

def time_to_int_tsdl(time_str):
    try:
        hh, mm, ss_ms = time_str.split(':')
        ss, ms = ss_ms.split('.')
        return int(hh) * 10000000 + int(mm) * 100000 + int(ss) * 1000 + int(ms)
    except ValueError:
        return None

def time_to_int_opc(time_str):
    try:
        hh, mm, ss = map(int, time_str.split(':'))
        return hh * 10000 + mm * 100 + ss
    except ValueError:
        return None

def is_within_time_range_tsdl(time_str, start_time_str, end_time_str):
    time_int = time_to_int_tsdl(time_str)
    start_int = time_to_int_tsdl(start_time_str)
    end_int = time_to_int_tsdl(end_time_str)
    return None not in (time_int, start_int, end_int) and start_int <= time_int <= end_int

def is_within_time_range_opc(time_str, start_time_str, end_time_str):
    time_int = time_to_int_opc(time_str)
    start_int = time_to_int_opc(start_time_str)
    end_int = time_to_int_opc(end_time_str)
    return None not in (time_int, start_int, end_int) and start_int <= time_int <= end_int

def filter_csv():
    mode = mode_var.get()
    try:
        start_time = start_time_var.get().strip().replace('"', '').replace('\r', '').replace('\n', '')
        end_time = end_time_var.get().strip().replace('"', '').replace('\r', '').replace('\n', '')

        if mode in ["TSDL (Export CSV)", "TSDL v2 (Export CSV)","TSDL (Export)","TSDL v2 (Export)"]:
            time_pattern = r"^\d{2}:\d{2}:\d{2}\.\d{3}$"
            if not re.match(time_pattern, start_time) or not re.match(time_pattern, end_time):
                raise ValueError("Invalid time format for TSDL")

            with open(input_file_var.get(), mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                filtered_data = []

                for i, row in enumerate(reader, start=1):
                    if mode == "TSDL (Export CSV)":
                        if i <= 2:
                            filtered_data.append(row)
                            continue
                    elif mode == "TSDL v2 (Export CSV)":
                        if i <= 3:
                            filtered_data.append(row)
                            continue
                    elif mode in ["TSDL (Export)", "TSDL v2 (Export)"]:
                        if i <= 1:
                            filtered_data.append(row)
                            continue
                    if len(row) > 1:
                        if mode == "TSDL (Export CSV)" or mode == "TSDL (Export)":
                            time_part = row[0].split(';')[1].strip().replace('"', '')
                        elif mode == "TSDL v2 (Export CSV)" or mode == "TSDL v2 (Export)":
                            time_part = row[1].strip().replace('"', '')
                        else:
                            continue

                        if not re.match(time_pattern, time_part):
                            continue
                        if is_within_time_range_tsdl(time_part, start_time, end_time):
                            filtered_data.append(row)

            with open(output_file_var.get(), mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerows(filtered_data)

        elif mode == "OPClogger":
            with open(input_file_var.get(), mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                filtered_data = [next(reader)]

                for row in reader:
                    if len(row) < 1:
                        continue
                    datetime_part = row[0].strip()
                    if " " in datetime_part:
                        time_str = datetime_part.split(" ")[1].split(",")[0]
                        if is_within_time_range_opc(time_str, start_time, end_time):
                            filtered_data.append(row)

            with open(output_file_var.get(), mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerows(filtered_data)

        messagebox.showinfo("Success", f"Filtered data has been saved to {output_file_var.get()}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

tk.Label(window, text="Export:").grid(row=0, column=0, padx=5, pady=5)
mode_dropdown = ttk.Combobox(window, textvariable=mode_var, values=["TSDL (Export CSV)", "TSDL v2 (Export CSV)", "TSDL (Export)", "TSDL v2 (Export)" ,"OPClogger"], state="readonly")
mode_dropdown.grid(row=0, column=1, padx=5, pady=5)

tk.Label(window, text="Input File:").grid(row=1, column=0, padx=5, pady=5)
tk.Entry(window, textvariable=input_file_var, width=40).grid(row=1, column=1, padx=5, pady=5)
tk.Button(window, text="Browse", command=lambda: browse_file(input_file_var)).grid(row=1, column=2, padx=5, pady=5)

tk.Label(window, text="Start Time:").grid(row=2, column=0, padx=5, pady=5)
tk.Entry(window, textvariable=start_time_var, width=20).grid(row=2, column=1, padx=5, pady=5)

tk.Label(window, text="End Time:").grid(row=3, column=0, padx=5, pady=5)
tk.Entry(window, textvariable=end_time_var, width=20).grid(row=3, column=1, padx=5, pady=5)

tk.Label(window, text="Output File:").grid(row=4, column=0, padx=5, pady=5)
tk.Entry(window, textvariable=output_file_var, width=40).grid(row=4, column=1, padx=5, pady=5)
tk.Button(window, text="Save As", command=lambda: save_file(output_file_var)).grid(row=4, column=2, padx=5, pady=5)

tk.Button(window, text="Run", command=filter_csv).grid(row=5, column=1, pady=10)

window.mainloop()
