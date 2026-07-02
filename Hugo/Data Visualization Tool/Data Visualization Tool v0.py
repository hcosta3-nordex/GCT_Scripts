
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,NavigationToolbar2Tk)


def open_plot_window(root, final_csv_path, source_selected):
    if not final_csv_path:
        messagebox.showwarning("Warning", "No file selected")
        return

    plot_win = tk.Toplevel(root)
    plot_win.title("Plot")
    plot_win.geometry("1200x750")

    paned = tk.PanedWindow(plot_win, orient=tk.HORIZONTAL)
    paned.pack(fill="both", expand=True)

    center_frame = tk.Frame(paned)
    right_frame = tk.Frame(paned)

    paned.add(center_frame, stretch="always")
    paned.add(right_frame)

    def set_pane_size():
        width = plot_win.winfo_width()
        paned.sash_place(0, int(width * 2.75), 0)

    plot_win.after(100, set_pane_size)

    df = pd.read_csv(
        final_csv_path,
        sep=",",
        engine="c",
        low_memory=False,
        on_bad_lines="skip"
    )

    if "Date" not in df.columns:
        df = pd.read_csv(
            final_csv_path,
            engine="c",
            sep=",",
            header=2,
            low_memory=False,
            on_bad_lines="skip"
        )

    df["Time_clean"] = df["Time"].astype(str).str.replace("'", "", regex=False)
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time_clean"], format="mixed", errors="coerce")
    df = df.dropna(subset=["Datetime"]).set_index("Datetime")
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    variables = [c for c in df.columns if c not in ["Date", "Time", "Time_clean"]]

    search_var = tk.StringVar()
    search_entry = tk.Entry(right_frame, textvariable=search_var)
    search_entry.pack(fill="x", padx=2, pady=2)

    list_frame = tk.Frame(right_frame)
    list_frame.pack(fill="both", expand=True)

    y_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
    x_scroll = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL)

    listbox = tk.Listbox(list_frame,selectmode=tk.SINGLE,exportselection=False,yscrollcommand=y_scroll.set,xscrollcommand=x_scroll.set,font=("Segoe UI", 9))
    
    y_scroll.config(command=listbox.yview)
    x_scroll.config(command=listbox.xview)

    y_scroll.pack(side="right", fill="y")
    x_scroll.pack(side="bottom", fill="x")
    listbox.pack(side="left", fill="both", expand=True)

    dragged = {"var": None}

    def on_list_click(event):
        idx = listbox.nearest(event.y)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(idx)
        dragged["var"] = listbox.get(idx)

    listbox.bind("<ButtonPress-1>", on_list_click)

    def update_list(*args):
        search = search_var.get().lower()
        listbox.delete(0, tk.END)
        for v in variables:
            if search in v.lower():
                listbox.insert(tk.END, v)

    update_list()
    search_var.trace_add("write", update_list)

    fig = plt.figure()
    canvas = FigureCanvasTkAgg(fig, master=center_frame)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    toolbar = NavigationToolbar2Tk(canvas, center_frame)
    toolbar.update()
    toolbar.pack(side="bottom", fill="x")

    axes = []
    plot_data = [[]]

    legend_state = {}
    legend_links = {}

    lines = []
    mode = {"type": None}
    selected_text = {"obj": None}
    mouse_pressed = {"state": False}

    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    def format_time(x, pos=None):
        dt = mdates.num2date(x)
        if source_selected == "OPClogger" or source_selected == "MFR OPClogger":
            return f"{dt.strftime('%H:%M:%S')}".rstrip("0").rstrip(".")
        elif source_selected == "MFR TSDL":
            return f"{dt.strftime('%H:%M:%S')}.{dt.microsecond:06d}".rstrip("0").rstrip(".")
        else:
            ms = int(dt.microsecond / 1000)
            return f"{dt.strftime('%H:%M:%S')}.{ms:03d}".rstrip("0").rstrip(".")

    def rebuild_axes():
        fig.clf()
        axes.clear()
        legend_links.clear()

        gs = gridspec.GridSpec(len(plot_data), 1, figure=fig)

        for i in range(len(plot_data)):
            ax = fig.add_subplot(gs[i, 0], sharex=axes[0] if axes else None)

            lines_local = []
            labels = []

            for j, var in enumerate(plot_data[i]):
                legend_state.setdefault(var, True)

                y = df[var].astype(str).str.replace(",", ".", regex=False)
                y = pd.to_numeric(y, errors="coerce")

                line, = ax.plot(df.index, y, color=colors[j % len(colors)])
                line.set_visible(legend_state[var])

                line._var = var
                line._axis = i

                lines_local.append(line)

                tick = "☑" if legend_state[var] else "☐"
                labels.append(f"{tick} {var}    ⨯")

            if lines_local:
                legend = ax.legend(lines_local, labels, fontsize=8)
                legend.set_draggable(True)
                for txt, line_obj, var in zip(legend.get_texts(), lines_local, plot_data[i]):
                    txt.set_picker(True)
                    txt._line = line_obj
                    txt._var = var
                    txt._axis = i
                    legend_links[txt] = line_obj

            ax.set_xlim(df.index.min(), df.index.max())
            ax.margins(x=0)      

            ax.xaxis.set_major_formatter(plt.FuncFormatter(format_time))
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda y, _: f"{y:.3f}".rstrip("0").rstrip("."))
            )

            axes.append(ax)

        fig.tight_layout()
        canvas.draw()

    rebuild_axes()

    def add_subplot():
        plot_data.append([])
        rebuild_axes()

    ttk.Button(right_frame, text="Add Plot Area", command=add_subplot).pack(pady=5)

    def add_plot(var, ax):
        for i, axis in enumerate(axes):
            if axis == ax:
                plot_data[i].append(var)
                break
        rebuild_axes()

    def on_release(event):
        mouse_pressed["state"] = False
        if dragged["var"] and event.inaxes:
            add_plot(dragged["var"], event.inaxes)
        dragged["var"] = None
        selected_text["obj"] = None

    canvas.mpl_connect("button_release_event", on_release)
    canvas.mpl_connect("button_press_event", lambda e: mouse_pressed.update(state=True))

    def on_pick(event):
        txt = event.artist

        if txt in legend_links:
            line = txt._line
            var = txt._var
            ax_idx = txt._axis

            bbox = txt.get_window_extent()
            click_x = event.mouseevent.x

            if click_x > bbox.x0 + bbox.width * 0.7:
                if var in plot_data[ax_idx]:
                    plot_data[ax_idx].remove(var)
                legend_state.pop(var, None)
            else:
                legend_state[var] = not line.get_visible()

            rebuild_axes()
            return

        selected_text["obj"] = txt

    canvas.mpl_connect("pick_event", on_pick)

    def set_vline():
        mode["type"] = "v"

    def set_hline():
        mode["type"] = "h"

    def clear_lines():
        for l, t, _ in lines:
            l.remove()
            t.remove()
        lines.clear()
        canvas.draw()

    tk.Button(toolbar, text="│", command=set_vline, relief="flat").pack(side="left")
    tk.Button(toolbar, text="─", command=set_hline, relief="flat").pack(side="left")
    tk.Button(toolbar, text="🗑", command=clear_lines, relief="flat").pack(side="left")

    def open_cutter():
        cutter_win = tk.Toplevel(root)
        cutter_win.title("Advanced Cutter")
        cutter_win.geometry("1200x800")

        paned = tk.PanedWindow(cutter_win, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        left_frame = tk.Frame(paned)
        right_frame = tk.Frame(paned)
        
        paned.add(left_frame, stretch="always")
        paned.add(right_frame, minsize=300)

        def set_pane_size():
            width = cutter_win.winfo_width()
            paned.sash_place(0, int(width * 0.75), 0)
        
        cutter_win.after(100, set_pane_size)

        def detect_time_precision():
            for val in df["Time"].astype(str):
                if "." in val:
                    return len(val.split(".")[1])
            return 0

        time_precision = detect_time_precision()

        def format_time_display(ts, precision):
            base = ts.strftime("%H:%M:%S")

            if precision == 0:
                return base

            frac = f"{ts.microsecond:06d}"

            frac = frac[:precision]

            frac = frac.rstrip("0")

            if frac == "":
                return base

            return base + "." + frac

        top_frame = tk.Frame(left_frame)
        top_frame.pack(fill="x", pady=10)

        for i in range(6):
            top_frame.columnconfigure(i, weight=1)

        tk.Label(top_frame, text="Start Date").grid(row=0, column=0, padx=5, sticky="w")
        start_date = tk.Entry(top_frame, width=12)
        start_date.grid(row=0, column=1, padx=(5, 15))

        tk.Label(top_frame, text="Start Time").grid(row=0, column=2, padx=5, sticky="w")
        start_time = tk.Entry(top_frame, width=15)
        start_time.grid(row=0, column=3, padx=5)

        tk.Label(top_frame, text="").grid(row=2, column=0, pady=5)

        tk.Label(top_frame, text="End Date").grid(row=3, column=0, padx=5, sticky="w")
        end_date = tk.Entry(top_frame, width=12)
        end_date.grid(row=3, column=1, padx=(5, 15))

        tk.Label(top_frame, text="End Time").grid(row=3, column=2, padx=5, sticky="w")
        end_time = tk.Entry(top_frame, width=15)
        end_time.grid(row=3, column=3, padx=5)

        output_path_var = tk.StringVar()
        full_default_path = final_csv_path.replace(".csv", "_cut.csv")
        default_filename = os.path.basename(full_default_path)
        output_path_var.set(default_filename)

        tk.Label(top_frame, text="").grid(row=4, column=0, pady=5)

        tk.Label(top_frame, text="Output file").grid(row=5, column=0, padx=5, sticky="w")
        output_entry = tk.Entry(top_frame, textvariable=output_path_var, width=80)
        output_entry.grid(row=5, column=1, columnspan=3, padx=5, pady=5, sticky="we")

        start_dt = df.index.min()
        end_dt = df.index.max()

        start_date.insert(0, str(start_dt.date()))
        start_time.insert(0, start_dt.strftime("%H:%M:%S"))

        end_date.insert(0, str(end_dt.date()))
        end_time.insert(0, end_dt.strftime("%H:%M:%S"))

        fig2 = plt.figure(figsize=(10, 5))
        canvas2 = FigureCanvasTkAgg(fig2, master=left_frame)
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        ax = fig2.add_subplot(111)

        plotted = []
        selected_var = {"name": None}
        legend_state = {}
        legend_links = {}

        def update_plot():
            ax.clear()
            legend_links.clear()

            try:
                start = pd.to_datetime(start_date.get() + " " + start_time.get())
                end = pd.to_datetime(end_date.get() + " " + end_time.get())
            except:
                return

            data = df.loc[(df.index >= start) & (df.index <= end)]

            lines_local = []
            labels = []

            for i, var in enumerate(plotted):
                legend_state.setdefault(var, True)

                y = pd.to_numeric(data[var], errors="coerce")
                line, = ax.plot(data.index, y)

                line.set_visible(legend_state[var])
                line._var = var

                lines_local.append(line)

                tick = "☑" if legend_state[var] else "☐"
                labels.append(f"{tick} {var}    ⨯")

            if lines_local:
                legend = ax.legend(lines_local, labels, fontsize=8)
                legend.set_draggable(True)

                for txt, line_obj, var in zip(legend.get_texts(), lines_local, plotted):
                    txt.set_picker(True)
                    txt._line = line_obj
                    txt._var = var
                    legend_links[txt] = line_obj

            ax.set_xlim(data.index.min(), data.index.max())
            ax.margins(x=0)

            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.3f}".rstrip("0").rstrip(".")))

            ax.grid(True)
            canvas2.draw()
        
        def on_pick(event):
            txt = event.artist

            if txt in legend_links:
                line = txt._line
                var = txt._var

                bbox = txt.get_window_extent()
                click_x = event.mouseevent.x

                if click_x > bbox.x0 + bbox.width * 0.7:
                    if var in plotted:
                        plotted.remove(var)
                    legend_state.pop(var, None)

                else:
                    legend_state[var] = not line.get_visible()

                update_plot()
        
        canvas2.mpl_connect("pick_event", on_pick)

        def on_time_change(event=None):
            update_plot()

        for w in [start_date, start_time, end_date, end_time]:
            w.bind("<KeyRelease>", on_time_change)

        search_var = tk.StringVar()
        tk.Entry(right_frame, textvariable=search_var).pack(fill="x", padx=5, pady=5)

        list_frame = tk.Frame(right_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        y_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        x_scroll = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL)

        listbox = tk.Listbox(list_frame,selectmode=tk.SINGLE,exportselection=False,yscrollcommand=y_scroll.set,xscrollcommand=x_scroll.set,font=("Segoe UI", 9))

        y_scroll.config(command=listbox.yview)
        x_scroll.config(command=listbox.xview)

        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        listbox.pack(side="left", fill="both", expand=True)

        def update_list(*args):
            search = search_var.get().lower()
            listbox.delete(0, tk.END)
            for v in variables:
                if search in v.lower():
                    listbox.insert(tk.END, v)

        update_list()
        search_var.trace_add("write", update_list)

        def on_list_select(event):
            for i in range(listbox.size()):
                listbox.itemconfig(i, {'bg': 'white'})

            selection = listbox.curselection()
            if not selection:
                return

            idx = selection[0]
            selected_var["name"] = listbox.get(idx)

            listbox.itemconfig(idx, {'bg': '#cce5ff'})

        def on_plot_click(event):
            if event.inaxes is None:
                return

            var = selected_var["name"]
            if not var:
                return

            if var not in plotted:
                plotted.append(var)
                update_plot()

            selected_var["name"] = None

        listbox.bind("<<ListboxSelect>>", on_list_select)
        canvas2.mpl_connect("button_press_event", on_plot_click)

        def process():
            try:
                start = pd.to_datetime(start_date.get() + " " + start_time.get())
                end = pd.to_datetime(end_date.get() + " " + end_time.get())
            except:
                messagebox.showerror("Error", "Invalid date/time")
                return

            filename = output_path_var.get().strip()

            if not filename.endswith(".csv"):
                filename += ".csv"

            folder = os.path.dirname(final_csv_path)
            output = os.path.join(folder, filename)

            if not output:
                messagebox.showerror("Error", "Please provide an output file path")
                return

            with open(final_csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            header_lines = []
            data_start_idx = None

            for i, line in enumerate(lines):
                parts = line.split(",")
                try:
                    pd.to_datetime(parts[0] + " " + parts[1])
                    data_start_idx = i
                    break
                except:
                    header_lines.append(line)

            raw_df = pd.read_csv(final_csv_path, skiprows=data_start_idx, header=None)

            dt = pd.to_datetime(raw_df.iloc[:, 0].astype(str) + " " + raw_df.iloc[:, 1].astype(str))

            mask = (dt >= start) & (dt <= end)
            raw_cut = raw_df.loc[mask]

            with open(output, "w", encoding="utf-8") as f:
                f.writelines(header_lines)

            raw_cut.to_csv(output, mode="a", index=False, header=False)

            messagebox.showinfo("Success", "Cutted file created")

        ttk.Button(right_frame, text="Process", command=process).pack(pady=10)

        def clear_all():
            plotted.clear()
            legend_state.clear()

            start_date.delete(0, tk.END)
            start_time.delete(0, tk.END)
            end_date.delete(0, tk.END)
            end_time.delete(0, tk.END)

            start_date.insert(0, str(start_dt.date()))
            start_time.insert(0, start_dt.strftime("%H:%M:%S"))

            end_date.insert(0, str(end_dt.date()))
            end_time.insert(0, end_dt.strftime("%H:%M:%S"))

            update_plot()

        ttk.Button(right_frame, text="Clear All", command=clear_all).pack(pady=5)
    
    def open_manual_vline():
        win = tk.Toplevel(plot_win)
        win.title("Add Vertical Line")

        def get_time_format_label():
            if source_selected in ["OPClogger", "MFR OPClogger"]:
                return "Enter Time (HH:MM:SS)"
            elif source_selected == "MFR TSDL":
                return "Enter Time (HH:MM:SS.ffffff)"
            elif source_selected in ["TSDL (Export CSV)", "TSDL (Export)"]:
                return "Enter Time (HH:MM:SS.mss)"
            else:
                return "Enter Time (HH:MM:SS.[mss,us,0])"

        ttk.Label(win, text=get_time_format_label()).pack(padx=10, pady=5)

        entry = tk.Entry(win, width=30)
        entry.pack(padx=10, pady=5)

        def apply():
            try:
                user_input = entry.get().strip()

                if source_selected in ["OPClogger", "MFR OPClogger"]:
                    fmt = "%H:%M:%S"
                elif source_selected == "MFR TSDL":
                    fmt = "%H:%M:%S.%f"
                else:
                    fmt = "%H:%M:%S.%f"

                parsed_time = pd.to_datetime(user_input, format=fmt, errors="coerce")

                if pd.isna(parsed_time):
                    raise ValueError("Invalid time format")

                target_time = parsed_time.time()

                nearest_time = min(
                    df.index,
                    key=lambda t: abs(
                        (t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6)
                        -
                        (target_time.hour * 3600 + target_time.minute * 60 + target_time.second + target_time.microsecond / 1e6)
                    )
                )

                def format_label(ts):
                    if source_selected in ["OPClogger", "MFR OPClogger"]:
                        return ts.strftime('%H:%M:%S').rstrip("0").rstrip(".")
                    elif source_selected == "MFR TSDL":
                        return f"{ts.strftime('%H:%M:%S')}.{ts.microsecond:06d}".rstrip("0").rstrip(".")
                    else:
                        ms = int(ts.microsecond / 1000)
                        return f"{ts.strftime('%H:%M:%S')}.{ms:03d}".rstrip("0").rstrip(".")

                label = format_label(nearest_time)

                for ax in axes:
                    line = ax.axvline(nearest_time, color="red", linestyle="--")

                    ylim = ax.get_ylim()

                    txt = ax.text(
                        nearest_time,
                        ylim[1] - (ylim[1] - ylim[0]) * 0.05,
                        label,
                        rotation=90,
                        color="red",
                        ha="right",
                        va="top",
                        picker=True
                    )
                    txt.set_clip_on(True)

                    lines.append((line, txt, ax))

                canvas.draw()
                win.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Invalid time\n{e}")

        ttk.Button(win, text="Apply", command=apply).pack(pady=10)

    def open_manual_hline():
        win = tk.Toplevel(plot_win)
        win.title("Add Horizontal Line")

        ttk.Label(win, text="Enter Y value:").pack(padx=10, pady=5)

        entry = tk.Entry(win, width=20)
        entry.pack(padx=10, pady=5)

        def apply():
            try:
                y = float(entry.get())

                for ax in axes:
                    line = ax.axhline(y, color="green", linestyle="--")

                    xlim = ax.get_xlim()

                    txt = ax.text(
                        xlim[1] - (xlim[1] - xlim[0]) * 0.01,
                        y,
                        f"{y:.3f}".rstrip("0").rstrip("."),
                        color="green",
                        ha="right",
                        va="bottom",
                        picker=True
                    )
                    txt.set_clip_on(True)

                    lines.append((line, txt, ax))

                canvas.draw()
                win.destroy()

            except:
                messagebox.showerror("Error", "Invalid Y value")

        ttk.Button(win, text="Apply", command=apply).pack(pady=10)

    tk.Button(toolbar, text="✂", command=open_cutter, relief="flat").pack(side="left")
    tk.Button(toolbar, text="│*", command=lambda: open_manual_vline(), relief="flat").pack(side="left")
    tk.Button(toolbar, text="─*", command=lambda: open_manual_hline(), relief="flat").pack(side="left")

    def on_click(event):
        if mode["type"] is None or event.inaxes is None:
            return

        ax = event.inaxes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        if mode["type"] == "v":
            x_time = mdates.num2date(event.xdata)
            x_time = pd.Timestamp(x_time).tz_localize(None)

            nearest_time = min(df.index, key=lambda t: abs(t - x_time))
            label = df.loc[nearest_time, "Time_clean"]

            line = ax.axvline(nearest_time, color="red", linestyle="--")

            txt = ax.text(
                x_time,
                ylim[1] - (ylim[1] - ylim[0]) * 0.05,
                label,
                rotation=90,
                color="red",
                ha="right",
                va="top",
                picker=True
            )

        else:
            y = event.ydata

            line = ax.axhline(y, color="green", linestyle="--")

            txt = ax.text(
                xlim[1] - (xlim[1] - xlim[0]) * 0.01,
                y,
                f"{y:.3f}".rstrip("0").rstrip("."),
                color="green",
                ha="right",
                va="bottom",
                picker=True
            )

        txt.set_clip_on(True)

        lines.append((line, txt, ax))
        canvas.draw()
        mode["type"] = None

    canvas.mpl_connect("button_press_event", on_click)

    def on_motion(event):
        if not mouse_pressed["state"]:
            return
        if selected_text["obj"] is None:
            return
        if event.inaxes is None:
            return

        selected_text["obj"].set_position((event.xdata, event.ydata))
        canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", on_motion)

    def clear_all():
        plot_data.clear()
        plot_data.append([])
        legend_state.clear()
        rebuild_axes()

    ttk.Button(right_frame, text="Clear All", command=clear_all).pack(pady=5)
    
    ttk.Button(right_frame,text="New Window",command=lambda: open_plot_window(root,final_csv_path,source_selected)).pack(pady=5)

def load_file():
    file_path = filedialog.askopenfilename(title="Select CSV",filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])

    if not file_path:
        return

    source = source_var.get()

    if not source:
        messagebox.showwarning("Warning", "Select source type")
        return

    open_plot_window(root, file_path, source)


root = tk.Tk()
root.title("Data Visualization Tool v0")
root.geometry("500x150")

ttk.Label(root, text="Source Type").pack(pady=(10, 0))

source_var = tk.StringVar()

source_combo = ttk.Combobox(root,textvariable=source_var,state="readonly",values=["OPClogger","MFR OPClogger","MFR TSDL","TSDL (Export CSV)","TSDL (Export)"])
source_combo.pack(fill="x", padx=20, pady=5)

ttk.Button(root,text="Load CSV",command=load_file).pack(pady=20)

root.mainloop()

