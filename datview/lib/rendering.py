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
    with importlib.resources.path("datview.assets",
                                  "datview_icon.png") as icon:
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


class DatviewToolbar(NavigationToolbar2Tk):
    # Remove the "Configure subplots" button
    toolitems = [t for t in NavigationToolbar2Tk.toolitems if
                 t[0] != "Subplots"]


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
        self.file_list_scrollbar.grid(row=1, column=2, sticky="ns",
                                      pady=(9, 9))
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
        self.hdf_key_list.grid(row=0, column=2, sticky="w", padx=5,
                               pady=(0, 5))
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
        ttip_export_tif_button = "Export 3d-array HDF/CINE dataset to " \
                                 "TIF files"
        ToolTip(self.export_tif_button, ttip_export_tif_button)
        # Status bar
        self.status_bar = tk.Text(self, height=1, state="disabled",
                                  wrap="none", bg="lightgrey")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew",
                             padx=5, pady=(0, 5))

    def define_window_geometry(self, ratio):
        """Specify size of a widget window"""
        width = int(self.screen_width * ratio)
        height = int(self.screen_height * ratio)
        max_ratio = 1.65
        if width > height:
            ratio = width / height
            if ratio > max_ratio:
                width = int(max_ratio * height)
        else:
            ratio = height / width
            if ratio > max_ratio:
                height = int(max_ratio * width)
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
        window_1d = tk.Toplevel(self)
        window_1d.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window_1d.title(title)
        try:
            dpi = window_1d.winfo_fpixels("1i") + 30
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
        ax.plot(array_1d, color="blue", linewidth=1.0)
        ax.set_aspect("auto")
        if len(help_text) > 0:
            ax.set_title(help_text)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window_1d)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = DatviewToolbar(canvas, window_1d)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window_1d.destroy()

        window_1d.protocol("WM_DELETE_WINDOW", on_close)

    def table_viewer(self, data, title="Array Table Viewer"):
        """Display 1d or 2d-data as table format"""
        table_window = tk.Toplevel(self)
        table_window.title(title)
        width, height, x_offset, y_offset = self.define_window_geometry(
            TEXT_WIN_RATIO)
        table_window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        text_widget = tk.Text(table_window, wrap="none", font=("Courier", 11))
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb = tk.Scrollbar(table_window, orient="vertical",
                           command=text_widget.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = tk.Scrollbar(table_window, orient="horizontal",
                           command=text_widget.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        def format_value(val):
            """Format the values with proper width"""
            if isinstance(val, float):
                return f"{val:.5g}" if abs(val) < 1e-5 or abs(
                    val) > 1e5 else f"{val:.5f}"
            return str(val)

        def calculate_max_width(data_t, headers):
            """Calculate the maximum width for each column"""
            col_widths = [len(header) for header in headers]
            for i in range(data_t.shape[0]):
                for j in range(data_t.shape[1]):
                    val_length = len(format_value(data_t[i, j]))
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
        table_window.grid_rowconfigure(0, weight=1)
        table_window.grid_columnconfigure(0, weight=1)

        def on_close():
            table_window.destroy()

        table_window.protocol("WM_DELETE_WINDOW", on_close)

    def show_histogram(self, mat, help_text="", title=""):
        """Display histogram of an image."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        hist_window = tk.Toplevel(self)
        hist_window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        hist_window.title(title)
        try:
            dpi = hist_window.winfo_fpixels("1i") + 30
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

        canvas = FigureCanvasTkAgg(fig, master=hist_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = DatviewToolbar(canvas, hist_window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            hist_window.destroy()

        hist_window.protocol("WM_DELETE_WINDOW", on_close)

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
        stat_window = tk.Toplevel(self)
        stat_window.title(title + " | " + help_text)
        stat_window.resizable(True, False)
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        win_w = stat_window.winfo_width()
        win_h = stat_window.winfo_height()
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        stat_window.geometry(f"+{x}+{y}")

        tree = ttk.Treeview(stat_window, columns=("Metric", "Value"),
                            show="headings")
        tree.heading("Metric", text="Metric")
        tree.heading("Value", text="Value")
        tree.column("Metric", width=150)
        tree.column("Value", width=220, anchor="e")
        tree.pack(padx=10, pady=10)
        for metric, value in stats_dict.items():
            formatted_value = f"{value:.5f}"
            tree.insert("", "end", values=(metric, formatted_value))
        stat_window.update_idletasks()

    def show_percentile_plot(self, percentiles, density, help_text="",
                             title=""):
        """
        Displays a percentile density plot.
        percentiles: The x-axis values (percentiles).
        density: The y-axis values (normalized density).
        """
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        perc_window = tk.Toplevel(self)
        perc_window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        perc_window.title(title)
        try:
            dpi = perc_window.winfo_fpixels("1i") + 30
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

        canvas = FigureCanvasTkAgg(fig, master=perc_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = DatviewToolbar(canvas, perc_window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            perc_window.destroy()

        perc_window.protocol("WM_DELETE_WINDOW", on_close)

    def show_2d_image(self, img, file_path=""):
        """
        Display an image with sliders for adjusting contrast
        """
        current_image = np.asarray(img)
        is_color = False
        if current_image.ndim == 3 and current_image.shape[2] in [3, 4]:
            is_color = True
            nmin, nmax = np.min(current_image), np.max(current_image)
            if nmax > nmin:
                current_image = (current_image - nmin) / (nmax - nmin)
            current_image = np.clip(current_image, 0.0, 1.0)
        if np.isnan(current_image).any():
            current_image = np.nan_to_num(current_image)

        settings = self.define_window_geometry(PLT_WIN_2D_RATIO)
        win_width, win_height, x_offset, y_offset = settings

        window_2d = tk.Toplevel(self)
        window_2d.title(f"Viewing: {os.path.basename(file_path)}")
        window_2d.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")
        window_2d.message_text_var = tk.StringVar(master=window_2d,
                                                  value=file_path)

        min_contrast_var = tk.DoubleVar(master=window_2d, value=0.0)
        max_contrast_var = tk.DoubleVar(master=window_2d, value=1.0)
        min_contrast_label_var = tk.StringVar(master=window_2d, value="0.0")
        max_contrast_label_var = tk.StringVar(master=window_2d, value="100.0")

        try:
            dpi = window_2d.winfo_fpixels("1i") + 30
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

        window_2d.rowconfigure(0, weight=1)
        window_2d.rowconfigure(1, weight=0)
        window_2d.rowconfigure(2, weight=0)
        window_2d.columnconfigure(0, weight=1)

        canvas_frame = ttk.Frame(window_2d)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(window_2d)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(window_2d, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame,
                                  textvariable=window_2d.message_text_var,
                                  wraplength=win_width, anchor=tk.W)
        message_label.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        fig_img, ax_img = plt.subplots(constrained_layout=True, dpi=dpi)
        ax_img.set_title(f"Height x Width : {current_image.shape[0]} "
                         f"x {current_image.shape[1]}")
        ax_img.set_xlabel("X")
        ax_img.set_ylabel("Y")
        ax_img.set_aspect("equal")

        if is_color:
            slice0 = ax_img.imshow(current_image)
        else:
            vmin_init = np.percentile(current_image, 0)
            vmax_init = np.percentile(current_image, 100)
            slice0 = ax_img.imshow(current_image, cmap="gray",
                                   vmin=vmin_init, vmax=vmax_init)

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.rowconfigure(1, weight=0)
        canvas_frame.columnconfigure(0, weight=1)
        window_2d.update_idletasks()
        canvas_img = FigureCanvasTkAgg(fig_img, master=canvas_frame)
        canvas_img.draw()
        canvas_img.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(canvas_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar_frame.columnconfigure(0, weight=1)
        toolbar = DatviewToolbar(canvas_img, toolbar_frame)
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

            aspect_var = tk.StringVar(master=window_2d, value="equal")
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
                vmin = np.percentile(current_image, p_min)
                vmax = np.percentile(current_image, p_max)
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
                if current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                stats = util.get_image_statistics(current_image)
                title = f"Statistics: {os.path.basename(file_path)}"
                self.show_statistics_table(stats, title=title)

            def open_histogram():
                if current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                title = f"Histogram: {os.path.basename(file_path)}"
                self.show_histogram(current_image, help_text="",
                                    title=title)

            def open_percentile():
                if current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                try:
                    percentiles, density = util.get_percentile_density(
                        current_image)
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
            plt.close(fig_img)
            window_2d.destroy()

        window_2d.protocol("WM_DELETE_WINDOW", on_close)


class InteractiveViewer:
    """
    A standalone class managing a single interactive viewer window.
    """

    def __init__(self, main_window, main_app, file_path, file_type,
                 hdf_key=None, list_files=None):

        self.main_win = main_window
        self.main_app = main_app
        self.file_type = file_type
        self.file_path = file_path
        self.hdf_key = hdf_key
        self.list_files = list_files
        self.hdf_file_obj = None
        self.closing = False
        if file_type == "tif":
            self.depth = len(list_files)
            if self.depth == 0:
                raise ValueError("No TIF files found.")
            initial_image = util.load_image(list_files[0], average=True)
            self.height, self.width = initial_image.shape[:2]
        elif file_type == "cine":
            metadata = util.get_metadata_cine(file_path)
            self.width = metadata["biWidth"]
            self.height = metadata["biHeight"]
            self.depth = metadata["TotalImageCount"]
            initial_image = util.extract_frame_cine(file_path, 0)
        elif file_type == "hdf":
            try:
                self.data_obj, self.hdf_file_obj = util.load_hdf(
                    file_path, hdf_key, return_file_obj=True)
            except Exception:
                raise ValueError(
                    f"Failed to load HDF dataset at key: {hdf_key}")
            if self.data_obj.ndim != 3:
                raise ValueError(f"HDF data must be 3D for interactive "
                                 f"viewer, found {self.data_obj.ndim}D.")
            self.depth, self.height, self.width = self.data_obj.shape
            initial_image = self.data_obj[0, :, :]
        else:
            raise ValueError(
                f"Unsupported file type for viewer: {file_type}")
        # Viewer State
        self.viewer_state = {
            "image": initial_image,  # The currently displayed 2D slice
            "table": None,  # The current 1D line profile data
            "index": 0,  # Current slice index
            "axis": 0,  # Current slicing axis (0=Z, 1=Y, 2=X)
            "path": self.file_path,
            "hdf_key": self.hdf_key,
            "img_width": self.width,
            "img_height": self.height,
            "img_depth": self.depth,
            "last_profile_point": None,
            "last_profile_orientation": None
        }
        # Matplotlib line references (for updates/cleanup)
        self.plot_hline = None
        self.plot_vline = None
        self.update_job = None
        self._setup_ui()
        self._setup_bindings()
        self.set_active()

    def _setup_ui(self):
        # Determine DPI and Font for plotting
        try:
            dpi = self.main_win.winfo_fpixels("1i") + 30
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update(
                {'font.family': font_family, 'font.size': FONT_SIZE})
        except:
            pass
        settings = self.main_app.define_window_geometry(PLT_WIN_3D_RATIO)
        win_width, win_height, x_offset, y_offset = settings
        self.main_win.geometry(f"{win_width}x{win_height}+"
                               f"{x_offset}+{y_offset}")
        # UI variables
        self.message_text_var = tk.StringVar(master=self.main_win,
                                             value=self.file_path)
        self.axis_var = tk.StringVar(master=self.main_win, value="axis 0")
        self.slice0_var = tk.IntVar(master=self.main_win, value=0)
        self.slice1_var = tk.IntVar(master=self.main_win, value=0)
        self.min_contrast_var = tk.DoubleVar(master=self.main_win,
                                             value=0.0)
        self.max_contrast_var = tk.DoubleVar(master=self.main_win,
                                             value=1.0)
        self.slice0_label_var = tk.StringVar(master=self.main_win,
                                             value="0")
        self.slice1_label_var = tk.StringVar(master=self.main_win,
                                             value="0")
        self.min_contrast_label_var = tk.StringVar(master=self.main_win,
                                                   value="0.0")
        self.max_contrast_label_var = tk.StringVar(master=self.main_win,
                                                   value="100.0")
        self.aspect_var = tk.StringVar(master=self.main_win, value="equal")
        # Configure window's grid
        self.main_win.rowconfigure(0, weight=1)
        self.main_win.rowconfigure(1, weight=0)
        self.main_win.rowconfigure(2, weight=0)
        self.main_win.columnconfigure(0, weight=1)
        # Create the frames
        canvas_frame = ttk.Frame(self.main_win)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(self.main_win)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(self.main_win, relief=tk.SUNKEN,
                                 borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame,
                                  textvariable=self.message_text_var,
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
        # Figure 1: Image
        self.fig_img, self.ax_img = plt.subplots(constrained_layout=True,
                                                 dpi=dpi)
        self.ax_img.set_title(f"Axis: 0. Index: 0. H x W: "
                              f"{self.height} x {self.width}")
        self.ax_img.set_xlabel("X")
        self.ax_img.set_ylabel("Y")
        self.ax_img.set_aspect("equal")
        vmin_init = np.percentile(self.viewer_state["image"], 0)
        vmax_init = np.percentile(self.viewer_state["image"], 100)
        self.slice0 = self.ax_img.imshow(self.viewer_state["image"],
                                         cmap="gray", vmin=vmin_init,
                                         vmax=vmax_init)
        self.slice0.set_extent([0, self.width, self.height, 0])
        # Figure 2: Intensity-plot
        self.fig_plot, self.ax_plot = plt.subplots(
            constrained_layout=False,
            dpi=dpi)
        self.ax_plot.set_title("Line Profile")
        self.ax_plot.set_box_aspect(
            np.clip(0.95 * self.width / self.height, 0.8, 1.0))
        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        self.main_win.update_idletasks()
        self.canvas_img = FigureCanvasTkAgg(self.fig_img,
                                            master=image_frame)
        self.canvas_img.draw()
        self.canvas_img.get_tk_widget().grid(row=0, column=0,
                                             sticky="nsew")
        plot_frame.rowconfigure(0, weight=1)
        plot_frame.columnconfigure(0, weight=1)
        self.canvas_plot = FigureCanvasTkAgg(self.fig_plot,
                                             master=plot_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().grid(row=0, column=0,
                                              sticky="nsew")
        toolbar_frame.columnconfigure(0, weight=1)
        toolbar = DatviewToolbar(self.canvas_img, toolbar_frame)
        toolbar.update()
        toolbar.grid(row=0, column=0, sticky="ew")
        # Control Frame Widgets
        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=3)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=0)
        control_frame.columnconfigure(4, weight=2)
        control_frame.columnconfigure(5, weight=0)
        control_frame.columnconfigure(6, weight=0)
        control_frame.columnconfigure(7, weight=0)
        control_frame.columnconfigure(8, weight=0)
        control_frame.rowconfigure(0, weight=0)
        control_frame.rowconfigure(1, weight=0)
        # Slice Control 1 (Axis 0)
        if self.file_type == "hdf" and self.depth > 1:
            axis0_radio = ttk.Radiobutton(control_frame, text="Axis 0",
                                          variable=self.axis_var,
                                          value="axis 0",
                                          command=self.on_axis_select)
            axis0_radio.grid(row=0, column=0, sticky='w', padx=(10, 5),
                             pady=2)
        else:
            ttk.Label(control_frame, text="Slice:").grid(row=0, column=0,
                                                         sticky='e',
                                                         padx=(10, 5),
                                                         pady=2)
        self.slider0 = ttk.Scale(control_frame, from_=0,
                                 to=self.depth - 1, orient=tk.HORIZONTAL,
                                 variable=self.slice0_var,
                                 command=self.on_slice_change)
        self.slider0.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(control_frame,
                  textvariable=self.slice0_label_var,
                  width=4).grid(row=0, column=2, sticky='w', padx=(0, 10))
        # Slice Control 2 (Axis 1, HDF only)
        if self.file_type == "hdf" and self.height > 1:
            axis1_radio = ttk.Radiobutton(control_frame, text="Axis 1",
                                          variable=self.axis_var,
                                          value="axis 1",
                                          command=self.on_axis_select)
            axis1_radio.grid(row=1, column=0, sticky='w', padx=(10, 5),
                             pady=2)
            self.slider1 = ttk.Scale(control_frame, from_=0,
                                     to=self.height - 1,
                                     orient=tk.HORIZONTAL,
                                     variable=self.slice1_var,
                                     command=self.on_slice_change,
                                     state=tk.DISABLED)
            self.slider1.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
            ttk.Label(control_frame, textvariable=self.slice1_label_var,
                      width=4).grid(row=1, column=2, sticky='w',
                                    padx=(0, 10))
        # Contrast Controls
        ttk.Label(control_frame,
                  text="Min %:").grid(row=0, column=3, sticky='w',
                                      padx=(10, 5), pady=2)
        min_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL,
                               variable=self.min_contrast_var,
                               command=self.on_contrast_change)
        min_slider.grid(row=0, column=4, sticky='ew', padx=5, pady=2)
        ttk.Label(control_frame, textvariable=self.min_contrast_label_var,
                  width=5).grid(row=0, column=5, sticky='w', padx=(0, 10))
        ttk.Label(control_frame,
                  text="Max %:").grid(row=1, column=3, sticky='w',
                                      padx=(10, 5), pady=2)
        max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL,
                               variable=self.max_contrast_var,
                               command=self.on_contrast_change)
        max_slider.grid(row=1, column=4, sticky='ew', padx=5, pady=2)
        ttk.Label(control_frame, textvariable=self.max_contrast_label_var,
                  width=5).grid(row=1, column=5, sticky='w', padx=(0, 10))
        # Buttons
        style = ttk.Style()
        style.theme_use(TTK_THEME)
        style.configure("Short.TButton", padding=[5, 1, 5, 1])

        reset_button = ttk.Button(control_frame, text="Reset",
                                  command=self.reset_contrast,
                                  style="Short.TButton")
        reset_button.grid(row=0, column=6, sticky='ew', padx=5,
                          pady=(5, 0))

        statistics_button = ttk.Button(control_frame, text="Statistics",
                                       command=self.open_statistics,
                                       style="Short.TButton")
        statistics_button.grid(row=0, column=7, sticky='ew', padx=(0, 5),
                               pady=(5, 0))

        histogram_button = ttk.Button(control_frame, text="Histogram",
                                      command=self.open_histogram,
                                      style="Short.TButton")
        histogram_button.grid(row=1, column=6, sticky='ew', padx=5, pady=5)

        percentile_button = ttk.Button(control_frame, text="Percentile",
                                       command=self.open_percentile,
                                       style="Short.TButton")
        percentile_button.grid(row=1, column=7, sticky='ew', padx=(0, 5),
                               pady=5)
        # Aspect Ratio Control
        ttk.Label(control_frame, text="Aspect").grid(row=0, column=8,
                                                     sticky='w',
                                                     padx=(0, 5),
                                                     pady=5)
        aspect_combo = ttk.Combobox(control_frame,
                                    textvariable=self.aspect_var,
                                    values=["equal", "auto"], width=5)
        aspect_combo.grid(row=1, column=8, sticky='ewns', padx=(0, 5),
                          pady=5)
        aspect_combo.bind("<<ComboboxSelected>>", self.update_aspect_ratio)
        aspect_combo.bind("<Return>", self.update_aspect_ratio)

    def _setup_bindings(self):
        # Bindings for active view, closing, and interactions
        self.main_win.bind("<FocusIn>", self.set_active)
        self.main_win.bind("<Button-1>", self.set_active)
        self.main_win.protocol("WM_DELETE_WINDOW", self.on_close)

        self.id_scroll = self.canvas_img.mpl_connect("scroll_event",
                                                     self.on_scroll)
        self.id_press = self.canvas_img.mpl_connect("button_press_event",
                                                    self.plot_intensity_along_clicked_point)
        # Connect to Matplotlib's built-in axis change callback
        self.id_xlim = self.ax_img.callbacks.connect('xlim_changed',
                                                     self.on_zoom_pan)
        self.id_ylim = self.ax_img.callbacks.connect('ylim_changed',
                                                     self.on_zoom_pan)

    def set_active(self, event=None):
        """
        Notify the main app that this viewer is the actively focused window.
        """
        self.main_app.set_active_viewer_instance(self)

    def _get_image_slice(self, index, axis):
        """Fetches the 2D image slice based on file type."""
        if self.file_type == "tif":
            return util.load_image(self.list_files[index], average=True)
        elif self.file_type == "cine":
            return util.extract_frame_cine(self.file_path, index)
        elif self.file_type == "hdf":
            if axis == 0:
                return self.data_obj[index, :, :]
            elif axis == 1:
                return self.data_obj[:, index, :]
            # This viewer only supports 3D data slice along axis 0 or 1.
            return self.data_obj[index, :, :]
        return None

    def perform_update(self, value):
        """
        The HEAVY function: Reads from disk and redraws Matplotlib.
        Only runs when the user stops dragging the slider (debounced).
        """
        if self.closing:
            return
        self.update_job = None
        index = self.viewer_state["index"]
        axis = self.viewer_state["axis"]
        # Load new image data (from disk/HDF)
        shape_changed = False
        try:
            img = self._get_image_slice(index, axis)
            if self.file_type == "tif":
                if self.viewer_state["image"].shape != img.shape:
                    shape_changed = True
        except Exception as e:
            messagebox.showerror("Data Error",
                                 f"Failed to load slice {index} along axis "
                                 f"{axis}: {e}")
            return
        # Update state and derived properties
        self.viewer_state["image"] = img
        self.viewer_state["index"] = index
        self.viewer_state["axis"] = axis
        if self.file_type == "hdf" and axis == 1:
            height = self.viewer_state["img_depth"]
            width = self.viewer_state["img_width"]
            extent = [0, width, height, 0]
            title_text = f"Axis: 1. Index: {index}. H x W: {height} x {width}"
        else:
            if self.file_type == "tif":
                height, width = img.shape[:2]
                if shape_changed:
                    self.viewer_state["img_height"] = height
                    self.viewer_state["img_width"] = width
                extent = [0, width, height, 0]
                title_text = f"Axis: 0. Index: {index}. " \
                             f"H x W: {height} x {width}"
            else:
                height = self.viewer_state["img_height"]
                width = self.viewer_state["img_width"]
                extent = [0, width, height, 0]
                title_text = f"Axis: 0. Index: {index}. H x W: " \
                             f"{height} x {width}"
        if np.isnan(img).any():
            img = np.nan_to_num(img)
        # Apply contrast and redraw image
        if self.file_type == "tif" and shape_changed:
            self.min_contrast_var.set(0.0)
            self.max_contrast_var.set(1.0)
            self.min_contrast_label_var.set("0.0")
            self.max_contrast_label_var.set("100.0")
            vmin = np.percentile(img, 0)
            vmax = np.percentile(img, 100)
        else:
            p_min = self.min_contrast_var.get() * 100.0
            p_max = self.max_contrast_var.get() * 100.0
            vmin = np.percentile(img, p_min)
            vmax = np.percentile(img, p_max)
            if vmin == vmax:
                vmin -= 0.5
                vmax += 0.5
        self.slice0.set_data(img)
        self.slice0.set_clim(vmin, vmax)
        self.slice0.set_extent(extent)
        # Update labels/titles
        if self.file_type == "tif":
            if shape_changed:
                self.clear_plot_lines(clear_profile_data=True)
            self.ax_img.set_title(title_text)
            self.ax_img.set_aspect(self.aspect_var.get())
            self.message_text_var.set(f"{self.file_path} | Slice: "
                                      f"{index}, Axis: {axis}")
        else:
            self.ax_img.set_title(title_text)
            self.ax_img.set_aspect(self.aspect_var.get())
            self.message_text_var.set(f"{self.file_path} | Slice: "
                                      f"{index}, Axis: {axis}")
        self.canvas_img.draw_idle()
        # Update plot lines
        self.clear_plot_lines(clear_profile_data=False)
        if self.viewer_state["last_profile_point"] is not None:
            y, x = self.viewer_state["last_profile_point"]
            if 0 <= y < height and 0 <= x < width:
                self.update_profile_plot(
                    redraw_image_line=True,
                    clicked_point=self.viewer_state["last_profile_point"],
                    orientation=self.viewer_state["last_profile_orientation"])
            else:
                self.clear_plot_lines(clear_profile_data=True)
        else:
            self.canvas_img.draw_idle()

    def clear_plot_lines(self, clear_profile_data=False):
        """Clears plot lines and/or profile data."""
        # Remove line drawing from image plot
        if self.plot_hline:
            self.plot_hline.set_visible(False)
            self.plot_hline.remove()
            self.plot_hline = None
        if self.plot_vline:
            self.plot_vline.set_visible(False)
            self.plot_vline.remove()
            self.plot_vline = None
        if clear_profile_data:
            # Also reset the profile data/point itself
            self.viewer_state["table"] = None
            self.viewer_state["last_profile_point"] = None
            self.viewer_state["last_profile_orientation"] = None
            self.ax_plot.clear()
            self.ax_plot.set_title("Line Profile")
            self.ax_plot.set_xlabel("")
            self.ax_plot.autoscale()
            self.canvas_plot.draw_idle()
        self.canvas_img.draw_idle()

    def update_profile_plot(self, redraw_image_line=False,
                            clicked_point=None,
                            orientation=None):
        """
        Updates the line profile plot based on a new click, or redraws based
        on previously stored state if called from slice/zoom update.

        clicked_point is (y, x)
        """
        img = self.viewer_state["image"]
        if img is None:
            self.clear_plot_lines(clear_profile_data=True)
            return
        y_profile, x_profile = None, None
        if clicked_point:
            y_profile, x_profile = clicked_point
            if orientation == 'horizontal':
                self.viewer_state["table"] = img[y_profile, :]
                self.viewer_state[
                    "last_profile_orientation"] = 'horizontal'
                self.viewer_state["last_profile_point"] = clicked_point
            elif orientation == 'vertical':
                self.viewer_state["table"] = img[:, x_profile]
                self.viewer_state["last_profile_orientation"] = 'vertical'
                self.viewer_state["last_profile_point"] = clicked_point
            else:
                self.viewer_state["table"] = None
                return
        elif self.viewer_state["table"] is not None:
            orientation = self.viewer_state["last_profile_orientation"]
            y_profile, x_profile = self.viewer_state["last_profile_point"]
        else:
            self.clear_plot_lines(clear_profile_data=True)
            return
        if redraw_image_line:
            self.clear_plot_lines(clear_profile_data=False)
            if orientation == 'horizontal':
                self.plot_hline = self.ax_img.axhline(y_profile,
                                                      color="red",
                                                      lw=0.6)
            elif orientation == 'vertical':
                self.plot_vline = self.ax_img.axvline(x_profile,
                                                      color="red",
                                                      lw=0.6)
            self.canvas_img.draw_idle()
        # Redraw profile plot (Zoom-linked logic)
        profile = self.viewer_state["table"]
        self.ax_plot.clear()
        self.ax_plot.plot(profile, color="blue", linewidth=0.8)
        # Set title with the current coordinate
        if orientation == 'horizontal':
            self.ax_plot.set_title(f"Intensity at row: {y_profile}")
            self.ax_plot.set_xlabel("X (Pixel Index)")
        else:
            self.ax_plot.set_title(f"Intensity at column: {x_profile}")
            self.ax_plot.set_xlabel("Y (Pixel Index)")
        # Handle Zoom Logic (Restored from previous version)
        x_min_img, x_max_img = self.ax_img.get_xlim()
        y_min_img, y_max_img = self.ax_img.get_ylim()
        if orientation == 'horizontal':
            profile_x_min, profile_x_max = x_min_img, x_max_img
        else:
            profile_x_min = min(y_min_img, y_max_img)
            profile_x_max = max(y_min_img, y_max_img)
        self.ax_plot.set_xlim(profile_x_min, profile_x_max)
        # Automatic Y-scaling based on the visible zoom window
        px_min, px_max = self.ax_plot.get_xlim()
        idx_start = int(max(0, np.floor(min(px_min, px_max))))
        idx_end = int(min(len(profile), np.ceil(max(px_min, px_max))))
        if idx_end > idx_start:
            local_data = profile[idx_start:idx_end]
            if local_data.size > 0:
                local_min = np.nanmin(local_data)
                local_max = np.nanmax(local_data)
                yrange = local_max - local_min
                pad = yrange * 0.05 if yrange != 0 else 1.0
                self.ax_plot.set_ylim(local_min - pad, local_max + pad)
        self.canvas_plot.draw_idle()

    def on_slice_change(self, value):
        """
        Lightweight debouncer for slice slider changes.
        """
        active_axis = self.axis_var.get()
        val_int = int(float(value))
        if active_axis == "axis 0" or self.file_type != "hdf":
            self.viewer_state["index"] = val_int
            self.viewer_state["axis"] = 0
            self.slice0_label_var.set(f"{val_int}")
        elif active_axis == "axis 1":
            self.viewer_state["index"] = val_int
            self.viewer_state["axis"] = 1
            self.slice1_label_var.set(f"{val_int}")
        if self.update_job:
            self.main_win.after_cancel(self.update_job)
        # Debounce the heavy update operation
        self.update_job = self.main_win.after(10,
                                              lambda: self.perform_update(
                                                  value))

    def on_contrast_change(self, value):
        """Called when contrast sliders move."""
        if self.closing or not self.main_win.winfo_exists():
            return
        img = self.viewer_state["image"]
        if img is None:
            return
        min_val = self.min_contrast_var.get()
        max_val = self.max_contrast_var.get()
        p_min = min_val * 100.0
        p_max = max_val * 100.0
        # Enforce min < max
        if p_min >= p_max:
            if p_max > 0.0:
                p_min = p_max - 0.1
                self.min_contrast_var.set(p_min / 100.0)
            else:
                p_min, p_max = 0.0, 0.1
                self.min_contrast_var.set(0.0)
                self.max_contrast_var.set(0.001)
        self.min_contrast_label_var.set(f"{p_min:.1f}")
        self.max_contrast_label_var.set(f"{p_max:.1f}")
        vmin = np.percentile(img, p_min)
        vmax = np.percentile(img, p_max)
        if vmin == vmax:  # Handle flat data
            vmin -= 0.5
            vmax += 0.5
        self.slice0.set_clim(vmin, vmax)
        self.canvas_img.draw_idle()

    def reset_contrast(self, event=None):
        """Resets the contrast sliders and updates the image."""
        self.min_contrast_var.set(0.0)
        self.max_contrast_var.set(1.0)
        self.on_contrast_change(None)

    def on_axis_select(self):
        """Handle Axis 0 / Axis 1 radio button selection (HDF only)."""
        if self.file_type != "hdf":
            return
        if self.axis_var.get() == "axis 0":
            self.slider0.config(state=tk.NORMAL)
            self.slider1.config(state=tk.DISABLED)
            self.slider0.config(to=self.viewer_state["img_depth"] - 1)
        else:
            self.slider0.config(state=tk.DISABLED)
            self.slider1.config(state=tk.NORMAL)
            self.slider1.config(to=self.viewer_state["img_height"] - 1)
        current_slider = \
            self.slider0 if self.axis_var.get() == "axis 0" else self.slider1
        current_slider.set(0)
        self.on_slice_change(0)
        self.ax_img.autoscale()
        self.clear_plot_lines(clear_profile_data=True)
        self.canvas_img.draw_idle()

    def on_scroll(self, event):
        """Scroll to change slice index."""
        if event.inaxes != self.ax_img:
            return
        active_axis = self.axis_var.get()
        scroll_step = -int(np.sign(event.step))
        if active_axis == "axis 0" or self.file_type != "hdf":
            slider = self.slider0
            var = self.slice0_var
        else:
            slider = self.slider1
            var = self.slice1_var
        current_val = var.get()
        max_val = slider.cget('to')
        new_val_int = current_val + scroll_step
        new_val_int = int(max(min(new_val_int, max_val), 0))
        if new_val_int != current_val:
            var.set(new_val_int)
            self.on_slice_change(new_val_int)

    def on_zoom_pan(self, ax):
        """Callback for when the image axes are zoomed or panned."""
        if self.viewer_state["table"] is not None:
            self.update_profile_plot(redraw_image_line=False)

    def plot_intensity_along_clicked_point(self, event):
        """Generate a line profile based on mouse click."""
        self.set_active()  # Make sure this viewer is active
        if event.inaxes != self.ax_img:
            return
        if event.xdata is None or event.ydata is None:
            return
        img_height, img_width = self.viewer_state['image'].shape
        x_click, y_click = int(event.xdata), int(event.ydata)
        if not (0 <= y_click < img_height and 0 <= x_click < img_width):
            return
        y_profile, x_profile = y_click, x_click
        if event.button == 1:  # Left click: Horizontal
            orientation = 'horizontal'
        elif event.button == 3:  # Right click: Vertical
            orientation = 'vertical'
        else:
            return
        clicked_point = (y_profile, x_profile)
        self.update_profile_plot(redraw_image_line=True,
                                 clicked_point=clicked_point,
                                 orientation=orientation)

    def update_aspect_ratio(self, event=None):
        """Updates the aspect ratio."""
        if self.closing or not self.main_win.winfo_exists():
            return
        val = self.aspect_var.get().strip()
        if val.lower() in ["equal", "auto"]:
            new_aspect = val.lower()
        else:
            try:
                new_aspect = float(val)
            except ValueError:
                self.aspect_var.set("equal")
                new_aspect = "equal"
        self.ax_img.set_aspect(new_aspect)
        self.canvas_img.draw_idle()
        self.update_profile_plot(redraw_image_line=False)

    def open_statistics(self):
        """Opens statistics window for the current image slice."""
        img = self.viewer_state["image"]
        if img is None:
            messagebox.showwarning("No Image", "No image data to analyze.")
            return
        stats = util.get_image_statistics(img)
        title = f"Statistics: {os.path.basename(self.file_path)}"
        help_text = f" Slice: {self.viewer_state['index']}. " \
                    f"Axis {self.viewer_state['axis']}"
        self.main_app.show_statistics_table(stats, title=title,
                                            help_text=help_text)

    def open_histogram(self):
        """Opens histogram window for the current image slice."""
        img = self.viewer_state["image"]
        if img is None:
            messagebox.showwarning("No Image", "No image data to analyze.")
            return
        title = f"{os.path.basename(self.file_path)}"
        help_text = f" slice: {self.viewer_state['index']} axis: " \
                    f"{self.viewer_state['axis']}."
        self.main_app.show_histogram(img, help_text=help_text, title=title)

    def open_percentile(self):
        """Opens percentile plot window for the current image slice."""
        img = self.viewer_state["image"]
        if img is None:
            messagebox.showwarning("No Image", "No image data to analyze.")
            return
        try:
            percentiles, density = util.get_percentile_density(img)
        except ValueError as e:
            messagebox.showerror("Error",
                                 f"Could not calculate percentiles:\n{e}")
            return
        title = f"Percentile Plot: {os.path.basename(self.file_path)}"
        help_text = f" slice: {self.viewer_state['index']} axis: " \
                    f"{self.viewer_state['axis']}"
        self.main_app.show_percentile_plot(percentiles, density,
                                           help_text=help_text,
                                           title=title)

    def on_close(self):
        """Cleanup and notify main app upon window close"""
        self.closing = True
        if self.update_job:
            try:
                self.main_win.after_cancel(self.update_job)
            except tk.TclError:
                pass
            self.update_job = None
        try:
            self.canvas_img.mpl_disconnect(self.id_scroll)
            self.canvas_img.mpl_disconnect(self.id_press)
            self.ax_img.callbacks.disconnect(self.id_xlim)
            self.ax_img.callbacks.disconnect(self.id_ylim)
        except Exception:
            pass
        for var_name in (
                "message_text_var",
                "axis_var",
                "slice0_var",
                "slice1_var",
                "min_contrast_var",
                "max_contrast_var",
                "slice0_label_var",
                "slice1_label_var",
                "min_contrast_label_var",
                "max_contrast_label_var",
                "aspect_var",
        ):
            var = getattr(self, var_name, None)
            if var is not None:
                try:
                    var.set("")
                except tk.TclError:
                    pass
                setattr(self, var_name, None)
        if self.hdf_file_obj:
            try:
                self.hdf_file_obj.close()
            except Exception:
                pass
            self.hdf_file_obj = None
        self.main_app.notify_viewer_closed(self)
        try:
            plt.close(self.fig_img)
            plt.close(self.fig_plot)
        except Exception:
            pass
        self.viewer_state.clear()
        try:
            self.main_win.destroy()
        except tk.TclError:
            pass
