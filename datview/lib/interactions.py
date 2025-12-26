import os
import gc
import signal
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import datview.lib.utilities as util
import datview.lib.rendering as ren

# ==============================================================================
#                          GUI Interactions
# ==============================================================================


class DatviewInteraction(ren.DatviewRendering):
    """
    Class to link user interactions to the responses of the software
    """
    def __init__(self, folder="."):
        super().__init__()
        self.base_folder = Path(folder).expanduser()
        if not self.base_folder.exists():
            msg = f"No folder: {self.base_folder}\nReset to: {Path.home()}"
            messagebox.showwarning("Folder does not exit", msg)
            self.base_folder = Path.home()
        self.base_folder_label.config(text=self.base_folder)
        # Link actions to GUI components
        self.interactive_viewer_button.bind("<Button-1>",
                                            self.launch_interactive_viewer)
        self.table_viewer_button.bind("<Button-1>", self.launch_table_viewer)
        self.select_base_folder_button.bind("<Button-1>",
                                            self.select_base_folder)
        self.folder_tree_view.bind("<<TreeviewSelect>>", self.on_folder_select)
        self.folder_tree_view.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.file_list_view.bind("<ButtonRelease-1>", self.on_file_select)
        self.file_list_view.bind("<Double-1>", self.on_file_double_click)
        self.file_list_view.bind("<Up>", self.on_arrow_key_click)
        self.file_list_view.bind("<Down>", self.on_arrow_key_click)
        self.save_image_button.bind("<Button-1>", self.save_to_image)
        self.save_table_button.bind("<Button-1>", self.save_to_table)
        self.export_tif_button.bind("<Button-1>",
                                    self.launch_export_tif_window)
        # Initialize parameters
        self.populate_tree_view()
        self.listing_counter = 0
        self._after_id = None
        self.selected_folder_path = None
        # Variables
        self.active_viewer_instance = None
        self.current_table = None
        self.current_image = None
        # Re-apply global Matplotlib font settings
        rc("font", size=ren.PLT_MAIN_FONTSIZE)
        rc("axes", titlesize=ren.PLT_MAIN_FONTSIZE)
        rc("axes", labelsize=ren.PLT_MAIN_FONTSIZE)
        rc("xtick", labelsize=ren.PLT_MAIN_FONTSIZE)
        rc("ytick", labelsize=ren.PLT_MAIN_FONTSIZE)
        # Handle exit event
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, self.on_exit_signal)
        self.shutdown_flag = False
        self.check_for_exit_signal()

    def set_active_viewer_instance(self, viewer):
        """Called by InteractiveViewer when it gains focus."""
        self.active_viewer_instance = viewer
        self.update_status_bar(f"Active viewer: {viewer.file_path}")

    def notify_viewer_closed(self, viewer):
        """Called by InteractiveViewer when it closes."""
        if self.active_viewer_instance == viewer:
            self.active_viewer_instance = None
            self.current_image = None
            self.current_table = None
            self.update_status_bar(self.selected_folder_path or "")

    def select_base_folder(self, event):
        """Open file dialog to select a new base folder."""
        selected_folder = filedialog.askdirectory(initialdir=self.base_folder,
                                                  title="Select Base Folder")
        if selected_folder:
            self.base_folder = selected_folder
            self.base_folder_label.config(text=self.base_folder)
            self.populate_tree_view()
            self.disable_hdf_key_entry()
            config_data = {"last_folder": self.base_folder}
            util.save_config(config_data)

    def update_status_bar(self, text):
        self.status_bar.config(state="normal")
        self.status_bar.delete(1.0, tk.END)
        self.status_bar.insert(tk.END, text)
        self.status_bar.config(state="disabled")

    def disable_hdf_key_entry(self):
        self.hdf_key_list.set("")
        self.hdf_key_list.config(state="disabled")

    def populate_tree_view(self):
        """Clear existing Treeview and populate with the current base folder.
        """
        for item in self.folder_tree_view.get_children():
            self.folder_tree_view.delete(item)
        root_node = self.folder_tree_view.insert("", "end",
                                                 text=str(self.base_folder),
                                                 open=False,
                                                 values=[self.base_folder])
        self.folder_tree_view.insert(root_node, "end", text="dummy")

    def populate_tree(self, parent_node, folder_path):
        """Populate the tree view with folders (not files) recursively."""
        existing_children = self.folder_tree_view.get_children(parent_node)
        for child in existing_children:
            self.folder_tree_view.delete(child)
        try:
            subfolders = [f for f in os.listdir(folder_path) if
                          os.path.isdir(os.path.join(folder_path, f))]
            for folder_name in sorted(subfolders):
                full_path = os.path.join(folder_path, folder_name)
                folder_node = self.folder_tree_view.insert(parent_node, "end",
                                                           text=folder_name,
                                                           values=[full_path])
                self.folder_tree_view.insert(folder_node, "end", text="dummy")
        except PermissionError as e:
            print(f"Permission error accessing folder: {folder_path} - {e}")

    def populate_tree_async(self, parent_node, folder_path):
        """Use a thread to populate the tree asynchronously."""
        thread = threading.Thread(target=self.populate_tree,
                                  args=(parent_node, folder_path), daemon=True)
        thread.start()

    def on_tree_expand(self, event):
        """Handle tree expansion synchronously."""
        selected_item = self.folder_tree_view.selection()[0]
        folder_path = self.folder_tree_view.item(selected_item, "values")[0]
        self.populate_tree_async(selected_item, folder_path)

    def file_generator(self, folder_path, request_id):
        """
        Generator to yield file names incrementally.
        Checks if the current request_id is still valid.
        """
        try:
            with os.scandir(folder_path) as entries:
                files = sorted(
                    entry.name for entry in entries if entry.is_file())
                for file_name in files:
                    if self.listing_counter != request_id:
                        return
                    yield file_name
        except PermissionError as e:
            self.update_listbox(f"Permission error: {e}")

    def process_file_listing(self, folder_path, request_id):
        """Process the file listing using a generator to handle large
        directories incrementally."""
        for i, file_name in enumerate(
                self.file_generator(folder_path, request_id)):
            if self.listing_counter != request_id:
                return
            self.update_listbox(file_name)
        gc.collect()

    def update_listbox(self, message):
        self.after(0, lambda: self.file_list_view.insert(tk.END, message))

    def on_folder_select(self, event):
        """Handle folder selection from Treeview."""
        selected_items = self.folder_tree_view.selection()
        if not selected_items:
            return
        self.listing_counter += 1
        current_request_id = self.listing_counter
        self.file_list_view.delete(0, tk.END)
        self.disable_hdf_key_entry()
        selected_item = selected_items[0]
        folder_path = self.folder_tree_view.item(selected_item, "values")[0]
        self.selected_folder_path = folder_path
        self.update_status_bar(folder_path)
        gc.collect()
        thread = threading.Thread(target=self.process_file_listing,
                                  args=(folder_path, current_request_id),
                                  daemon=True)
        thread.start()

    def restore_focus_to_listbox(self, current_selection):
        """Restore focus to the file listbox after combobox interaction."""
        self.file_list_view.focus_set()
        if current_selection:
            self.file_list_view.selection_clear(0, tk.END)
            self.file_list_view.selection_set(current_selection)
            self.file_list_view.activate(current_selection)

    def populate_hdf_key_list(self, file_path):

        def find_array_datasets(hdf_obj, base_path=""):
            """Search for datasets in hdf file that are 1D, 2D, or 3D arrays.
            """
            hdf_datasets_t = []
            for key, item in hdf_obj.items():
                current_path = f"{base_path}/{key}".strip("/")
                if isinstance(item, h5py.Group):
                    hdf_datasets_t.extend(
                        find_array_datasets(item, current_path))
                elif isinstance(item, h5py.Dataset):
                    data_type, value = util.get_hdf_data(file_path,
                                                         current_path)
                    # Only keep array-like datasets
                    if (data_type == "array"
                            and isinstance(value, tuple)
                            and 0 < len(value) < 4):
                        hdf_datasets_t.append((current_path, value))
            return hdf_datasets_t

        current_selection = self.file_list_view.curselection()
        self.hdf_key_list.set("")
        self.hdf_key_list.config(state="normal")
        self.hdf_key_list["values"] = []
        try:
            with h5py.File(file_path, "r") as hdf_file:
                # Find all array datasets (1D, 2D, or 3D)
                hdf_datasets = find_array_datasets(hdf_file)
                hdf_datasets.sort(key=lambda x: len(x[1]), reverse=True)
                if hdf_datasets:
                    dataset_paths = [dataset[0] for dataset in hdf_datasets]
                    self.hdf_key_list["values"] = dataset_paths
                    self.hdf_key_list.set(dataset_paths[0])
                else:
                    self.hdf_key_list.set("No valid arrays found")
                    self.hdf_key_list.config(state="disabled")
            # Restore the previous selection in the file listbox
            if current_selection:
                self.file_list_view.selection_clear(0, tk.END)
                self.file_list_view.selection_set(current_selection)
                self.file_list_view.activate(current_selection)
            # After selecting from the combobox, restore focus to the listbox
            self.hdf_key_list.bind("<<ComboboxSelected>>",
                                   lambda event: self.restore_focus_to_listbox(
                                       current_selection))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse HDF5 file: {e}")
            self.disable_hdf_key_entry()
            return

    def _handle_single_click(self):
        """Handler for single-click after the delay."""
        selected_index = self.file_list_view.curselection()
        if not selected_index:
            self.disable_hdf_key_entry()
            self.update_status_bar(self.selected_folder_path or "")
            return
        file_index = selected_index[0]
        selected_file = self.file_list_view.get(file_index)
        full_path = os.path.join(self.selected_folder_path, selected_file)
        self.update_status_bar(
            f"File-index: {file_index}. Full-path: {full_path}")
        if selected_file.endswith(ren.HDF_EXT):
            self.populate_hdf_key_list(full_path)
        else:
            self.disable_hdf_key_entry()

    def on_file_select(self, event):
        """Handle single-click on a file in the listbox."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        # Delay to check if it will turn into a double click
        self._after_id = self.after(200, self._handle_single_click)

    def on_arrow_key_click(self, event):
        selected_index = self.file_list_view.curselection()
        if not selected_index:
            return
        current_index = selected_index[0]
        new_index = current_index
        if event.keysym == "Up" and current_index > 0:
            new_index = current_index - 1
        elif (event.keysym == "Down"
              and current_index < self.file_list_view.size() - 1):
            new_index = current_index + 1
        self.file_list_view.selection_clear(0, tk.END)
        self.file_list_view.selection_set(new_index)
        self.file_list_view.activate(new_index)
        self.file_list_view.see(new_index)
        # Trigger the same behavior as clicking on a file
        self.on_file_select(None)
        return "break"

    def display_image_file(self, file_path):
        """Display an image using Matplotlib with sliders to adjust contrast"""
        try:
            img = util.load_image(file_path)
            self.show_2d_image(img, file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the image: {e}")

    def display_hdf_file(self, file_path):
        """Display structure of a hdf file"""
        try:
            hdf_file = h5py.File(file_path, "r")
            current_selected_file = self.file_list_view.curselection()
            hdf_window = tk.Toplevel(self)
            hdf_window.title(f"HDF Viewer: {file_path}")
            width, height, x_offset, y_offset = self.define_window_geometry(
                ren.TEXT_WIN_RATIO)
            hdf_window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
            # Configure the grid layout
            hdf_window.grid_columnconfigure(0, weight=1)
            hdf_window.grid_columnconfigure(1, weight=1)
            hdf_window.grid_rowconfigure(0, weight=1)
            # Frame for tree view
            tree_frame = ttk.Frame(hdf_window)
            tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            tree_frame.grid_rowconfigure(0, weight=0)
            tree_frame.grid_rowconfigure(1, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            # Create the tree view for HDF5 structure
            tree_frame_label = ttk.Label(tree_frame,
                                         text="HDF File Hierarchy")
            tree_frame_label.grid(row=0, column=0, sticky="new")
            tree_view = ttk.Treeview(tree_frame, show="tree")
            tree_view.grid(row=1, column=0, sticky="nsew")
            # Frame for the output field with scrollbars
            info_frame = ttk.Frame(hdf_window)
            info_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            # Configure grid for the info frame
            info_frame.grid_rowconfigure(0, weight=0)
            info_frame.grid_rowconfigure(1, weight=1)
            info_frame.grid_columnconfigure(0, weight=1)
            # Text widget for displaying details about selected group/dataset
            info_frame_text = "Brief Information On Datasets and Groups"
            info_frame_label = ttk.Label(info_frame, text=info_frame_text)
            info_frame_label.grid(row=0, column=0, sticky="new")
            info_text = tk.Text(info_frame, wrap="none", height=20, width=30)
            info_text.grid(row=1, column=0, sticky="nsew")
            # Scrollbars for the text widget
            info_scrollbar_ver = tk.Scrollbar(info_frame, orient="vertical",
                                              command=info_text.yview)
            info_scrollbar_hor = tk.Scrollbar(info_frame, orient="horizontal",
                                              command=info_text.xview)
            info_text.config(yscrollcommand=info_scrollbar_ver.set,
                             xscrollcommand=info_scrollbar_hor.set)
            info_scrollbar_ver.grid(row=1, column=1, sticky="ns")
            info_scrollbar_hor.grid(row=2, column=0, sticky="ew", padx=(1, 0))
            # Populate the tree with groups and datasets
            self.populate_hdf_tree(tree_view, hdf_file)

            def on_tree_select(event):
                selected_item = tree_view.selection()[0]
                hdf_path = tree_view.item(selected_item, "text")
                data_type, value = util.get_hdf_data(file_path, hdf_path)
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, f"HDF Path: {hdf_path}\n")
                info_text.insert(tk.END, f"Data Type: {data_type}\n")
                if data_type == "array":
                    info_text.insert(tk.END, f"Shape: {value}")
                else:
                    info_text.insert(tk.END, f"Value: {value}")

            def on_close_hdf_window():
                if current_selected_file:
                    self.file_list_view.selection_clear(0, tk.END)
                    self.file_list_view.selection_set(current_selected_file)
                    self.file_list_view.activate(current_selected_file)
                hdf_window.destroy()

            # Bind selection event to show group or dataset info
            tree_view.bind("<<TreeviewSelect>>", on_tree_select)
            hdf_window.protocol("WM_DELETE_WINDOW", on_close_hdf_window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the HDF file: {e}")

    def populate_hdf_tree(self, tree_view, hdf_file, parent=""):
        def add_node(name, obj):
            tree_view.insert(parent, "end", text=name)
            if isinstance(obj, h5py.Group):
                for subname, subobj in obj.items():
                    add_node(f"{name}/{subname}", subobj)

        for item_name, item in hdf_file.items():
            add_node(item_name, item)

    def on_file_double_click(self, event):
        """Handle double-click on a file in the listbox."""
        selected_index = self.file_list_view.curselection()
        if not selected_index:
            return
        selected_file = self.file_list_view.get(selected_index[0])
        full_path = os.path.join(self.selected_folder_path, selected_file)
        selected_file = selected_file.lower()
        if (selected_file.endswith(ren.TEXT_EXT)
                or selected_file.endswith(ren.CINE_EXT)):
            self.display_text_file(full_path)
        elif selected_file.endswith(ren.IMAGE_EXT):
            self.display_image_file(full_path)
        elif selected_file.endswith(ren.HDF_EXT):
            self.display_hdf_file(full_path)
        else:
            if util.is_text_file(full_path):
                self.display_text_file(full_path)
            else:
                messagebox.showerror("Not support format",
                                     "Can't open this file format")

    def launch_interactive_viewer(self, event):
        """Launch the interactive viewer for the selected folder/file."""
        check = self.check_file_type_in_listbox()
        if check is None:
            msg = ("Please select a hdf file, a cine file, or any tif file in "
                   "the folder")
            messagebox.showinfo("Input needed", msg)
            return
        file_path = None
        list_files = None
        hdf_key_path = None
        selected_index = self.file_list_view.curselection()
        if not selected_index:
            messagebox.showinfo("Input needed", "Please select a file")
            return
        selected_file = self.file_list_view.get(selected_index[0])
        if check == "tif":
            file_path = self.selected_folder_path
            list_files = util.find_file(file_path)
            if not list_files:
                messagebox.showerror("No Files",
                                     f"No image files found in: {file_path}")
                return
        elif check == "cine":
            file_path = os.path.join(self.selected_folder_path, selected_file)
        elif check == "hdf":
            file_path = os.path.join(self.selected_folder_path, selected_file)
            hdf_key_path = self.hdf_key_list.get().strip()
            if not hdf_key_path or hdf_key_path == "No valid arrays found":
                messagebox.showinfo("Input needed",
                                    "Please select an HDF array key.")
                return
            try:
                data_obj, file_obj = util.load_hdf(file_path, hdf_key_path,
                                                   return_file_obj=True)
                data_shape = data_obj.shape
                data_ndim = len(data_shape)
                if data_ndim == 1:
                    data = data_obj[:]
                    self.current_table = data
                    self.show_1d_data(data,
                                      help_text="HDF-key: " + hdf_key_path,
                                      title=file_path)
                    file_obj.close()
                    return
                elif data_ndim == 2:
                    data = data_obj[:]
                    self.current_image = data
                    self.show_2d_image(data, file_path)
                    file_obj.close()
                    return
                elif data_ndim != 3:
                    messagebox.showerror("Can't show data",
                                         f"Only can show 1d, 2d, or 3d data. "
                                         f"Not {data_ndim}d")
                    return
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return

        inter_window = tk.Toplevel(self)
        inter_window.title(f"Viewing: {os.path.basename(file_path)}")
        try:
            ren.InteractiveViewer(main_window=inter_window, main_app=self,
                                  file_path=file_path, file_type=check,
                                  hdf_key=hdf_key_path,
                                  list_files=list_files)
        except Exception as e:
            messagebox.showerror("Viewer Error",
                                 f"Failed to initialize viewer: {e}")
            inter_window.destroy()

    def check_file_type_in_listbox(self):
        """Check if the listbox contains tif files or a hdf, cine file."""
        if self.file_list_view.size() == 0:
            return None
        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            try:
                if self.selected_folder_path:
                    for entry in os.scandir(self.selected_folder_path):
                        if entry.name.lower().endswith(ren.IMAGE_EXT):
                            return "tif"
            except:
                pass
            return None

        file_name = self.file_list_view.get(selected_index[0])
        if file_name.lower().endswith(ren.IMAGE_EXT):
            return "tif"
        elif file_name.lower().endswith(ren.HDF_EXT):
            return "hdf"
        elif file_name.lower().endswith(ren.CINE_EXT):
            return "cine"
        return None

    def launch_table_viewer(self, event):
        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            if self.active_viewer_instance:
                self.save_to_table(event)
                return
            messagebox.showinfo("Input needed", "Please select a file")
            return
        selected_file = self.file_list_view.get(selected_index[0])
        full_path = os.path.join(self.selected_folder_path, selected_file)
        self.current_table = None
        file_obj = None
        if selected_file.lower().endswith(ren.HDF_EXT):
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data, file_obj = util.load_hdf(full_path, hdf_key_path,
                                               return_file_obj=True)
                win_title = full_path + " | HDF-key: " + hdf_key_path
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(ren.IMAGE_EXT):
            try:
                data = util.load_image(full_path, average=True)
                win_title = full_path + " | Averaged Channel"
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(ren.CINE_EXT):
            data = util.get_time_stamps_cine(full_path)
            win_title = full_path + " | Time stamps"
        else:
            return
        if 1 in data.shape:
            data = np.squeeze(data)
        if len(data.shape) > 2:
            messagebox.showinfo("Invalid Array",
                                "This function is only for 1D or 2D arrays.")
            return
        total_elements = data.size
        if total_elements > 2000 * 2000:
            msg = ("Array is too large to be displayed in the Table Viewer.\n"
                   "Please use image viewer for large arrays.")
            messagebox.showinfo("Array Too Large", msg)
            return
        self.table_viewer(data, win_title)
        if file_obj is not None:
            file_obj.close()
        self.current_table = data

    def save_to_image(self, event):
        """Saves the current image slice from the ACTIVE viewer."""
        viewer = self.active_viewer_instance
        if viewer is None or not hasattr(viewer, 'viewer_state'):
            if self.current_image is None:
                msg = "No active image. Use Interactive-Viewer!"
                messagebox.showinfo("Input needed", msg)
                return
            img_to_save = self.current_image
        else:
            img_to_save = viewer.viewer_state.get("image")
            if img_to_save is None:
                messagebox.showinfo("Input needed",
                                    "Active viewer has no current "
                                    "image slice.")
                return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".tif",
            filetypes=[("TIFF files", "*.tif"), ("PNG files", "*.png"),
                       ("JPEG files", "*.jpg")],
            title="Save Image As")
        if not file_path:
            return
        util.save_image(file_path, img_to_save)
        self.update_status_bar(f"Image saved to: {file_path}")

    def save_to_table(self, event):
        """Saves 1D line profile from ACTIVE viewer OR last loaded array."""
        viewer = self.active_viewer_instance
        if viewer is not None and hasattr(viewer, 'viewer_state'):
            data_to_save = viewer.viewer_state.get("table")
            if data_to_save is None:
                data_to_save = self.current_table
        else:
            data_to_save = self.current_table

        if data_to_save is None:
            msg = "No selected data. Use viewers or click image for profile!"
            messagebox.showinfo("Input needed", msg)
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Data As")
        if not file_path:
            return
        data_to_save = np.asarray(data_to_save)
        total_elements = data_to_save.size
        if total_elements > 2000 * 2000:
            msg = "Array too large. Operation aborted."
            messagebox.showinfo("Array Too Large", msg)
            return
        util.save_table(file_path, data_to_save)
        self.update_status_bar(f"Data saved to: {file_path}")

    def export_tif_window(self, file_path, file_type):
        """
        Creates the window for exporting HDF/CINE data to TIF files.
        """
        input_path = None
        hdf_key_path = None
        hdf_object = None
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
                data, hdf_object = util.load_hdf(full_path, hdf_key_path,
                                                 return_file_obj=True)
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
                                         f"{depth, height, width}")}

        def on_close_window():
            """
            Cleanup variables explicitly to satisfy the Garbage Collector
            before destroying the Tcl widget.
            """
            for v in export_window.vars.values():
                try:
                    v.set("")
                except tk.TclError:
                    pass
            export_window.vars.clear()
            export_window.destroy()
            if hdf_object is not None:
                hdf_object.close()

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
                                                    sticky="ew", padx=5,
                                                    pady=5)
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
                                                             sticky="w",
                                                             padx=5, pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_start"],
                  width=8).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Y-stop:").grid(row=0, column=2, sticky="w",
                                                   padx=(15, 5), pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_stop"],
                  width=8).grid(row=0, column=3, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Width  | X-start:").grid(row=1, column=0,
                                                             sticky="w",
                                                             padx=5, pady=5)
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
        ttk.Entry(naming_frame,
                  textvariable=export_window.vars["prefix"]).grid(row=0,
                                                                  column=1,
                                                                  sticky="ew",
                                                                  padx=5,
                                                                  pady=5)

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
            params['slice_start'] = parse_int(
                export_window.vars["start"].get(), 0)
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
                params['min_percent'] = float(
                    export_window.vars["min_p"].get())
                params['max_percent'] = float(
                    export_window.vars["max_p"].get())
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
                messagebox.showerror("Export Error",
                                     f"An error occurred:\n{e}",
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

    def launch_export_tif_window(self, event):
        """Launch the interactive viewer for the selected folder/file."""
        check = self.check_file_type_in_listbox()
        if check is None or check == "tif":
            msg = "Please select a HDF file or a CINE file"
            messagebox.showinfo("Input needed", msg)
            return

        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            messagebox.showinfo("Input needed", "Please select a file")
            return

        selected_file = self.file_list_view.get(selected_index[0])
        file_path = os.path.join(self.selected_folder_path, selected_file)

        if check == "cine":
            self.export_tif_window(file_path, file_type="cine")
        else:  # hdf
            hdf_key_path = self.hdf_key_list.get().strip()
            if not hdf_key_path or hdf_key_path == "No valid arrays found":
                messagebox.showinfo("Input needed",
                                    "Please select an HDF array key.")
                return
            self.export_tif_window(file_path, file_type="hdf")

    def on_exit(self):
        if not self.shutdown_flag:
            self.shutdown_flag = True
            try:
                if self._after_id is not None:
                    self.after_cancel(self._after_id)
                    self._after_id = None
                try:
                    self.after_cancel(self.check_for_exit_id)
                except AttributeError:
                    pass

                print("\n************")
                print("Exit the app")
                print("************\n")

                if self.active_viewer_instance and hasattr(
                        self.active_viewer_instance, 'on_close'):
                    self.active_viewer_instance.on_close()

                plt.close("all")
                self.destroy()
            except Exception as e:
                print("\n************")
                print(f"Exit the app with error {e}")
                print("************\n")
                plt.close("all")
                self.destroy()
        plt.rcdefaults()

    def on_exit_signal(self, signum, frame):
        self.on_exit()

    def check_for_exit_signal(self):
        self.check_for_exit_id = self.after(10, self.check_for_exit_signal)
