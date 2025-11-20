import os
import gc
import json
import logging
from pathlib import Path
import importlib.resources
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
import datview.lib.utilities as util
if os.environ.get("DISPLAY") is None and os.environ.get("MPLBACKEND") is None:
    matplotlib.use("Agg")
else:
    matplotlib.use("TkAgg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# ==============================================================================
#                          GUI Rendering
# ==============================================================================


FONT_SIZE = 11
FONT_WEIGHT = "normal"
TTK_THEME = "clam"
MAIN_WIN_RATIO = 0.8
TEXT_WIN_RATIO = 0.7
PLT_WIN_3D_RATIO = 0.85
PLT_WIN_2D_RATIO = 0.85
PLT_WIN_1D_RATIO = 0.6
PLT_1D_RATIO = 0.8
HIST_WIN_RATIO = 0.9
PLT_MAIN_FONTSIZE = 9
PLT_TEXT_FONTSIZE = 8
SCROLL_SENSITIVITY = 1
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
HDF_EXT = (".nxs", "nx", ".h5", ".hdf", ".hdf5")
TEXT_EXT = (".json", ".out", ".err", ".txt", ".yaml")
CINE_EXT = ".cine"


def get_icon_path():
    with importlib.resources.path("datview.assets", "datview_icon.png") as icon:
        return str(icon)


class ToolTip:
    """For creating a tooltip for a widget"""
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.delay = delay
        self._after_id = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip)

    def schedule_tooltip(self, event):
        if self.tooltip:
            return
        if self._after_id:
            self.widget.after_cancel(self._after_id)
        self._after_id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self):
        if not self._after_id:
            return
        self._after_id = None
        try:
            x, y, _, _ = self.widget.bbox("insert")
            if x is None:
                return
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() - 20
        except tk.TclError:
            return

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=self.text, background="yellow",
                          relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class DatviewRendering(tk.Tk):
    """
    For building GUI components.
    """
    def __init__(self):
        super().__init__()
        # Set GUI parameters
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.config(size=FONT_SIZE, weight=FONT_WEIGHT)
        self.option_add("*Font", default_font)
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.dpi = self.winfo_fpixels("1i")
        width, height, x_offset, y_offset = self.define_window_geometry(
            MAIN_WIN_RATIO)
        self.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        try:
            icon_path = get_icon_path()
            if icon_path and Path(icon_path).exists():
                icon = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon)
        except (tk.TclError, TypeError):
            pass
        self.title("Data Viewer")
        style = ttk.Style()
        style.theme_use(TTK_THEME)
        # Configure the main window's grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        # For base-folder selection widgets
        base_folder_frame = tk.LabelFrame(self, text="Base Folder", padx=0,
                                          pady=0)
        base_folder_frame.grid(row=0, column=0, columnspan=3, sticky="ew",
                               padx=5, pady=0)
        base_folder_frame.grid_columnconfigure(0, weight=1)
        self.base_folder_label = tk.Label(base_folder_frame, text="")
        self.base_folder_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.select_base_folder_button = ttk.Button(base_folder_frame,
                                                    text="Select Base Folder")
        self.select_base_folder_button.grid(row=0, column=1, sticky="e",
                                            padx=8, pady=(0, 8))
        # For the tree-view of a folder hierarchy
        self.folder_tree_view = ttk.Treeview(self, show="tree")
        self.folder_tree_view.column("#0", width=350, minwidth=250,
                                     stretch=tk.NO)
        self.folder_tree_view.grid(row=1, rowspan=2, column=0, sticky="nsew",
                                   padx=5, pady=5)
        # For file-list viewing
        self.file_list_view = tk.Listbox(self)
        self.file_list_view.grid(row=1, column=1, sticky="nsew", padx=5,
                                 pady=(5, 4))
        self.file_list_scrollbar = tk.Scrollbar(
            self, orient=tk.VERTICAL, command=self.file_list_view.yview)
        self.file_list_scrollbar.grid(row=1, column=2, sticky="ns", pady=(9, 9))
        self.file_list_view.config(yscrollcommand=self.file_list_scrollbar.set)
        self.file_list_scrollbar.config(command=self.file_list_view.yview)
        # For viewer and saver frame
        viewer_saver_frame = tk.Frame(self)
        viewer_saver_frame.grid(row=2, column=1, columnspan=2, sticky="ew",
                                padx=1, pady=2)
        # Interactive-viewer button
        self.interactive_viewer_button = ttk.Button(viewer_saver_frame,
                                                    width=20,
                                                    text="Interactive Viewer")
        self.interactive_viewer_button.grid(row=0, column=0, sticky="w",
                                            padx=5, pady=(0, 5))
        ttip_viewer_button = ("View a dataset (array) in a HDF file, "
                              "or multiple image files in a folder")
        ToolTip(self.interactive_viewer_button, ttip_viewer_button)
        # Table-viewer button
        self.table_viewer_button = ttk.Button(viewer_saver_frame, width=20,
                                              text="Table Viewer")
        self.table_viewer_button.grid(row=0, column=1, sticky="w", padx=5,
                                      pady=(0, 5))
        ToolTip(self.table_viewer_button, "Show the table format of "
                                          "a 1D- or 2D-array")
        # HDF keys combobox
        self.hdf_key_list = ttk.Combobox(viewer_saver_frame, state="disabled",
                                         width=40)
        self.hdf_key_list.grid(row=0, column=2, sticky="w", padx=5, pady=(0, 5))
        ToolTip(self.hdf_key_list, "HDF keys to array-like datasets")
        # Save-image button
        self.save_image_button = ttk.Button(viewer_saver_frame, width=20,
                                            text="Save image")
        self.save_image_button.grid(row=1, column=0, sticky="w", padx=5,
                                    pady=(0, 5))
        ttip_save_image_button = "Save a slice of 3d-array dataset to image"
        ToolTip(self.save_image_button, ttip_save_image_button)
        # Save-table button
        self.save_table_button = ttk.Button(viewer_saver_frame, width=20,
                                            text="Save table")
        self.save_table_button.grid(row=1, column=1, sticky="w", padx=5,
                                    pady=(0, 5))
        ttip_save_table_button = "Save 1d- or 2d-array dataset to a csv file"
        ToolTip(self.save_table_button, ttip_save_table_button)
        # Export-to-tif button
        self.export_tif_button = ttk.Button(viewer_saver_frame, width=20,
                                            text="Export to tif")
        self.export_tif_button.grid(row=1, column=2, sticky="w", padx=5,
                                    pady=(0, 5))
        ttip_export_tif_button = "Export 3d-array HDF/CINE dataset to TIF files"
        ToolTip(self.export_tif_button, ttip_export_tif_button)
        # Status bar
        self.status_bar = tk.Text(self, height=1, state="disabled", wrap="none",
                                  bg="lightgrey")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew",
                             padx=5, pady=(0, 5))

    def define_window_geometry(self, ratio):
        """Specify size of a widget window"""
        width = int(self.screen_width * ratio)
        height = int(self.screen_height * ratio)
        x_offset = (self.screen_width - width) // 2
        y_offset = (self.screen_height - height) // 2
        return width, height, x_offset, y_offset

    def display_text_file(self, file_path):
        """Display content of a text file or cine metadata in a new window"""
        extension = Path(file_path).suffix.lower()
        try:
            text_window = tk.Toplevel(self)
            text_window.title(f"Viewing: {file_path}")
            width, height, x_offset, y_offset = self.define_window_geometry(
                TEXT_WIN_RATIO)
            text_window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")

            text_area = tk.Text(text_window, wrap=tk.WORD)
            text_scrollbar = tk.Scrollbar(text_window, orient=tk.VERTICAL,
                                          command=text_area.yview)
            text_area.config(yscrollcommand=text_scrollbar.set)
            text_area.pack(side=tk.LEFT, expand=True, fill="both")
            text_scrollbar.pack(side=tk.RIGHT, fill="y")
            if extension == ".cine":
                metadata = util.get_metadata_cine(file_path)
                formatted_metadata = json.dumps(metadata, indent=4)
                text_area.insert(tk.END, formatted_metadata)
            else:
                with open(file_path, "r") as file:
                    content = file.read()
                text_area.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the file: {e}")

    def show_1d_data(self, array_1d, help_text="", title=""):
        """Display a graph of 1d data."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update({'font.family': font_family,
                                 'font.size': FONT_SIZE})
        except:
            pass
        fig, ax = plt.subplots(figsize=((width / dpi) * PLT_1D_RATIO,
                                        (height / dpi) * PLT_1D_RATIO), dpi=dpi)
        ax.plot(array_1d, color="blue", linewidth=1.0)
        ax.set_aspect("auto")
        if len(help_text) > 0:
            ax.set_title(help_text)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def table_viewer(self, data, title="Array Table Viewer"):
        """Display 1d or 2d-data as table format"""
        window = tk.Toplevel(self)
        window.title(title)
        width, height, x_offset, y_offset = self.define_window_geometry(
            TEXT_WIN_RATIO)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        text_widget = tk.Text(window, wrap="none", font=("Courier", 11))
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb = tk.Scrollbar(window, orient="vertical", command=text_widget.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = tk.Scrollbar(window, orient="horizontal",
                           command=text_widget.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        def format_value(val):
            """Format the values with proper width"""
            if isinstance(val, float):
                return f"{val:.5g}" if abs(val) < 1e-5 or abs(
                    val) > 1e5 else f"{val:.5f}"
            return str(val)

        def calculate_max_width(data, headers):
            """Calculate the maximum width for each column"""
            col_widths = [len(header) for header in headers]
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    val_length = len(format_value(data[i, j]))
                    col_widths[j] = max(col_widths[j], val_length)
            return col_widths

        def format_table_row(row_values, col_widths):
            """Format the row based on column widths"""
            return " ".join([f"{val:>{width_t}}" for val, width_t in
                             zip(row_values, col_widths)])

        row_index_width = len(f"Row {data.shape[0] - 1}: ")
        text_length = len(str(data.shape[0] - 1))

        def display_array_as_text():
            """Format and display the data in the Text widget"""
            nonlocal row_index_width, text_length
            if len(data.shape) == 1:
                for i in range(data.shape[0]):
                    formatted_value = format_value(data[i])
                    msg = f"Row {i:0{text_length}}: {formatted_value}\n"
                    text_widget.insert(tk.END, msg)
            else:
                headers = [f"Col {j:0{text_length}}" for j in
                           range(data.shape[1])]
                col_widths = calculate_max_width(data, headers)
                header = " " * row_index_width \
                         + format_table_row(headers[:], col_widths[:]) + "\n"
                text_widget.insert(tk.END, header)
                for i in range(data.shape[0]):
                    row_header = f"Row {i:0{text_length}}: "  # Row header
                    row_values = [format_value(data[i, j]) for j in
                                  range(data.shape[1])]
                    text_widget.insert(tk.END, row_header + format_table_row(
                        row_values, col_widths[:]) + "\n")

        display_array_as_text()
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)

        def on_close():
            self.current_image = None
            self.current_table = None
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def show_histogram(self, mat, help_text="", title=""):
        """Display histogram of an image."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update({'font.family': font_family,
                                 'font.size': FONT_SIZE})
        except:
            pass
        flat_data = mat.ravel()
        try:
            p1 = np.percentile(flat_data, 0.5)
            p99 = np.percentile(flat_data, 99.5)
            # Handle edge case where data is all one value
            if p1 == p99:
                p1 = flat_data.min() - 1
                p99 = flat_data.max() + 1
            hist_range = (p1, p99)
        except IndexError:
            hist_range = None
        num_bins = 256
        hist, bin_edges = np.histogram(flat_data, bins=num_bins,
                                       range=hist_range)
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        fig, ax = plt.subplots(figsize=((width / dpi) * HIST_WIN_RATIO,
                                        (height / dpi) * HIST_WIN_RATIO),
                               dpi=dpi)
        ax.bar(bin_edges[:-1], hist, width=bin_widths,
               color='gray', edgecolor='black', alpha=0.5,
               align='edge',
               label=f"Num bins: {num_bins}")
        ax.set_title("Histogram " + help_text)
        ax.set_xlabel("Grayscale")
        ax.set_ylabel("Frequency (Count)")
        ax.legend()
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def show_statistics_table(self, stats_dict, help_text="",
                              title="Image Statistics"):
        """
        Display calculated statistics. Input is a dictionary from
        get_image_statistics.
        """
        if stats_dict is None:
            messagebox.showwarning("No Data",
                                   "No statistics to display")
            return
        window = tk.Toplevel(self)
        window.title(title + " | " + help_text)
        window.resizable(True, False)
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        win_w = window.winfo_width()
        win_h = window.winfo_height()
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        window.geometry(f"+{x}+{y}")

        tree = ttk.Treeview(window, columns=("Metric", "Value"),
                            show="headings")
        tree.heading("Metric", text="Metric")
        tree.heading("Value", text="Value")
        tree.column("Metric", width=150)
        tree.column("Value", width=220, anchor="e")
        tree.pack(padx=10, pady=10)
        for metric, value in stats_dict.items():
            formatted_value = f"{value:.5f}"
            tree.insert("", "end", values=(metric, formatted_value))
        window.update_idletasks()

    def show_percentile_plot(self, percentiles, density, help_text="",
                             title=""):
        """
        Displays a percentile density plot.
        percentiles: The x-axis values (percentiles).
        density: The y-axis values (normalized density).
        """
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update({'font.family': font_family,
                                 'font.size': FONT_SIZE})
        except:
            pass

        fig, ax = plt.subplots(figsize=((width / dpi) * PLT_1D_RATIO,
                                        (height / dpi) * PLT_1D_RATIO),
                               dpi=dpi)
        ax.plot(percentiles, density, marker='.', linestyle='-', color='blue')
        ax.set_title("Percentile density " + help_text)
        ax.set_xlabel("Percentile")
        ax.set_ylabel("Normalized density")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_xlim(0, 100)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def show_2d_image(self, img, file_path=""):
        """
        Display an image with sliders for adjusting contrast
        """
        self.current_image = np.asarray(img)
        is_color = False
        if (self.current_image.ndim == 3
                and self.current_image.shape[2] in [3, 4]):
            is_color = True
            nmin, nmax = np.min(self.current_image), np.max(self.current_image)
            if nmax > nmin:
                self.current_image = (self.current_image - nmin) / (nmax - nmin)
            self.current_image = np.clip(self.current_image, 0.0, 1.0)
        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)

        settings = self.define_window_geometry(PLT_WIN_2D_RATIO)
        win_width, win_height, x_offset, y_offset = settings

        window = tk.Toplevel(self)
        window.title(f"Viewing: {os.path.basename(file_path)}")
        window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")
        window.message_text_var = tk.StringVar(master=window, value=file_path)

        min_contrast_var = tk.DoubleVar(master=window, value=0.0)
        max_contrast_var = tk.DoubleVar(master=window, value=1.0)
        min_contrast_label_var = tk.StringVar(master=window, value="0.0")
        max_contrast_label_var = tk.StringVar(master=window, value="100.0")


        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update({'font.family': font_family,
                                 'font.size': FONT_SIZE})
        except:
            pass

        # Button style
        style = ttk.Style()
        style.theme_use(TTK_THEME)
        style.configure("Short.TButton", padding=[5, 1, 5, 1])

        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=0)
        window.rowconfigure(2, weight=0)
        window.columnconfigure(0, weight=1)

        canvas_frame = ttk.Frame(window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame,
                                  textvariable=window.message_text_var,
                                  wraplength=win_width, anchor=tk.W)
        message_label.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        fig_img, ax_img = plt.subplots(constrained_layout=True, dpi=dpi)
        ax_img.set_title(f"Height x Width : {self.current_image.shape[0]} "
                         f"x {self.current_image.shape[1]}")
        ax_img.set_xlabel("X")
        ax_img.set_ylabel("Y")
        ax_img.set_aspect("equal")

        if is_color:
            slice0 = ax_img.imshow(self.current_image)
        else:
            vmin_init = np.percentile(self.current_image, 0)
            vmax_init = np.percentile(self.current_image, 100)
            slice0 = ax_img.imshow(self.current_image, cmap="gray",
                                   vmin=vmin_init, vmax=vmax_init)

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.rowconfigure(1, weight=0)
        canvas_frame.columnconfigure(0, weight=1)
        window.update_idletasks()
        canvas_img = FigureCanvasTkAgg(fig_img, master=canvas_frame)
        canvas_img.draw()
        canvas_img.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(canvas_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar_frame.columnconfigure(0, weight=1)
        toolbar = NavigationToolbar2Tk(canvas_img, toolbar_frame)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")

        if not is_color:
            control_frame.columnconfigure(0, weight=0)
            control_frame.columnconfigure(1, weight=1)
            control_frame.columnconfigure(2, weight=0)
            control_frame.columnconfigure(3, weight=0)
            control_frame.columnconfigure(4, weight=0)
            control_frame.rowconfigure(0, weight=0)
            control_frame.rowconfigure(1, weight=0)
            ttk.Label(control_frame,
                      text="Min %:").grid(row=0, column=0, sticky='w',
                                          padx=(10, 5), pady=(5, 0))
            min_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                                   orient=tk.HORIZONTAL,
                                   variable=min_contrast_var)
            min_slider.grid(row=0, column=1, sticky='ew', padx=5, pady=(5, 0))
            min_label = ttk.Label(control_frame,
                                  textvariable=min_contrast_label_var, width=5)
            min_label.grid(row=0, column=2, sticky='w', padx=(0, 10),
                           pady=(5, 0))

            ttk.Label(control_frame,
                      text="Max %:").grid(row=1, column=0, sticky='w',
                                          padx=(10, 5), pady=(0, 5))
            max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                                   orient=tk.HORIZONTAL,
                                   variable=max_contrast_var)
            max_slider.grid(row=1, column=1, sticky='ew', padx=5, pady=(0, 5))
            max_label = ttk.Label(control_frame,
                                  textvariable=max_contrast_label_var, width=5)
            max_label.grid(row=1, column=2, sticky='w', padx=(0, 10),
                           pady=(0, 5))

            reset_button = ttk.Button(control_frame, text="Reset",
                                      style="Short.TButton")
            reset_button.grid(row=0, column=3, sticky='ew', padx=5, pady=5)

            statistics_button = ttk.Button(control_frame, text="Statistics",
                                           style="Short.TButton")
            statistics_button.grid(row=0, column=4, sticky='ew', padx=(0, 5),
                                   pady=5)

            histogram_button = ttk.Button(control_frame, text="Histogram",
                                          style="Short.TButton")
            histogram_button.grid(row=1, column=3, sticky='ew', padx=5,
                                  pady=(0, 5))

            percentile_button = ttk.Button(control_frame, text="Percentile",
                                           style="Short.TButton")
            percentile_button.grid(row=1, column=4, sticky='ew', padx=(0, 5),
                                   pady=(0, 5))

            aspect_var = tk.StringVar(master=window, value="equal")
            aspect_label = ttk.Label(control_frame, text="Aspect")
            aspect_combo = ttk.Combobox(control_frame, textvariable=aspect_var,
                                        values=["equal", "auto"], width=5)
            aspect_label.grid(row=0, column=5, sticky='w', padx=0, pady=5)
            aspect_combo.grid(row=1, column=5, sticky='ewns', padx=(0, 5),
                              pady=(0, 5))

            def update_aspect_ratio(event=None):
                """
                Updates the aspect ratio.
                """
                val = aspect_var.get().strip()
                if val.lower() in ["equal", "auto"]:
                    new_aspect = val.lower()
                else:
                    try:
                        new_aspect = float(val)
                    except ValueError:
                        aspect_var.set("equal")
                        new_aspect = "equal"
                ax_img.set_aspect(new_aspect)
                canvas_img.draw_idle()

            aspect_combo.bind("<<ComboboxSelected>>", update_aspect_ratio)
            aspect_combo.bind("<Return>", update_aspect_ratio)

        if not is_color:

            def on_contrast_change(value):
                if self.current_image is None:
                    return
                min_val = min_contrast_var.get()
                max_val = max_contrast_var.get()
                p_min = min_val * 100.0
                p_max = max_val * 100.0
                min_contrast_label_var.set(f"{p_min:.1f}")
                max_contrast_label_var.set(f"{p_max:.1f}")
                if p_min >= p_max:
                    if p_max > 0.0:
                        p_min = p_max - 0.1
                        min_contrast_var.set(p_min / 100.0)
                    else:
                        p_min, p_max = 0.0, 0.1
                        min_contrast_var.set(0.0)
                        max_contrast_var.set(0.001)
                vmin = np.percentile(self.current_image, p_min)
                vmax = np.percentile(self.current_image, p_max)
                if vmin == vmax:  # Handle flat data
                    vmin = vmin - 0.5
                    vmax = vmax + 0.5
                slice0.set_clim(vmin, vmax)
                canvas_img.draw_idle()

            def reset_contrast(event=None):
                """
                Resets the contrast sliders and updates the image.
                """
                min_contrast_var.set(0.0)
                max_contrast_var.set(1.0)
                on_contrast_change(None)

            def open_statistics():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                stats = util.get_image_statistics(self.current_image)
                title = f"Statistics: {os.path.basename(file_path)}"
                self.show_statistics_table(stats, title=title)

            def open_histogram():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                title = f"Histogram: {os.path.basename(file_path)}"
                self.show_histogram(self.current_image, help_text="",
                                    title=title)

            def open_percentile():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                try:
                    percentiles, density = util.get_percentile_density(
                        self.current_image)
                except ValueError as e:
                    messagebox.showerror("Error",
                                         f"Could not get percentiles:\n{e}")
                    return
                title = f"Percentile plot: {os.path.basename(file_path)}"
                self.show_percentile_plot(percentiles, density, title=title)

            min_slider.config(command=on_contrast_change)
            max_slider.config(command=on_contrast_change)
            reset_button.config(command=reset_contrast)
            statistics_button.config(command=open_statistics)
            histogram_button.config(command=open_histogram)
            percentile_button.config(command=open_percentile)

        def on_close():
            self.current_image = None
            self.current_table = None
            plt.close(fig_img)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def interactive_viewer(self, file_path, file_type):
        """
        Display an image of a 3D array from a hdf file, cine file, or a folder
        of tif files. Includes sliders to adjust contrast, view different
        images, and a line-profile plot based on the mouse-clicked position.
        """
        clicked_point, hline, vline = None, None, None
        img, data = None, None
        slider1 = None
        list_files = []
        self.current_idx = 0
        self.current_axis = 0

        if file_type == "tif":
            list_files = util.find_file(file_path)
            if not list_files:
                messagebox.showerror("No Files",
                                     f"No TIF files found in: {file_path}")
                return
            img = util.load_image(list_files[0])
            (height, width) = img.shape
            depth = len(list_files)
            current_path = file_path

        elif file_type == "cine":
            cine_metadata = util.get_metadata_cine(file_path)
            width = cine_metadata["biWidth"]
            height = cine_metadata["biHeight"]
            depth = cine_metadata["TotalImageCount"]
            img = util.extract_frame_cine(file_path, 0)
            current_path = file_path

        else:  # HDF5
            selected_index = self.file_list_view.curselection()
            selected_file = self.file_list_view.get(selected_index[0])
            full_path = os.path.join(self.selected_folder_path, selected_file)
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data = util.load_hdf(full_path, hdf_key_path)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return

            if 1 in data.shape:
                data = np.squeeze(data)

            if len(data.shape) == 1:
                self.current_table = data[:]
                self.show_1d_data(self.current_table,
                                  help_text="HDF-key: " + hdf_key_path,
                                  title=file_path)
                return
            elif len(data.shape) == 2:
                self.current_table = data[:]
                self.show_2d_image(self.current_table, full_path)
                return
            elif len(data.shape) != 3:
                messagebox.showerror("Can't show data",
                                     f"File: {selected_file}\nOnly can "
                                     f"show 1d, 2d, or 3d data. "
                                     f"Not {len(data.shape)}d")
                return

            (depth, height, width) = data.shape
            img = data[0, :, :]
            current_path = full_path

        self.current_image = img
        settings = self.define_window_geometry(PLT_WIN_3D_RATIO)
        win_width, win_height, x_offset, y_offset = settings

        window = tk.Toplevel(self)
        window.update_job = None
        window.title(f"Viewing: {os.path.basename(current_path)}")
        window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")

        message_text_var = tk.StringVar(master=window, value=current_path)
        axis_var = tk.StringVar(master=window, value="axis 0")
        slice0_var = tk.IntVar(master=window, value=0)
        slice1_var = tk.IntVar(master=window, value=0)
        min_contrast_var = tk.DoubleVar(master=window, value=0.0)
        max_contrast_var = tk.DoubleVar(master=window, value=1.0)

        slice0_label_var = tk.StringVar(master=window, value="0")
        slice1_label_var = tk.StringVar(master=window, value="0")
        min_contrast_label_var = tk.StringVar(master=window, value="0.0")
        max_contrast_label_var = tk.StringVar(master=window, value="100.0")

        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update(
                {'font.family': font_family, 'font.size': FONT_SIZE})
        except:
            pass

        # --- Configure window's grid ---
        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=0)
        window.rowconfigure(2, weight=0)
        window.columnconfigure(0, weight=1)
        # --- Create and grid the frames ---
        canvas_frame = ttk.Frame(window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame, textvariable=message_text_var,
                                  wraplength=win_width - 100, anchor=tk.W)
        message_label.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        # Setup Matplotlib Figures
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=3)
        canvas_frame.columnconfigure(1, weight=2)
        canvas_frame.rowconfigure(1, weight=0)

        image_frame = ttk.Frame(canvas_frame)
        image_frame.grid(row=0, column=0, sticky="nsew")
        plot_frame = ttk.Frame(canvas_frame)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        toolbar_frame = ttk.Frame(canvas_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew", columnspan=2)
        # Figure 1: To show image
        fig_img, ax_img = plt.subplots(constrained_layout=True, dpi=dpi)
        ax_img.set_title(f"Axis: {0}. Index: {0}. "
                         f"H x W: {height} x {width}")
        ax_img.set_xlabel("X")
        ax_img.set_ylabel("Y")
        ax_img.set_aspect("equal")
        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)
        vmin_init = np.percentile(self.current_image, 0)
        vmax_init = np.percentile(self.current_image, 100)

        slice0 = ax_img.imshow(self.current_image, cmap="gray", vmin=vmin_init,
                               vmax=vmax_init)
        slice0.set_extent([0, width, height, 0])
        # Figure 2: To show intensity-plot
        fig_plot, ax_plot = plt.subplots(constrained_layout=False, dpi=dpi)
        ax_plot.set_title("Line Profile")
        ax_plot.set_box_aspect(np.clip(0.95 * width / height, 0.8, 1.1))

        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        window.update_idletasks()
        canvas_img = FigureCanvasTkAgg(fig_img, master=image_frame)
        canvas_img.draw()
        canvas_img.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        plot_frame.rowconfigure(0, weight=1)
        plot_frame.columnconfigure(0, weight=1)
        canvas_plot = FigureCanvasTkAgg(fig_plot, master=plot_frame)
        canvas_plot.draw()
        canvas_plot.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame.columnconfigure(0, weight=1)
        toolbar = NavigationToolbar2Tk(canvas_img, toolbar_frame)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")

        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=3)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=0)
        control_frame.columnconfigure(4, weight=2)
        control_frame.columnconfigure(5, weight=0)
        control_frame.columnconfigure(6, weight=0)

        control_frame.rowconfigure(0, weight=0)
        control_frame.rowconfigure(1, weight=0)

        if data is not None:
            axis0_radio = ttk.Radiobutton(control_frame, text="Axis 0",
                                          variable=axis_var, value="axis 0")
            axis0_radio.grid(row=0, column=0, sticky='w', padx=(10, 5), pady=2)

            slider0 = ttk.Scale(control_frame, from_=0, to=depth - 1,
                                orient=tk.HORIZONTAL, variable=slice0_var)
            slider0.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
            slice0_label = ttk.Label(control_frame,
                                     textvariable=slice0_label_var, width=4)
            slice0_label.grid(row=0, column=2, sticky='w', padx=(0, 10))
        else:
            ttk.Label(control_frame, text="Slice:").grid(row=0, column=0,
                                                         sticky='e',
                                                         padx=(10, 5), pady=2)
            slider0 = ttk.Scale(control_frame, from_=0, to=depth - 1,
                                orient=tk.HORIZONTAL, variable=slice0_var)
            slider0.grid(row=0, column=1, sticky='ew', padx=5, pady=2)

            slice0_label = ttk.Label(control_frame,
                                     textvariable=slice0_label_var, width=4)
            slice0_label.grid(row=0, column=2, sticky='w', padx=(0, 10))

        ttk.Label(control_frame, text="Min %:").grid(row=0, column=3,
                                                     sticky='w', padx=(10, 5),
                                                     pady=2)
        min_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL, variable=min_contrast_var)
        min_slider.grid(row=0, column=4, sticky='ew', padx=5, pady=2)
        min_label = ttk.Label(control_frame,
                              textvariable=min_contrast_label_var, width=5)
        min_label.grid(row=0, column=5, sticky='w', padx=(0, 10))

        ttk.Label(control_frame, text="Max %:").grid(row=1, column=3,
                                                     sticky='w', padx=(10, 5),
                                                     pady=2)
        max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL, variable=max_contrast_var)
        max_slider.grid(row=1, column=4, sticky='ew', padx=5, pady=2)
        max_label = ttk.Label(control_frame,
                              textvariable=max_contrast_label_var, width=5)
        max_label.grid(row=1, column=5, sticky='w', padx=(0, 10))

        style = ttk.Style()
        style.theme_use(TTK_THEME)
        style.configure("Short.TButton", padding=[5, 1, 5, 1])

        reset_button = ttk.Button(control_frame, text="Reset",
                                  style="Short.TButton")
        reset_button.grid(row=0, column=6, sticky='ew', padx=5, pady=(5, 0))

        def open_statistics():
            """
            Wrapper to calculate stats and then call the display function.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            stats = util.get_image_statistics(self.current_image)
            title = f"Statistics: {os.path.basename(current_path)}"
            help_text = f" Slice: {self.current_idx}. Axis {self.current_axis}"
            self.show_statistics_table(stats, title=title, help_text=help_text)

        statistics_button = ttk.Button(control_frame, text="Statistics",
                                       command=open_statistics,
                                       style="Short.TButton")
        statistics_button.grid(row=0, column=7, sticky='ew', padx=(0, 5),
                               pady=(5, 0))

        def open_histogram():
            """
            Wrapper function to get the current image and show its histogram.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            title = f"{os.path.basename(current_path)}"
            help_text = f" slice: {self.current_idx} axis: {self.current_axis}."
            self.show_histogram(self.current_image, help_text=help_text,
                                title=title)

        histogram_button = ttk.Button(control_frame, text="Histogram",
                                      command=open_histogram,
                                      style="Short.TButton")
        histogram_button.grid(row=1, column=6, sticky='ew', padx=5, pady=5)

        def open_percentile():
            """
            Wrapper to calculate percentile density and display the plot.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            try:
                percentiles, density = util.get_percentile_density(
                    self.current_image)
            except ValueError as e:
                messagebox.showerror("Error",
                                     f"Could not calculate percentiles:\n{e}")
                return
            title = f"Percentile Plot: {os.path.basename(current_path)}"
            help_text = f" slice: {self.current_idx} axis: {self.current_axis}"
            self.show_percentile_plot(percentiles, density,
                                      help_text=help_text, title=title)
        percentile_button = ttk.Button(control_frame, text="Percentile",
                                       command=open_percentile,
                                       style="Short.TButton")
        percentile_button.grid(row=1, column=7, sticky='ew', padx=(0, 5),
                               pady=5)

        ttk.Label(control_frame, text="Aspect").grid(row=0, column=8,
                                                     sticky='w', padx=(0, 5),
                                                     pady=5)
        aspect_var = tk.StringVar(master=window, value="equal")
        aspect_combo = ttk.Combobox(control_frame, textvariable=aspect_var,
                                    values=["equal", "auto"], width=5)
        aspect_combo.grid(row=1, column=8, sticky='ewns', padx=(0, 5), pady=5)

        if data is not None:
            axis1_radio = ttk.Radiobutton(control_frame, text="Axis 1",
                                          variable=axis_var, value="axis 1")
            axis1_radio.grid(row=1, column=0, sticky='w', padx=(10, 5), pady=2)

            slider1 = ttk.Scale(control_frame, from_=0, to=height - 1,
                                orient=tk.HORIZONTAL, variable=slice1_var,
                                state=tk.DISABLED)
            slider1.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
            slice1_label = ttk.Label(control_frame,
                                     textvariable=slice1_label_var, width=4)
            slice1_label.grid(row=1, column=2, sticky='w', padx=(0, 10))

        def clear_plot_lines(clear_all=False):
            """Clears plot lines."""
            nonlocal clicked_point, hline, vline
            ax_plot.clear()
            ax_plot.set_title("Line Profile")
            ax_plot.set_xlabel("")
            ax_plot.autoscale()
            canvas_plot.draw_idle()
            if hline:
                hline.set_visible(False)
                hline = None
            if vline:
                vline.set_visible(False)
                vline = None
            if clear_all:
                clicked_point = None
            canvas_img.draw_idle()

        def update_profile_plot():
            """
            Updates the line profile plot based on the current clicked_point
            and matches the zoom of the image canvas.
            """
            nonlocal clicked_point, hline, vline
            if clicked_point is None or self.current_image is None:
                ax_plot.clear()
                ax_plot.set_title("Line Profile")
                ax_plot.set_xlabel("")
                ax_plot.autoscale()
                canvas_plot.draw_idle()
                return
            y, x = clicked_point
            ax_plot.clear()
            if hline:
                self.current_table = self.current_image[y, :]
                ax_plot.plot(self.current_table, color="blue", linewidth=0.8)
                ax_plot.set_title(f"Intensity at row: {y}")
                ax_plot.set_xlabel("X")
                x_min, x_max = ax_img.get_xlim()
                ax_plot.set_xlim(x_min, x_max)
            elif vline:
                self.current_table = self.current_image[:, x]
                ax_plot.plot(self.current_table, color="blue", linewidth=0.8)
                ax_plot.set_title(f"Intensity at column: {x}")
                y_min, y_max = ax_img.get_ylim()
                ax_plot.set_xlim(y_max, y_min)
                ax_plot.set_xlabel("Y")

            px_min, px_max = ax_plot.get_xlim()
            idx_start = int(max(0, min(px_min, px_max)))
            idx_end = int(min(len(self.current_table), max(px_min, px_max)))
            if idx_end > idx_start:
                local_data = self.current_table[idx_start:idx_end]
                if local_data.size > 0:
                    local_min = np.nanmin(local_data)
                    local_max = np.nanmax(local_data)
                    yrange = local_max - local_min
                    pad = yrange * 0.05 if yrange != 0 else 1.0
                    ax_plot.set_ylim(local_min - pad, local_max + pad)
            canvas_plot.draw_idle()

        def perform_update(value):
            """
            The HEAVY function: Reads from disk and redraws Matplotlib.
            Only runs when the user stops dragging the slider.
            """
            nonlocal img, height, width
            window.update_job = None
            active_axis = axis_var.get()
            p_min = min_contrast_var.get() * 100.0
            p_max = max_contrast_var.get() * 100.0
            raw_aspect = aspect_var.get().strip()
            aspect_val = "equal"
            if raw_aspect.lower() in ["equal", "auto"]:
                aspect_val = raw_aspect.lower()
            else:
                try:
                    aspect_val = float(raw_aspect)
                except ValueError:
                    pass

            if active_axis == "axis 0" or data is None:
                index = slice0_var.get()
                self.current_axis = 0
                if file_type == "tif":
                    img = util.load_image(list_files[index])
                    message_text_var.set(list_files[index])
                    (new_height, new_width) = img.shape
                    if new_height != height or new_width != width:
                        clear_plot_lines(clear_all=True)
                    height, width = new_height, new_width
                elif file_type == "cine":
                    img = util.extract_frame_cine(file_path, index)
                    message_text_var.set(file_path)
                else:
                    img = data[index, :, :]
                    message_text_var.set(current_path)
                ax_img.set_title(
                    f"Axis: 0. Index: {index}. H x W: {height} x {width}")
                slice0.set_extent([0, width, height, 0])
                ax_img.set_aspect(aspect_val)
            else:  # axis 1 (HDF5 only)
                index = slice1_var.get()
                self.current_axis = 1
                img = data[:, index, :]
                message_text_var.set(current_path)
                ax_img.set_title(
                    f"Axis: 1. Index: {index}. H x W: {depth} x {width}")
                slice0.set_extent([0, width, depth, 0])
                ax_img.set_aspect(aspect_val)

            self.current_idx = index
            self.current_image = img

            if np.isnan(self.current_image).any():
                self.current_image = np.nan_to_num(self.current_image)

            vmin = np.percentile(self.current_image, p_min)
            vmax = np.percentile(self.current_image, p_max)
            if vmin == vmax:
                vmin = vmin - 0.5
                vmax = vmax + 0.5
            slice0.set_data(self.current_image)
            slice0.set_clim(vmin, vmax)
            canvas_img.draw_idle()
            update_profile_plot()

        def on_slice_change(value):
            """
            Lightweight debouncer.
            """
            active_axis = axis_var.get()
            if value is None:
                if active_axis == "axis 0":
                    value = slice0_var.get()
                else:
                    value = slice1_var.get()
            val_int = int(float(value))
            if active_axis == "axis 0":
                slice0_label_var.set(f"{val_int}")
            else:
                slice1_label_var.set(f"{val_int}")
            if window.update_job:
                try:
                    window.after_cancel(window.update_job)
                except ValueError:
                    pass
            window.update_job = window.after(10, lambda: perform_update(value))

        def on_contrast_change(value):
            """
            Called when contrast sliders move.
            """
            if self.current_image is None:
                return
            min_val = min_contrast_var.get()
            max_val = max_contrast_var.get()
            p_min = min_val * 100.0
            p_max = max_val * 100.0
            min_contrast_label_var.set(f"{p_min:.1f}")
            max_contrast_label_var.set(f"{p_max:.1f}")
            if p_min >= p_max:
                if p_max > 0.0:
                    p_min = p_max - 0.1
                    min_contrast_var.set(p_min / 100.0)
                else:
                    p_min, p_max = 0.0, 0.1
                    min_contrast_var.set(0.0)
                    max_contrast_var.set(0.001)
            vmin = np.percentile(self.current_image, p_min)
            vmax = np.percentile(self.current_image, p_max)
            if vmin == vmax:  # Handle flat data
                vmin = vmin - 0.5
                vmax = vmax + 0.5
            slice0.set_clim(vmin, vmax)
            canvas_img.draw_idle()

        def reset_contrast(event=None):
            """
            Resets the contrast sliders and updates the image.
            """
            min_contrast_var.set(0.0)
            max_contrast_var.set(1.0)
            on_contrast_change(None)

        def on_axis_select():
            if slider1 is None:
                return
            if axis_var.get() == "axis 0":
                slider0.config(state=tk.NORMAL)
                slider1.config(state=tk.DISABLED)
            else:
                slider0.config(state=tk.DISABLED)
                slider1.config(state=tk.NORMAL)
            ax_img.autoscale()
            clear_plot_lines(clear_all=True)
            on_slice_change(None)
            canvas_img.draw_idle()

        def on_scroll(event):
            """
            Called on mouse scroll. Updates the slider variable and update
            the image/label.
            """
            if event.inaxes != ax_img:
                return
            active_axis = axis_var.get()
            scroll_step = int(np.sign(event.step))
            if active_axis == "axis 0" or data is None:
                current_val = slice0_var.get()
                max_val = slider0.cget('to')
                new_val_int = current_val + scroll_step
                new_val_int = max(min(new_val_int, max_val), 0)
                if new_val_int != current_val:
                    slice0_var.set(new_val_int)
                    on_slice_change(None)
            else:
                current_val = slice1_var.get()
                max_val = slider1.cget('to')
                new_val_int = current_val + scroll_step
                new_val_int = max(min(new_val_int, max_val), 0)

                if new_val_int != current_val:
                    slice1_var.set(new_val_int)
                    on_slice_change(None)

        def on_zoom_pan(ax):
            """
            Callback for when the image axes are zoomed or panned.
            This updates the line profile's x-limits to match.
            """
            if hline or vline:
                update_profile_plot()

        def plot_intensity_along_clicked_point(event):
            nonlocal clicked_point, hline, vline
            if event.inaxes != ax_img:
                return
            if event.xdata is None or event.ydata is None:
                return
            clicked_point = (int(event.ydata), int(event.xdata))
            clear_plot_lines(clear_all=False)
            if event.button == 1:
                hline = ax_img.axhline(clicked_point[0], color="red", lw=0.6)
            elif event.button == 3:
                vline = ax_img.axvline(clicked_point[1], color="red", lw=0.6)

            canvas_img.draw_idle()
            update_profile_plot()

        slider0.config(command=on_slice_change)
        min_slider.config(command=on_contrast_change)
        max_slider.config(command=on_contrast_change)
        reset_button.config(command=reset_contrast)

        if data is not None:
            slider1.config(command=on_slice_change)
            axis0_radio.config(command=on_axis_select)
            axis1_radio.config(command=on_axis_select)

        canvas_img.mpl_connect("scroll_event", on_scroll)
        canvas_img.mpl_connect("button_press_event",
                               plot_intensity_along_clicked_point)
        ax_img.callbacks.connect('xlim_changed', on_zoom_pan)
        ax_img.callbacks.connect('ylim_changed', on_zoom_pan)

        def update_aspect_ratio(event=None):
            """
            Updates the aspect ratio. If input is invalid, resets UI to 'equal'.
            """
            val = aspect_var.get().strip()
            if val.lower() in ["equal", "auto"]:
                new_aspect = val.lower()
            else:
                try:
                    new_aspect = float(val)
                except ValueError:
                    aspect_var.set("equal")
                    new_aspect = "equal"
            ax_img.set_aspect(new_aspect)
            canvas_img.draw_idle()
            update_profile_plot()

        aspect_combo.bind("<<ComboboxSelected>>", update_aspect_ratio)
        aspect_combo.bind("<Return>", update_aspect_ratio)

        def on_close():
            self.current_image = None
            self.current_table = None
            try:
                canvas_img.get_tk_widget().destroy()
                canvas_plot.get_tk_widget().destroy()
            except:
                pass
            plt.close(fig_img)
            plt.close(fig_plot)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def export_tif_window(self, file_path, file_type):
        """
        Creates the window for exporting HDF/CINE data to TIF files.
        """
        input_path = None
        hdf_key_path = None
        if file_type == "cine":
            cine_metadata = util.get_metadata_cine(file_path)
            width = cine_metadata["biWidth"]
            height = cine_metadata["biHeight"]
            depth = cine_metadata["TotalImageCount"]
            input_path = file_path
        elif file_type == "hdf":
            selected_index = self.file_list_view.curselection()
            selected_file = self.file_list_view.get(selected_index[0])
            full_path = os.path.join(self.selected_folder_path, selected_file)
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data = util.load_hdf(full_path, hdf_key_path)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
            if len(data.shape) == 2:
                data = np.expand_dims(data, 0)
            if len(data.shape) != 3:
                messagebox.showerror("Only for 3d data",
                                     f"File: {selected_file}\nOnly export "
                                     f"2d/3d data. Not {len(data.shape)}d")
                return
            (depth, height, width) = data.shape
            input_path = full_path
        else:
            messagebox.showinfo("File type", "Please select a HDF/CINE file")
            return

        file_name = os.path.basename(input_path)
        export_window = tk.Toplevel(self)
        export_window.title(f"Export TIF of file: {file_name}")
        export_window.transient(self)
        export_window.resizable(True, False)
        export_window.vars = {
            "path": tk.StringVar(master=export_window,
                                 value="No folder selected..."),
            "new_folder": tk.StringVar(master=export_window, value="tifs"),
            "axis": tk.StringVar(master=export_window, value="Axis 0"),
            "start": tk.StringVar(master=export_window, value="0"),
            "stop": tk.StringVar(master=export_window, value="-1"),
            "step": tk.StringVar(master=export_window, value="1"),
            "y_start": tk.StringVar(master=export_window, value="0"),
            "y_stop": tk.StringVar(master=export_window, value="-1"),
            "x_start": tk.StringVar(master=export_window, value="0"),
            "x_stop": tk.StringVar(master=export_window, value="-1"),
            "rescale": tk.StringVar(master=export_window, value="None"),
            "min_p": tk.StringVar(master=export_window, value="0"),
            "max_p": tk.StringVar(master=export_window, value="100"),
            "skip": tk.StringVar(master=export_window, value="10"),
            "prefix": tk.StringVar(master=export_window, value="img"),
            "status": tk.StringVar(master=export_window,
                                   value=f"Data shape (depth, height, width): "
                                         f"{depth, height, width}")
        }

        def on_close_window():
            """
            Cleanup variables explicitly to satisfy the Garbage Collector
            before destroying the Tcl widget.
            """
            export_window.vars.clear()
            export_window.destroy()
            gc.collect()

        export_window.protocol("WM_DELETE_WINDOW", on_close_window)

        def browse_destination():
            folder_selected = filedialog.askdirectory(parent=export_window)
            if folder_selected:
                folder_selected = os.path.normpath(folder_selected)
                export_window.vars["path"].set(folder_selected)

        def create_subfolder():
            output_path_val = export_window.vars["path"].get()
            new_folder_name = export_window.vars["new_folder"].get().strip()
            if output_path_val == "No folder selected..." or not os.path.isdir(
                    output_path_val):
                messagebox.showerror("Error",
                                     "Please select a base folder first.",
                                     parent=export_window)
                return
            if not new_folder_name:
                messagebox.showwarning("Warning",
                                       "Please give name for the new folder.",
                                       parent=export_window)
                return
            final_output_path = os.path.join(output_path_val, new_folder_name)
            try:
                os.makedirs(final_output_path, exist_ok=True)
                export_window.vars["path"].set(final_output_path)
                export_window.vars["new_folder"].set("")
                messagebox.showinfo("Success",
                                    f"Folder created:\n{final_output_path}",
                                    parent=export_window)
            except OSError as e:
                messagebox.showerror("Error",
                                     f"Failed to create folder.\nError: {e}")

        # Build Layout
        export_window.grid_columnconfigure(0, weight=1)
        # Destination
        dest_frame = ttk.LabelFrame(export_window, text="Destination")
        dest_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        dest_frame.grid_columnconfigure(0, weight=1)

        ttk.Entry(dest_frame, textvariable=export_window.vars["path"],
                  state="readonly").grid(row=0, column=0, sticky="ew", padx=5,
                                         pady=5)
        ttk.Button(dest_frame, text="Browse base folder",
                   command=browse_destination).grid(row=0, column=1,
                                                    sticky="ew", padx=5, pady=5)
        ttk.Entry(dest_frame,
                  textvariable=export_window.vars["new_folder"]).grid(
            row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        ttk.Button(dest_frame, text="Make subfolder",
                   command=create_subfolder).grid(row=1, column=1, sticky="ew",
                                                  padx=5, pady=(0, 5))
        # Slicing
        slice_frame = ttk.LabelFrame(export_window, text="Slicing Parameters")
        slice_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        radio_frame = ttk.Frame(slice_frame)
        radio_frame.grid(row=0, column=0, columnspan=6, sticky="w", padx=5,
                         pady=(5, 0))
        ttk.Label(radio_frame, text="Export along:").pack(side=tk.LEFT)
        axis0_radio = ttk.Radiobutton(radio_frame, text="Axis 0",
                                      variable=export_window.vars["axis"],
                                      value="Axis 0")
        axis0_radio.pack(side=tk.LEFT, padx=5)
        axis1_radio = ttk.Radiobutton(radio_frame, text="Axis 1",
                                      variable=export_window.vars["axis"],
                                      value="Axis 1")
        axis1_radio.pack(side=tk.LEFT, padx=5)
        if file_type == "cine":
            axis1_radio.config(state=tk.DISABLED)

        ttk.Label(slice_frame, text="Start Index:").grid(row=1, column=0,
                                                         sticky="w", padx=5,
                                                         pady=5)
        ttk.Entry(slice_frame, textvariable=export_window.vars["start"],
                  width=8).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(slice_frame, text="Stop Index:").grid(row=1, column=2,
                                                        sticky="w",
                                                        padx=(15, 5), pady=5)
        ttk.Entry(slice_frame, textvariable=export_window.vars["stop"],
                  width=8).grid(row=1, column=3, sticky="w", padx=5, pady=5)
        ttk.Label(slice_frame, text="Step Index:").grid(row=1, column=4,
                                                        sticky="w",
                                                        padx=(15, 5), pady=5)
        ttk.Entry(slice_frame, textvariable=export_window.vars["step"],
                  width=8).grid(row=1, column=5, sticky="w", padx=5, pady=5)
        # Cropping
        crop_frame = ttk.LabelFrame(export_window, text="Cropping Parameters")
        crop_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        ttk.Label(crop_frame, text="Height | Y-start:").grid(row=0, column=0,
                                                             sticky="w", padx=5,
                                                             pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_start"],
                  width=8).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Y-stop:").grid(row=0, column=2, sticky="w",
                                                   padx=(15, 5), pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_stop"],
                  width=8).grid(row=0, column=3, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Width  | X-start:").grid(row=1, column=0,
                                                             sticky="w", padx=5,
                                                             pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["x_start"],
                  width=8).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="X-stop:").grid(row=1, column=2, sticky="w",
                                                   padx=(15, 5), pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["x_stop"],
                  width=8).grid(row=1, column=3, sticky="w", padx=5, pady=5)
        # Rescaling
        rescale_frame = ttk.LabelFrame(export_window,
                                       text="Rescaling Parameters")
        rescale_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        bit_radio_frame = ttk.Frame(rescale_frame)
        bit_radio_frame.grid(row=0, column=0, columnspan=6, sticky="w", padx=5,
                             pady=(5, 0))
        ttk.Label(bit_radio_frame, text="Rescale to:").pack(side=tk.LEFT)
        ttk.Radiobutton(bit_radio_frame, text="None",
                        variable=export_window.vars["rescale"],
                        value="None").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(bit_radio_frame, text="8-bit",
                        variable=export_window.vars["rescale"],
                        value="8-bit").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(bit_radio_frame, text="16-bit",
                        variable=export_window.vars["rescale"],
                        value="16-bit").pack(side=tk.LEFT, padx=5)
        ttk.Label(rescale_frame, text="Min Percentile:").grid(row=1, column=0,
                                                              sticky="w",
                                                              padx=5, pady=5)
        ttk.Entry(rescale_frame, textvariable=export_window.vars["min_p"],
                  width=8).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(rescale_frame, text="Max Percentile:").grid(row=1, column=2,
                                                              sticky="w",
                                                              padx=(10, 5),
                                                              pady=5)
        ttk.Entry(rescale_frame, textvariable=export_window.vars["max_p"],
                  width=8).grid(row=1, column=3, sticky="w", padx=5, pady=5)
        ttk.Label(rescale_frame, text="Slice sampling step:").grid(row=2,
                                                                   column=0,
                                                                   sticky="w",
                                                                   padx=5,
                                                                   pady=(0, 5))
        ttk.Entry(rescale_frame, textvariable=export_window.vars["skip"],
                  width=8).grid(row=2, column=1, sticky="w", padx=5,
                                pady=(0, 5))
        # Naming
        naming_frame = ttk.LabelFrame(export_window,
                                      text="File Naming & Export")
        naming_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        naming_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(naming_frame, text="File Prefix:").grid(row=0, column=0,
                                                          sticky="w", padx=5,
                                                          pady=5)
        ttk.Entry(naming_frame, textvariable=export_window.vars["prefix"]).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5)

        def parse_int(value, default=0, allow_negative=False):
            try:
                val = int(value)
                if not allow_negative and val < 0 and val != -1:
                    return default
                return val
            except ValueError:
                return default

        def validate_export_parameters():
            params = {}
            out_path = export_window.vars["path"].get()
            if not os.path.isdir(out_path):
                messagebox.showerror("Invalid Input",
                                     "Please select a valid folder.",
                                     parent=export_window)
                return
            params['output_path'] = out_path
            params['input_path'] = input_path
            params['hdf_key'] = hdf_key_path
            prefix = export_window.vars["prefix"].get().strip()
            if not prefix:
                messagebox.showerror("Invalid Input",
                                     "Please enter a file prefix.",
                                     parent=export_window)
                return
            params['prefix'] = prefix
            params['source_shape'] = (depth, height, width)
            params['axis'] = 0 if export_window.vars[
                                      "axis"].get() == "Axis 0" else 1

            slice_dim = depth if params['axis'] == 0 else height
            params['slice_start'] = parse_int(export_window.vars["start"].get(),
                                              0)
            params['slice_stop'] = parse_int(export_window.vars["stop"].get(),
                                             slice_dim, allow_negative=True)
            params['slice_step'] = parse_int(export_window.vars["step"].get(),
                                             1)
            if params['slice_step'] == 0:
                params['slice_step'] = 1
            if params['slice_stop'] == -1 or params['slice_stop'] > slice_dim:
                params['slice_stop'] = slice_dim
            if params['slice_start'] >= params['slice_stop']:
                messagebox.showerror("Invalid Input",
                                     "Start index must be < Stop index.",
                                     parent=export_window)
                return

            y_dim = height if params['axis'] == 0 else depth
            x_dim = width
            params['y_start'] = parse_int(export_window.vars["y_start"].get(),
                                          0)
            params['y_stop'] = parse_int(export_window.vars["y_stop"].get(),
                                         y_dim, allow_negative=True)
            params['x_start'] = parse_int(export_window.vars["x_start"].get(),
                                          0)
            params['x_stop'] = parse_int(export_window.vars["x_stop"].get(),
                                         x_dim, allow_negative=True)
            if params['y_stop'] == -1:
                params['y_stop'] = y_dim
            if params['x_stop'] == -1:
                params['x_stop'] = x_dim
            if (params['y_start'] >= params['y_stop'] or params['x_start'] >=
                    params['x_stop']):
                messagebox.showerror("Invalid Input",
                                     "Invalid crop dimensions.",
                                     parent=export_window)
                return
            params['rescale'] = export_window.vars["rescale"].get()
            try:
                params['min_percent'] = float(export_window.vars["min_p"].get())
                params['max_percent'] = float(export_window.vars["max_p"].get())
            except:
                messagebox.showerror("Invalid Input",
                                     "Percentiles must be numbers.",
                                     parent=export_window)
                return
            if params['min_percent'] >= params['max_percent']:
                messagebox.showerror("Invalid Input",
                                     "Min Percentile must be < Max.",
                                     parent=export_window)
                return
            params['slice_skip'] = parse_int(export_window.vars["skip"].get(),
                                             1)
            if params['slice_skip'] <= 0:
                params['slice_skip'] = 1
            return params

        def start_export():
            """ Synchronous export on main thread. """
            params = validate_export_parameters()
            if params is None:
                return

            run_export_button.config(state=tk.DISABLED)
            export_window.vars["status"].set("Preparing export...")
            export_window.update()

            def _gui_status_callback(message):
                try:
                    export_window.vars["status"].set(message)
                    export_window.update()
                except tk.TclError:
                    pass

            try:
                result = util.export_hdf_cine_to_tif(params,
                                                     _gui_status_callback)
                if result == "Success":
                    messagebox.showinfo("Export Complete",
                                        f"Saved to:\n{params['output_path']}",
                                        parent=export_window)
            except Exception as e:
                messagebox.showerror("Export Error", f"An error occurred:\n{e}",
                                     parent=export_window)
            finally:
                try:
                    if export_window.winfo_exists():
                        run_export_button.config(state=tk.NORMAL)
                        export_window.vars["status"].set(
                            f"Data shape: {depth, height, width}")
                except tk.TclError:
                    pass

        run_export_button = ttk.Button(naming_frame, text="Export",
                                       command=start_export)
        run_export_button.grid(row=0, column=2, sticky="e", padx=(5, 10),
                               pady=5)

        status_bar = ttk.Label(export_window,
                               textvariable=export_window.vars["status"],
                               relief=tk.SUNKEN, anchor="w", padding=(1, 1))
        status_bar.grid(row=5, column=0, sticky="ew", padx=10, pady=(5, 10))

        export_window.update_idletasks()
        export_window.grab_set()
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        win_w = export_window.winfo_width()
        win_h = export_window.winfo_height()
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        export_window.geometry(f"+{x}+{y}")
