import os
import gc
import threading
import signal
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

        # Initialize parameters
        self.populate_tree_view()
        self.stop_listing = False
        self._after_id = None
        self.selected_folder_path = None
        self.current_table = None
        self.current_image = None

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

    def populate_tree_async(self, parent_node, folder_path):
        """Use a thread to populate the tree asynchronously."""
        thread = threading.Thread(target=self.populate_tree,
                                  args=(parent_node, folder_path), daemon=True)
        thread.start()

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
                # Insert a dummy node for potential expansion
                self.folder_tree_view.insert(folder_node, "end", text="dummy")
        except PermissionError as e:
            print(f"Permission error accessing folder: {folder_path} - {e}")

    def on_tree_expand(self, event):
        """Handle tree expansion asynchronously to avoid GUI freezing."""
        selected_item = self.folder_tree_view.selection()[0]
        folder_path = self.folder_tree_view.item(selected_item, "values")[0]
        self.populate_tree_async(selected_item, folder_path)

    def file_generator(self, folder_path):
        """Generator to yield file names incrementally in sorted order
        and stop if needed.
        """
        try:
            with os.scandir(folder_path) as entries:
                files = sorted(
                    entry.name for entry in entries if entry.is_file())
                for file_name in files:
                    if self.stop_listing:
                        return
                    yield file_name
        except PermissionError as e:
            self.update_listbox(f"Permission error: {e}")

    def process_file_listing(self, folder_path):
        """Process the file listing using a generator to handle large
        directories incrementally."""
        for i, file_name in enumerate(self.file_generator(folder_path)):
            if self.stop_listing:
                return
            self.update_listbox(file_name)
        gc.collect()

    def update_listbox(self, message):
        self.after(0, lambda: self.file_list_view.insert(tk.END, message))

    def on_folder_select(self, event):
        """Handle folder selection from Treeview and stop listing from the
        previous folder."""
        selected_items = self.folder_tree_view.selection()
        if not selected_items:
            return
        self.stop_listing = True
        self.file_list_view.delete(0, tk.END)
        self.disable_hdf_key_entry()
        selected_item = selected_items[0]
        folder_path = self.folder_tree_view.item(selected_item, "values")[0]
        self.selected_folder_path = folder_path
        self.stop_listing = False
        self.update_status_bar(folder_path)
        thread = threading.Thread(target=self.process_file_listing,
                                  args=(folder_path,))
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
            hdf_datasets = []
            for key, item in hdf_obj.items():
                current_path = f"{base_path}/{key}".strip("/")
                if isinstance(item, h5py.Group):
                    hdf_datasets.extend(
                        find_array_datasets(item, current_path))
                elif isinstance(item, h5py.Dataset):
                    data_type, value = util.get_hdf_data(file_path,
                                                         current_path)
                    # Only keep array-like datasets
                    if (data_type == "array"
                            and isinstance(value, tuple)
                            and 0 < len(value) < 4):
                        hdf_datasets.append((current_path, value))
            return hdf_datasets

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
            self.update_status_bar("")
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
        if check == "tif":
            self.interactive_viewer(self.selected_folder_path, file_type="tif")
        elif check == "cine":
            selected_index = self.file_list_view.curselection()
            selected_file = self.file_list_view.get(selected_index)
            file_path = os.path.join(self.selected_folder_path, selected_file)
            self.interactive_viewer(file_path, file_type="cine")
        else:
            selected_index = self.file_list_view.curselection()
            if len(selected_index) == 0:
                messagebox.showinfo("Input needed", "Please select a hdf file")
                return
            self.interactive_viewer(self.selected_folder_path, file_type="hdf")

    def check_file_type_in_listbox(self):
        """Check if the listbox contains tif files or a hdf, cine file and
        return the file type."""
        if self.file_list_view.size() == 0:
            return None
        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            return
        file_name = self.file_list_view.get(selected_index)
        if file_name.lower().endswith((".tif", ".tiff")):
            return "tif"
        elif file_name.lower().endswith(ren.HDF_EXT):
            return "hdf"
        elif file_name.lower().endswith(ren.CINE_EXT):
            return "cine"
        return None

    def launch_table_viewer(self, event):
        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            messagebox.showinfo("Input needed", "Please select a file")
            return
        selected_file = self.file_list_view.get(selected_index[0])
        full_path = os.path.join(self.selected_folder_path, selected_file)
        if selected_file.lower().endswith(ren.HDF_EXT):
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data = util.load_hdf(full_path, hdf_key_path)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(ren.IMAGE_EXT):
            try:
                data = util.load_image(full_path, average=True)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(ren.CINE_EXT):
            data = util.get_time_stamps_cine(full_path)
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
        self.table_viewer(data)
        self.current_table = data

    def save_to_image(self, event):
        if self.current_image is not None:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".tif",
                filetypes=[("TIFF files", "*.tif"), ("PNG files", "*.png"),
                           ("JPEG files", "*.jpg")],
                title="Save Image As")
            if not file_path:
                return

            util.save_image(file_path, self.current_image)
            self.update_status_bar(f"Image saved to: {file_path}")
            self.current_image = None
        else:
            msg = "No selected image. Use Interactive-Viewer to choose one!"
            messagebox.showinfo("Input needed", msg)

    def save_to_table(self, event):
        if self.current_table is not None:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Save Data As")
            if not file_path:
                return
            total_elements = self.current_table.size
            if total_elements > 2000 * 2000:
                msg = ("Array is too large to be saved to csv format.\n"
                       "Please use Save-image for large arrays.")
                messagebox.showinfo("Array Too Large", msg)
                return
            util.save_table(file_path, self.current_table)
            self.update_status_bar(f"Data saved to: {file_path}")
            self.current_table = None
        else:
            msg = ("No selected data (1d or 2d-array from a file). "
                   "Use viewers to choose one!")
            messagebox.showinfo("Input needed", msg)

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
