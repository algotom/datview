import os
import logging
import json
import importlib.resources
from pathlib import Path
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
matplotlib.use("TkAgg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# ==============================================================================
#                          GUI Rendering
# ==============================================================================


FONT_SIZE = 10
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

    def show_2d_image(self, img, file_path=""):
        """Display an image with sliders for adjusting contrast"""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_2D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        fig, ax = plt.subplots(figsize=(FIT_RATIO * width / self.dpi,
                                        FIT_RATIO * height / self.dpi))
        if img.dtype != np.uint8:
            num = (img.max() - img.min())
            if num != 0.0:
                img = 255.0 * (img - img.min()) / num
            img = img.astype(np.uint8)
        img_plot = ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"Height x Width : {img.shape[0]} x {img.shape[1]}")
        fig.subplots_adjust(left=0.05, right=0.95, bottom=0.15, top=0.96)

        slider_ax_min = fig.add_axes([0.2, 0.07, 0.6, 0.03])
        min_slider = Slider(slider_ax_min, "Min", 0, 255, valinit=0, valstep=1)

        slider_ax_max = fig.add_axes([0.2, 0.03, 0.6, 0.03])
        max_slider = Slider(slider_ax_max, "Max", 0, 255, valinit=255,
                            valstep=1)
        fig.text(0.2, 0.015, file_path, horizontalalignment="left",
                 verticalalignment="center", transform=fig.transFigure,
                 fontsize=PLT_TEXT_FONTSIZE)

        def update_contrast(val):
            min_val = min_slider.val
            max_val = max_slider.val
            if min_val >= max_val:
                if max_val > 0:
                    min_val = max_val - 1
                    min_slider.set_val(min_val)
                else:
                    max_val = 1
                    min_val = 0
                    max_slider.set_val(max_val)
            img_plot.set_clim(vmin=min_val, vmax=max_val)
            fig.canvas.draw_idle()

        min_slider.on_changed(update_contrast)
        max_slider.on_changed(update_contrast)

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_1d_data(self, array_1d, help_text=None):
        """Display a graph of 1d data."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        win = tk.Toplevel(self)
        win.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        fig, ax = plt.subplots(figsize=((width / self.dpi) * FIT_RATIO,
                                        (height / self.dpi) * FIT_RATIO))
        ax.plot(array_1d, color="blue", linewidth=1.0)
        ax.set_aspect("auto")
        if help_text:
            ax.set_title(help_text)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, win)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    def interactive_viewer(self, file_path, file_type):
        """
        Display an image of a 3D array from a hdf file, cine file, or a folder
        of tif files. Includes sliders to adjust contrast, view different
        images, and a line-profile plot based on the mouse-clicked position.
        """
        clicked_point, hline, vline = None, None, None
        depth, height, width = None, None, None
        img, img_norm = None, None

        def normalize_image(img, min_val=0, max_val=255):
            nmin, nmax = np.min(img), np.max(img)
            if nmax != nmin:
                img_norm = np.uint8(255.0 * (img - nmin) / (nmax - nmin))
                img_norm = np.clip(img_norm, min_val, max_val)
            else:
                img_norm = np.zeros(img.shape)
            return img_norm

        if file_type == "tif" or file_type == "cine":
            if file_type == "tif":
                list_files = util.find_file(file_path + "/*tif*")
                img = util.load_image(list_files[0])
                (height, width) = img.shape
                depth = len(list_files)
                current_path = list_files[0]
            else:
                cine_metadata = util.get_metadata_cine(file_path)
                width = cine_metadata["biWidth"]
                height = cine_metadata["biHeight"]
                depth = cine_metadata["TotalImageCount"]
                img = util.extract_frame_cine(file_path, 0)
                current_path = file_path

            settings = self.define_window_geometry(PLT_WIN_3D_RATIO)
            win_width, win_height, x_offset, y_offset = settings
            fig, ax = plt.subplots(1, 2,
                                   figsize=(FIT_RATIO * win_width / self.dpi,
                                            FIT_RATIO * win_height / self.dpi),
                                   gridspec_kw={"width_ratios": [1.35, 1],
                                                "wspace": 0.15})
            fig.canvas.manager.window.wm_geometry(
                f"{win_width}x{win_height}+{x_offset}+{y_offset}")
            plt.subplots_adjust(bottom=0.15, left=0.05, right=0.95, top=0.96)
            ax[0].set_title(
                f"Axis: {0}. Index: {0}. Height x Width: {height} x {width}")
            ax[0].set_xlabel("X")
            ax[0].set_ylabel("Y")
            ax[0].set_aspect("equal")
            ax[1].set_aspect("auto")
            img_norm = normalize_image(img)
            slice0 = ax[0].imshow(img_norm, cmap="gray")
            slider_ax0 = fig.add_axes([0.12, 0.06, 0.65, 0.03])
            min_slider_ax = fig.add_axes([0.12, 0.03, 0.30, 0.03])
            max_slider_ax = fig.add_axes([0.47, 0.03, 0.30, 0.03])
            slider0 = Slider(slider_ax0, "Axis 0", 0, depth - 1, valinit=0,
                             valstep=1)
            slider1 = None
            message_text = plt.text(0.12, 0.015, current_path,
                                    horizontalalignment="left",
                                    verticalalignment="center",
                                    transform=fig.transFigure,
                                    fontsize=PLT_TEXT_FONTSIZE)
        else:
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
            if len(data.shape) > 3 or len(data.shape) == 0:
                messagebox.showerror("Can't show data",
                                     f"File: {selected_file}\nOnly can "
                                     f"show 1d, 2d, or 3d data. "
                                     f"Not {len(data.shape)}d")
                return
            hdf_full_path = full_path
            if 1 in data.shape:
                data = np.squeeze(data)
            if len(data.shape) == 1:
                self.current_table = data[:]
                self.show_1d_data(self.current_table, help_text=hdf_key_path)
                return
            elif len(data.shape) == 2:
                self.current_table = data[:]
                self.show_2d_image(self.current_table, hdf_full_path)
                return
            else:
                (depth, height, width) = data.shape
                settings = self.define_window_geometry(PLT_WIN_3D_RATIO)
                win_width, win_height, x_offset, y_offset = settings
                fig_width = FIT_RATIO * win_width / self.dpi
                fig_height = FIT_RATIO * win_height / self.dpi
                fig, ax = plt.subplots(1, 2,
                                       figsize=(fig_width, fig_height),
                                       gridspec_kw={"width_ratios": [1.35, 1],
                                                    "wspace": 0.15})
                plt.subplots_adjust(bottom=0.18, left=0.05, right=0.95,
                                    top=0.96)
                ax[0].set_title(f"Axis: {0}. Index: {0}. Height x Width:"
                                f" {height} x {width}")
                ax[0].set_xlabel("X")
                ax[0].set_ylabel("Y")
                ax[0].set_aspect("equal")
                ax[-1].set_aspect("auto")
                img = data[0, :, :]
                img_norm = normalize_image(img)
                slice0 = ax[0].imshow(img_norm, cmap="gray")
                slider_ax0 = fig.add_axes([0.12, 0.09, 0.65, 0.03])
                slider_ax1 = fig.add_axes([0.12, 0.06, 0.65, 0.03])
                min_slider_ax = fig.add_axes([0.12, 0.03, 0.30, 0.03])
                max_slider_ax = fig.add_axes([0.47, 0.03, 0.30, 0.03])
                radio_button = fig.add_axes([0.85, 0.06, 0.1, 0.06])
                slider0 = Slider(slider_ax0, "Axis 0", 0, depth - 1, valinit=0,
                                 valstep=1)
                slider1 = Slider(slider_ax1, "Axis 1", 0, height - 1, valinit=0,
                                 valstep=1)
                axis_selector = RadioButtons(radio_button, ["axis 0", "axis 1"],
                                             active=0)
                message_text = plt.text(0.12, 0.015, hdf_full_path,
                                        horizontalalignment="left",
                                        verticalalignment="center",
                                        transform=fig.transFigure,
                                        fontsize=PLT_TEXT_FONTSIZE)
                slider1.set_active(False)
                self.current_image = img

        def update_slider():
            nonlocal depth, height, width
            if slider1 is not None:
                if axis_selector.value_selected == "axis 0":
                    slider0.set_active(True)
                    slider1.reset()
                    slider1.set_active(False)
                    ax[0].set_title(f"Axis: {0}. Index: {0}. "
                                    f"Height x Width: {height} x {width}")
                else:
                    slider0.reset()
                    slider0.set_active(False)
                    slider1.set_active(True)
                    ax[0].set_title(f"Axis: {1}. Index: {0}. "
                                    f"Height x Width: {depth} x {width}")

        min_slider = Slider(min_slider_ax, "Min", 0, 255, valinit=0, valstep=1)
        max_slider = Slider(max_slider_ax, "Max", 0, 255, valinit=255,
                            valstep=1)

        def update_contrast(event):
            nonlocal img, img_norm
            if slider1 is not None:
                update_slider()
            min_val = int(min_slider.val)
            max_val = int(max_slider.val)
            if min_val >= max_val:
                if max_val > 0:
                    min_val = max_val - 1
                    min_slider.set_val(min_val)
                else:
                    min_val, max_val = 0, 1
                    max_slider.set_val(max_val)
                    min_slider.set_val(min_val)
            if file_type == "tif":
                index = int(slider0.val)
                img = util.load_image(list_files[index])
            elif file_type == "cine":
                index = int(slider0.val)
                img = util.extract_frame_cine(file_path, index)
            else:
                if axis_selector.value_selected == "axis 0":
                    index = int(slider0.val)
                    img = data[index, :, :]
                    slice0.set_extent([0, width, height, 0])
                else:
                    index = int(slider1.val)
                    img = data[:, index, :]
                    slice0.set_extent([0, width, depth, 0])
            img_norm = normalize_image(img, min_val=min_val, max_val=max_val)
            slice0.set_clim(vmin=min_val, vmax=max_val)
            slice0.set_data(img_norm)
            fig.canvas.draw_idle()
            self.current_image = img

        def update_axis(val, axis=0):
            nonlocal depth, height, width, img, img_norm
            nonlocal clicked_point, hline, vline
            index = int(slider0.val if axis == 0 else slider1.val)
            min_val = int(min_slider.val)
            max_val = int(max_slider.val)
            if axis == 0:
                ax[0].set_title(f"Axis: {axis}. Index: {index}. "
                                f"Height x Width: {height} x {width}")
            else:
                ax[0].set_title(f"Axis: {axis}. Index: {index}. "
                                f"Height x Width: {depth} x {width}")
            if file_type == "tif":
                img = util.load_image(list_files[index])
                img_norm = normalize_image(img, min_val, max_val)
                message_text.set_text(list_files[index])
                (new_height, new_width) = img.shape
                if new_height != height or new_width != width:
                    slice0.set_extent([0, new_width, new_height, 0])
                    height, width = new_height, new_width
            elif file_type == "cine":
                img = util.extract_frame_cine(file_path, index)
                img_norm = normalize_image(img, min_val, max_val)
                message_text.set_text(file_path)
            else:
                if axis == 0:
                    img = data[index, :, :]
                    img_norm = normalize_image(img)
                    slice0.set_extent([0, width, height, 0])
                else:
                    img = data[:, index, :]
                    img_norm = normalize_image(img)
                    slice0.set_extent([0, width, depth, 0])
            slice0.set_data(img_norm)
            ax[-1].clear()
            if hline:
                hline.set_visible(False)
            if vline:
                vline.set_visible(False)
            clicked_point, hline, vline = None, None, None
            self.current_image = img
            fig.canvas.draw_idle()

        def reset_sliders(event):
            min_slider.reset()
            max_slider.reset()
            slice0.autoscale()
            fig.canvas.draw_idle()

        slider0.on_changed(lambda v: update_axis(v, axis=0))
        if slider1 is not None:
            slider1.on_changed(lambda v: update_axis(v, axis=1))
            axis_selector.on_clicked(update_contrast)
        min_slider.on_changed(update_contrast)
        max_slider.on_changed(update_contrast)

        def on_scroll(event):
            if event.inaxes == ax[0]:
                if slider1 is not None:
                    if axis_selector.value_selected == "axis 0":
                        step = slider0.valstep if slider0.valstep else 1
                        current_val = slider0.val
                        sensitivity = SCROLL_SENSITIVITY
                        new_val = current_val + event.step * step * sensitivity
                        new_val = max(min(new_val, slider0.valmax),
                                      slider0.valmin)
                        slider0.set_val(new_val)
                    else:
                        step = slider1.valstep if slider1.valstep else 1
                        current_val = slider1.val
                        sensitivity = SCROLL_SENSITIVITY
                        new_val = current_val + event.step * step * sensitivity
                        new_val = max(min(new_val, slider1.valmax),
                                      slider1.valmin)
                        slider1.set_val(new_val)
                else:
                    step = slider0.valstep if slider0.valstep else 1
                    current_val = slider0.val
                    sensitivity = SCROLL_SENSITIVITY
                    new_val = current_val + event.step * step * sensitivity
                    new_val = max(min(new_val, slider0.valmax), slider0.valmin)
                    slider0.set_val(new_val)

        fig.canvas.mpl_connect("scroll_event", on_scroll)

        def update_intensity_plot_hor():
            nonlocal img, clicked_point
            axis = 1
            if clicked_point is not None:
                y, x = clicked_point
                index = int(slider0.val)
                if file_type == "tif":
                    if img is None:
                        img = util.load_image(list_files[index])
                elif file_type == "cine":
                    if img is None:
                        img = util.extract_frame_cine(file_path, index)
                else:
                    if img is None:
                        img = data[index]
                ax[axis].clear()
                self.current_table = img[y, :]
                ax[axis].plot(self.current_table, color="blue", linewidth=0.8)
                ax[axis].set_title(f"Intensity at row: {y}",
                                   fontsize=PLT_MAIN_FONTSIZE)
                ax[axis].set_xlabel("X", fontsize=PLT_MAIN_FONTSIZE)
                fig.canvas.draw_idle()

        def update_intensity_plot_ver():
            nonlocal img, clicked_point
            axis = 1
            if clicked_point is not None:
                y, x = clicked_point
                index = int(slider0.val)
                if file_type == "tif":
                    if img is None:
                        img = util.load_image(list_files[index])
                elif file_type == "cine":
                    if img is None:
                        img = util.extract_frame_cine(file_path, index)
                else:
                    if img is None:
                        img = data[index]
                ax[axis].clear()
                self.current_table = img[:, x]
                ax[axis].plot(self.current_table, color="blue", linewidth=0.8)
                ax[axis].set_title(f"Intensity at column: {x}",
                                   fontsize=PLT_MAIN_FONTSIZE)
                ax[axis].set_xlabel("Y")
                fig.canvas.draw_idle()

        def plot_intensity_along_clicked_point(event):
            nonlocal clicked_point, hline, vline
            if event.inaxes == ax[0]:
                clicked_point = (int(event.ydata), int(event.xdata))
                if hline is not None:
                    hline.set_visible(False)
                    hline = None
                if vline is not None:
                    vline.set_visible(False)
                    vline = None
                if event.button == 1:
                    hline = ax[0].axhline(clicked_point[0], color="red")
                    update_intensity_plot_hor()
                elif event.button == 3:
                    vline = ax[0].axvline(clicked_point[1], color="red")
                    update_intensity_plot_ver()

        fig.canvas.mpl_connect("button_press_event",
                               plot_intensity_along_clicked_point)

        top_window = tk.Toplevel(self)
        top_window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")
        canvas = FigureCanvasTkAgg(fig, master=top_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar_frame = tk.Frame(top_window)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        toolbar.pack(side=tk.LEFT, fill=tk.X)
        tk_reset_button = ttk.Button(toolbar_frame, text="Reset",
                                     command=lambda: reset_sliders(None))
        tk_reset_button.pack(side=tk.RIGHT, padx=10)

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
