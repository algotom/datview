import os
import json
import logging
from pathlib import Path
import importlib.resources
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
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
PLT_WIN_1D_RATIO = 0.7
FIT_RATIO = 0.8
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

    def schedule_tooltip(self, event):
        self._after_id = self.widget.after(self.delay, self.show_tooltip, event)

    def show_tooltip(self, event):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() - 20
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=self.text, background="yellow",
                          relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
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
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
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

    def table_viewer(self, data):
        """Display 1d or 2d-data as table format"""
        window = tk.Toplevel(self)
        window.title("Array Table Viewer")
        width, height, x_offset, y_offset = self.define_window_geometry(
            TEXT_WIN_RATIO)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        text_widget = tk.Text(window, wrap="none", font=("Courier", 11))
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb = tk.Scrollbar(window, orient="vertical",
                           command=text_widget.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = tk.Scrollbar(window, orient="horizontal",
                           command=text_widget.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        def format_value(val):
            """Format the values with proper width"""
            if isinstance(val, float):
                # Limit floats to 5 decimal places or use scientific notation
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
            return " ".join([f"{val:>{width}}" for val, width in
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
            if nmax - nmin > 0:
                self.current_image = (self.current_image - nmin) / (nmax - nmin)
            self.current_image = np.clip(self.current_image, 0.0, 1.0)
        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)

        settings = self.define_window_geometry(PLT_WIN_2D_RATIO)
        win_width, win_height, x_offset, y_offset = settings

        min_contrast_var = tk.DoubleVar(value=0.0)
        max_contrast_var = tk.DoubleVar(value=1.0)
        min_contrast_label_var = tk.StringVar(value="0")
        max_contrast_label_var = tk.StringVar(value="100")

        top_window = tk.Toplevel(self)
        top_window.title(f"Viewing: {os.path.basename(file_path)}")
        top_window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")
        top_window.message_text_var = tk.StringVar(value=file_path)

        try:
            dpi = top_window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update({'font.family': font_family,
                                 'font.size': FONT_SIZE})
        except:
            pass

        top_window.rowconfigure(0, weight=1)
        top_window.rowconfigure(1, weight=0)
        top_window.rowconfigure(2, weight=0)
        top_window.columnconfigure(0, weight=1)

        canvas_frame = ttk.Frame(top_window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(top_window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(top_window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame,
                                  textvariable=top_window.message_text_var,
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
        top_window.update_idletasks()
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
            control_frame.columnconfigure(4, weight=1)
            control_frame.columnconfigure(5, weight=0)
            control_frame.columnconfigure(6, weight=0)
            control_frame.rowconfigure(0, weight=0)

            ttk.Label(control_frame,
                      text="Min %:").grid(row=0, column=0, sticky='e',
                                          padx=(10, 5), pady=2)
            min_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                                   orient=tk.HORIZONTAL,
                                   variable=min_contrast_var)
            min_slider.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
            min_label = ttk.Label(control_frame,
                                  textvariable=min_contrast_label_var, width=4)
            min_label.grid(row=0, column=2, sticky='w', padx=(0, 10))

            ttk.Label(control_frame,
                      text="Max %:").grid(row=0, column=3, sticky='e',
                                          padx=(10, 5), pady=2)
            max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                                   orient=tk.HORIZONTAL,
                                   variable=max_contrast_var)
            max_slider.grid(row=0, column=4, sticky='ew', padx=5, pady=2)
            max_label = ttk.Label(control_frame,
                                  textvariable=max_contrast_label_var, width=4)
            max_label.grid(row=0, column=5, sticky='w', padx=(0, 10))

            reset_button = ttk.Button(control_frame, text="Reset")
            reset_button.grid(row=0, column=6, sticky='w', padx=10, pady=10)

        if not is_color:
            def on_contrast_change(value):
                if self.current_image is None:
                    return
                min_val = min_contrast_var.get()
                max_val = max_contrast_var.get()
                p_min = min_val * 100.0
                p_max = max_val * 100.0
                min_contrast_label_var.set(f"{int(p_min)}")
                max_contrast_label_var.set(f"{int(p_max)}")
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

        if not is_color:
            min_slider.config(command=on_contrast_change)
            max_slider.config(command=on_contrast_change)
            reset_button.config(command=reset_contrast)

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

        if file_type == "tif":
            list_files = util.find_file(file_path + "/*tif*")
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
                self.show_1d_data(self.current_table, help_text=hdf_key_path)
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

        message_text_var = tk.StringVar(value=current_path)
        axis_var = tk.StringVar(value="axis 0")
        slice0_var = tk.IntVar(value=0)
        slice1_var = tk.IntVar(value=0)
        min_contrast_var = tk.DoubleVar(value=0.0)
        max_contrast_var = tk.DoubleVar(value=1.0)

        slice0_label_var = tk.StringVar(value="0")
        slice1_label_var = tk.StringVar(value="0")
        min_contrast_label_var = tk.StringVar(value="0")
        max_contrast_label_var = tk.StringVar(value="100")

        top_window = tk.Toplevel(self)
        top_window.title(f"Viewing: {os.path.basename(current_path)}")
        top_window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")

        try:
            dpi = top_window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update(
                {'font.family': font_family, 'font.size': FONT_SIZE})
        except:
            pass

        # --- Configure top_window's grid ---
        top_window.rowconfigure(0, weight=1)
        top_window.rowconfigure(1, weight=0)
        top_window.rowconfigure(2, weight=0)
        top_window.columnconfigure(0, weight=1)

        # --- Create and grid the frames ---
        canvas_frame = ttk.Frame(top_window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")

        control_frame = ttk.Frame(top_window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        status_frame = ttk.Frame(top_window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)

        message_label = ttk.Label(status_frame, textvariable=message_text_var,
                                  wraplength=win_width - 100, anchor=tk.W)
        message_label.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        # Setup Matplotlib Figures
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.rowconfigure(1, weight=0)
        canvas_frame.columnconfigure(0, weight=3)
        canvas_frame.columnconfigure(1, weight=2)

        image_frame = ttk.Frame(canvas_frame)
        image_frame.grid(row=0, column=0, sticky="nsew")

        plot_frame = ttk.Frame(canvas_frame)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        toolbar_frame = ttk.Frame(canvas_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew", columnspan=2)

        # Figure 1: To show image
        fig_img, ax_img = plt.subplots(constrained_layout=True, dpi=dpi)
        ax_img.set_title(f"Axis: {0}. Index: {0}")
        ax_img.set_xlabel("X")
        ax_img.set_ylabel("Y")
        ax_img.set_aspect("equal")

        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)
        vmin_init = np.percentile(self.current_image, 0)
        vmax_init = np.percentile(self.current_image, 100)

        slice0 = ax_img.imshow(self.current_image, cmap="gray", vmin=vmin_init,
                               vmax=vmax_init)

        # Figure 2: To show intensity-plot
        fig_plot, ax_plot = plt.subplots(constrained_layout=False, dpi=dpi)
        ax_plot.set_title("Line Profile")
        ax_plot.set_box_aspect(np.clip(0.95 * width / height, 0.8, 1.1))

        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        top_window.update_idletasks()
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
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=0)
        control_frame.columnconfigure(4, weight=1)
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
                              textvariable=min_contrast_label_var, width=4)
        min_label.grid(row=0, column=5, sticky='w', padx=(0, 10))

        reset_button = ttk.Button(control_frame, text="Reset")
        reset_button.grid(row=0, column=6, sticky='w', padx=(10, 10),
                          rowspan=2, ipady=5)

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

        ttk.Label(control_frame, text="Max %:").grid(row=1, column=3,
                                                     sticky='w', padx=(10, 5),
                                                     pady=2)
        max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL, variable=max_contrast_var)
        max_slider.grid(row=1, column=4, sticky='ew', padx=5, pady=2)
        max_label = ttk.Label(control_frame,
                              textvariable=max_contrast_label_var, width=4)
        max_label.grid(row=1, column=5, sticky='w', padx=(0, 10))

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
            canvas_plot.draw_idle()

        def on_slice_change(value):
            """Called when a slice slider moves. Loads new data."""
            nonlocal img
            active_axis = axis_var.get()
            p_min = min_contrast_var.get() * 100.0
            p_max = max_contrast_var.get() * 100.0
            if active_axis == "axis 0" or data is None:
                index = slice0_var.get()
                slice0_label_var.set(f"{index}")
                if file_type == "tif":
                    img = util.load_image(list_files[index])
                    message_text_var.set(list_files[index])
                elif file_type == "cine":
                    img = util.extract_frame_cine(file_path, index)
                    message_text_var.set(file_path)
                else:
                    img = data[index, :, :]
                    message_text_var.set(current_path)
                ax_img.set_title(f"Axis: 0. Index: {index}. "
                                 f"H x W: {height} x {width}")
                slice0.set_extent([0, width, height, 0])
                ax_img.set_aspect("equal")
            else:  # axis 1 (HDF5 only)
                index = slice1_var.get()
                slice1_label_var.set(f"{index}")
                img = data[:, index, :]
                message_text_var.set(current_path)
                ax_img.set_title(f"Axis: 1. Index: {index}. "
                                 f"H x W: {depth} x {width}")
                slice0.set_extent([0, width, depth, 0])
                ax_img.set_aspect("equal")
            self.current_image = img
            if np.isnan(self.current_image).any():
                self.current_image = np.nan_to_num(self.current_image)

            vmin = np.percentile(self.current_image, p_min)
            vmax = np.percentile(self.current_image, p_max)
            if vmin == vmax:  # Handle flat data
                vmin = vmin - 0.5
                vmax = vmax + 0.5
            slice0.set_data(self.current_image)
            slice0.set_clim(vmin, vmax)
            canvas_img.draw_idle()
            update_profile_plot()

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
            min_contrast_label_var.set(f"{int(p_min)}")
            max_contrast_label_var.set(f"{int(p_max)}")

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
