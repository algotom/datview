"""
Interactions module for DatView.
Acts as the Controller (MVC), orchestrating UI and business logic.
Strictly follows PEP8 and MVC principles.
"""

import os
import sys
import json
import threading
from pathlib import Path
import h5py
import numpy as np
from PIL import Image
import pyqtgraph as pg
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import (QApplication, QFileDialog, QMessageBox,
                               QTreeWidgetItem, QInputDialog, QLineEdit)

import datview.lib.rendering as ren
import datview.lib.utilities as util


class DatviewInteraction(QObject):
    """Primary Controller for the DatView application."""

    def __init__(self, base_folder=None):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName(util.APP_NAME)
        self.app.setFont(ren.select_ui_font(point_size=util.FONT_SIZE,
                                            weight=util.FONT_WEIGHT))
        # Load saved theme (default Light)
        config_data = util.load_config()
        saved_theme = "Light"
        if config_data and "theme" in config_data:
            if config_data["theme"] in ren.THEMES:
                saved_theme = config_data["theme"]
        ren.apply_theme(self.app, saved_theme)

        if base_folder is None:
            base_folder = config_data.get("last_folder") if config_data else None
            if not base_folder:
                base_folder = os.path.expanduser("~")

        self.base_folder = Path(base_folder).expanduser()
        if not self.base_folder.exists():
            self.base_folder = Path.home()

        self.main_win = ren.DatviewMainWindow(str(self.base_folder))
        # Restore theme combo
        self.main_win.combo_theme.blockSignals(True)
        self.main_win.combo_theme.setCurrentText(saved_theme)
        self.main_win.combo_theme.blockSignals(False)
        self.active_viewer = None
        self.viewers = []
        self.current_table = None
        self.current_image = None
        self.listing_counter = 0
        self.selected_folder_path = str(self.base_folder)
        self.main_win.selected_folder_path = self.selected_folder_path

        self._wire_signals()
        self.populate_tree_root()

    def _wire_signals(self):
        """Wire UI signals to controller slots."""
        self.main_win.sig_browse_requested.connect(self.select_base_folder)
        self.main_win.sig_theme_changed.connect(self.on_theme_changed)
        self.main_win.sig_folder_selected.connect(self.on_folder_select)
        self.main_win.sig_file_select_changed.connect(
            self.on_file_select_change)
        self.main_win.sig_file_double_clicked.connect(self.on_file_double_click)
        self.main_win.sig_launch_inter_requested.connect(
            self.launch_interactive_viewer)
        self.main_win.sig_launch_table_requested.connect(
            self.launch_table_viewer)
        self.main_win.sig_launch_export_requested.connect(self.launch_export)
        self.main_win.sig_tree_expand_requested.connect(self.on_tree_expand)
        self.main_win.sig_ctx_copy_full_path.connect(self.on_ctx_copy_full_path)
        self.main_win.sig_ctx_rename_file.connect(self.on_ctx_rename_file)
        self.main_win.sig_ctx_make_subfolder.connect(self.on_ctx_make_subfolder)

    def select_base_folder(self):
        d = QFileDialog.getExistingDirectory(self.main_win,
                                             "Select Base Folder",
                                             str(self.base_folder))
        if d:
            self.base_folder = Path(d)
            self.main_win.lbl_base_folder.setText(str(self.base_folder))
            self.selected_folder_path = str(self.base_folder)
            self.main_win.selected_folder_path = self.selected_folder_path
            self.populate_tree_root()
            self.main_win.combo_hdf.clear()
            self.main_win.combo_hdf.setEnabled(False)
            theme_name = self.main_win.combo_theme.currentText()
            util.save_config({"last_folder": str(self.base_folder), "theme": theme_name})

    def on_theme_changed(self, theme_name: str):
        """Apply the selected theme and refresh open viewer backgrounds."""
        if not self.app:
            return
        ren.apply_theme(self.app, theme_name)
        pg_bg = pg.mkColor(ren.sel_theme["SURFACE"])
        for v in self.viewers:
            if hasattr(v, "imv") and v.imv is not None:
                try:
                    v.imv.getHistogramWidget().setBackground(pg_bg)
                except Exception:
                    pass
        cfg = {"last_folder": str(self.base_folder), "theme": theme_name}
        util.save_config(cfg)

    def populate_tree_root(self):
        self.main_win.tree.clear()
        item = QTreeWidgetItem(self.main_win.tree)
        item.setText(0, str(self.base_folder))
        item.setData(0, Qt.UserRole, str(self.base_folder))
        # Add dummy to allow expansion
        dummy = QTreeWidgetItem(item)
        dummy.setText(0, "")

    def on_tree_expand(self, item):
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.isdir(path):
            return
        # Always refresh contents when expanding
        item.takeChildren()
        try:
            subfolders = sorted(
                d for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))
            )
            for sub in subfolders:
                child = QTreeWidgetItem(item)
                child.setText(0, sub)
                child.setData(0, Qt.UserRole, os.path.join(path, sub))
                try:
                    child_path = child.data(0, Qt.UserRole)
                    has_kids = any(
                        e.is_dir() for e in os.scandir(child_path)
                    )
                except Exception:
                    has_kids = False
                if has_kids:
                    dummy = QTreeWidgetItem(child)
                    dummy.setText(0, "")
        except Exception as e:
            util.logger.error(f"Error reading folder: {e}")

    def on_folder_select(self):
        items = self.main_win.tree.selectedItems()
        if not items:
            return
        path = items[0].data(0, Qt.UserRole)
        if not path or not os.path.isdir(path):
            return

        self.listing_counter += 1
        current_request_id = self.listing_counter
        self.selected_folder_path = path
        self.main_win.selected_folder_path = path
        self.main_win.statusBar().showMessage(path)

        self.main_win.list_files.clear()
        self.main_win.combo_hdf.clear()
        self.main_win.combo_hdf.setEnabled(False)

        threading.Thread(target=self._populate_files_thread,
                         args=(path, current_request_id),
                         daemon=True).start()

    def on_ctx_copy_full_path(self, full_path: str):
        if not full_path:
            return
        QApplication.clipboard().setText(os.path.normpath(full_path))
        try:
            self.main_win.statusBar().showMessage(f"Copied: {full_path}", 2500)
        except Exception:
            pass

    def on_ctx_rename_file(self, full_path: str):
        if not full_path or not os.path.exists(full_path):
            return

        folder = os.path.dirname(full_path)
        old_name = os.path.basename(full_path)

        new_name, ok = QInputDialog.getText(
            self.main_win, "Change file name", "New name:", QLineEdit.Normal,
            old_name
        )
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name:
            return
        if (os.sep in new_name) or (os.altsep and os.altsep in new_name):
            QMessageBox.warning(self.main_win, "Invalid name",
                                "Name must not contain path separators.")
            return

        new_path = os.path.join(folder, new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self.main_win, "Already exists",
                                f"Target already exists:\n{new_path}")
            return

        try:
            os.rename(full_path, new_path)
        except Exception as e:
            QMessageBox.critical(self.main_win, "Rename failed", str(e))
            return

        self._refresh_current_folder_files()

    def on_ctx_make_subfolder(self, folder_path: str):
        folder_path = folder_path or ""
        if not folder_path or not os.path.isdir(folder_path):
            return

        name, ok = QInputDialog.getText(
            self.main_win, "Make sub-folder", "Folder name:", QLineEdit.Normal,
            ""
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if (os.sep in name) or (os.altsep and os.altsep in name):
            QMessageBox.warning(self.main_win, "Invalid name",
                                "Folder name must not contain path separators.")
            return

        new_dir = os.path.join(folder_path, name)
        if os.path.exists(new_dir):
            QMessageBox.warning(self.main_win, "Already exists",
                                f"Folder already exists:\n{new_dir}")
            return

        try:
            os.makedirs(new_dir, exist_ok=False)
        except Exception as e:
            QMessageBox.critical(self.main_win, "Create folder failed", str(e))
            return

        self._refresh_current_folder_files()

    def _refresh_current_folder_files(self):
        if not hasattr(self,
                       "selected_folder_path") or not self.selected_folder_path:
            return

        path = self.selected_folder_path
        self.listing_counter += 1
        current_request_id = self.listing_counter

        self.main_win.list_files.clear()
        self.main_win.combo_hdf.clear()
        self.main_win.combo_hdf.setEnabled(False)

        threading.Thread(
            target=self._populate_files_thread,
            args=(path, current_request_id),
            daemon=True
        ).start()

    def _populate_files_thread(self, path, request_id):
        try:
            files = sorted([f.name for f in os.scandir(path) if f.is_file()])

            def update_ui():
                if request_id == self.listing_counter:
                    self.main_win.list_files.addItems(files)

            QTimer.singleShot(0, self, update_ui)
        except Exception as e:
            util.logger.error(f"Error populating files: {e}")

    def on_file_select_change(self):
        QTimer.singleShot(util.FILE_SELECT_DEBOUNCE_MS, self,
                          self._handle_file_single_click)

    def _handle_file_single_click(self):
        items = self.main_win.list_files.selectedItems()
        if not items:
            if hasattr(self, 'selected_folder_path'):
                self.main_win.statusBar().showMessage(self.selected_folder_path)
            return
        fname = items[0].text()
        if not hasattr(self, 'selected_folder_path'):
            return
        full = os.path.join(self.selected_folder_path, fname)
        self.main_win.statusBar().showMessage(full)

        ext = Path(full).suffix.lower()
        self.main_win.sb_filetype.setText(ext.upper() if ext else "FILE")
        self.main_win.sb_dims.setText("")

        try:
            if ext in util.IMAGE_EXT:
                with Image.open(full) as img:
                    self.main_win.sb_dims.setText(f"{img.height}x{img.width}")
            elif ext == ".cine":
                m = util.get_metadata_cine(full)
                self.main_win.sb_dims.setText(
                    f"{m['TotalImageCount']}x{m['biHeight']}x{m['biWidth']}"
                )
        except Exception:
            pass

        if fname.lower().endswith(util.HDF_EXT):
            self.populate_hdf_keys(full)
        else:
            self.main_win.combo_hdf.clear()
            self.main_win.combo_hdf.setEnabled(False)

    def populate_hdf_keys(self, file_path: str):
        selected_items = self.main_win.list_files.selectedItems()
        selected_row = self.main_win.list_files.row(
            selected_items[0]) if selected_items else None

        self.main_win.combo_hdf.blockSignals(True)
        self.main_win.combo_hdf.clear()
        self.main_win.combo_hdf.setEnabled(True)

        def find_array_datasets(hdf_obj, base_path=""):
            """Find datasets that are 1D/2D/3D numeric arrays (shape tuple)."""
            out = []
            for key, item in hdf_obj.items():
                current_path = f"{base_path}/{key}".strip("/")
                if isinstance(item, h5py.Group):
                    out.extend(find_array_datasets(item, current_path))
                elif isinstance(item, h5py.Dataset):
                    data_type, value = util.get_hdf_data(file_path,
                                                         current_path)
                    if (data_type == "array" and
                            isinstance(value, tuple) and
                            0 < len(value) < 4):
                        out.append((current_path, value))
            return out

        try:
            with h5py.File(file_path, "r") as hdf_file:
                hdf_datasets = find_array_datasets(hdf_file)
                # sort by ndim (len(shape)) descending
                hdf_datasets.sort(key=lambda x: len(x[1]), reverse=True)

            if hdf_datasets:
                dataset_paths = [p for (p, _shape) in hdf_datasets]
                self.main_win.combo_hdf.addItems(dataset_paths)
                self.main_win.combo_hdf.setCurrentIndex(0)
                self.main_win.combo_hdf.setEnabled(True)
            else:
                self.main_win.combo_hdf.addItem("No valid arrays found")
                self.main_win.combo_hdf.setEnabled(False)

        except Exception as e:
            self.main_win.combo_hdf.clear()
            self.main_win.combo_hdf.addItem("No valid arrays found")
            self.main_win.combo_hdf.setEnabled(False)

        finally:
            self.main_win.combo_hdf.blockSignals(False)

            # Restore selection + focus back to file list (Tkinter-like UX)
            if (selected_row is not None and
                    0 <= selected_row < self.main_win.list_files.count()):
                self.main_win.list_files.setCurrentRow(selected_row)
            self.main_win.list_files.setFocus()

    def on_file_double_click(self, item):
        fname = item.text()
        full = os.path.join(self.selected_folder_path, fname)
        ext = Path(full).suffix.lower()

        if ext in util.TEXT_EXT or ext == util.CINE_EXT:
            self.display_text_file(full)
        elif ext in util.IMAGE_EXT:
            self.display_image_file(full)
        elif ext in util.HDF_EXT:
            self.display_hdf_file(full)
        elif util.is_text_file(full):
            self.display_text_file(full)
        else:
            QMessageBox.warning(self.main_win, "Warning",
                                "Unsupported file format")

    def display_text_file(self, path):
        try:
            if path.lower().endswith(util.CINE_EXT):
                meta = util.get_metadata_cine(path)
                content = json.dumps(meta, indent=4)
            else:
                content = None
            win = ren.TextViewerWindow(self.main_win, title=f"Viewing: {path}",
                                       file_path=path, content=content,
                                       ratio=util.TEXT_WIN_RATIO)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self.main_win, "Error", str(e))

    def display_image_file(self, path):
        try:
            img = util.load_image(path)
            win = ren.Viewer2DWindow(self,
                                     title=f"Viewing: {os.path.basename(path)}."
                                           f" (Height, Width) = {img.shape}",
                                     image=img, file_path=path)
            win.parent_app = self
            self._show_window(win)
            self.active_viewer = win
        except Exception as e:
            QMessageBox.critical(self.main_win, "Error", str(e))

    def display_hdf_file(self, path):
        try:
            win = ren.HDFViewerWindow(self.main_win, file_path=path,
                                      ratio=util.TEXT_WIN_RATIO)
            win.sig_item_double_clicked.connect(
                self.open_hdf_dataset_from_tree)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self.main_win, "Error", str(e))

    def open_hdf_dataset_from_tree(self, file_path: str, hdf_key: str):
        data_type, value = util.get_hdf_data(file_path, hdf_key)
        file_obj = None
        if data_type != "array" or not isinstance(value, tuple):
            return
        ndim = len(value)
        try:
            data_obj, file_obj = util.load_hdf(file_path, hdf_key,
                                               return_file_obj=True)
            if ndim == 1:
                data = data_obj[:]
                self.current_table = data
                win = ren.TableViewerWindow(self.main_win, title=file_path,
                                            data=data)
                self._show_window(win)
                return
            if ndim == 2:
                data = np.squeeze(np.asarray(data_obj[:]))
                self.current_image = data
                win = ren.Viewer2DWindow(self,
                                         title=os.path.basename(file_path),
                                         image=data, file_path=file_path)
                win.parent_app = self
                self._show_window(win)
                self.active_viewer = win
                return
            if ndim == 3:
                win = ren.InteractiveViewerWindow(self, file_path, "hdf",
                                                  hdf_key, None)
                self._show_window(win)
                self.active_viewer = win
                return
        finally:
            if file_obj is not None:
                try:
                    file_obj.close()
                except Exception:
                    pass

    def check_file_type_in_list(self):
        if self.main_win.list_files.count() == 0:
            return None
        items = self.main_win.list_files.selectedItems()
        if not items:
            try:
                if hasattr(self, 'selected_folder_path'):
                    for entry in os.scandir(self.selected_folder_path):
                        if entry.name.lower().endswith(util.IMAGE_EXT):
                            return "tif"
            except:
                pass
            return None
        fname = items[0].text().lower()
        if fname.endswith(util.IMAGE_EXT):
            return "tif"
        if fname.endswith(util.HDF_EXT):
            return "hdf"
        if fname.endswith(util.CINE_EXT):
            return "cine"
        return None

    def launch_interactive_viewer(self):
        check = self.check_file_type_in_list()
        if check is None:
            msg = ("Please select a HDF file, a CINE file, or any TIF file "
                   "in a folder")
            QMessageBox.information(self.main_win, "Input needed", msg)
            return

        items = self.main_win.list_files.selectedItems()
        if not items and check != "tif":
            QMessageBox.information(self.main_win, "Input needed",
                                    "Please select a file")
            return

        fname = items[0].text() if items else ""
        path = os.path.join(self.selected_folder_path, fname)

        ftype = check
        hdf_key = None
        list_files = None

        if check == "tif":
            list_files = util.find_file(self.selected_folder_path)
            if not list_files:
                QMessageBox.critical(self.main_win, "No Files",
                                     f"No image files found in: "
                                     f"{self.selected_folder_path}")
                return
            path = self.selected_folder_path
        elif check == "hdf":
            hdf_key = self.main_win.combo_hdf.currentText().strip()
            if not hdf_key or hdf_key == "No arrays found":
                QMessageBox.information(self.main_win, "Input needed",
                                        "Please select an HDF array key.")
                return

            try:
                data_obj, file_obj = util.load_hdf(path, hdf_key,
                                                   return_file_obj=True)
                data_ndim = len(data_obj.shape)
                if data_ndim == 1:
                    data = data_obj[:]
                    self.current_table = data
                    win = ren.PlotWindow1D(self.main_win, title=path,
                                           data_y=data,
                                           help_text="HDF-key: " + hdf_key)
                    self._show_window(win)
                    file_obj.close()
                    return
                elif data_ndim == 2:
                    data = data_obj[:]
                    self.current_image = data
                    win = ren.Viewer2DWindow(self,  # Controller as parent
                                             title=f"Viewing: "
                                                   f"{os.path.basename(path)}",
                                             image=data, file_path=path)
                    win.parent_app = self
                    self._show_window(win)
                    self.active_viewer = win
                    file_obj.close()
                    return
                elif data_ndim != 3:
                    QMessageBox.critical(self.main_win, "Can't show data",
                                         f"Only can show 1d, 2d, or 3d data. "
                                         f"Not {data_ndim}d")
                    file_obj.close()
                    return
                file_obj.close()
            except Exception as e:
                QMessageBox.critical(self.main_win, "Can't read file",
                                     f"File: {fname}\nError: {e}")
                return

        try:
            win = ren.InteractiveViewerWindow(self, path, ftype, hdf_key,
                                              list_files)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self.main_win, "Error",
                                 f"Failed to launch: {e}")

    def launch_table_viewer(self):
        items = self.main_win.list_files.selectedItems()
        if not items:
            if self.active_viewer:
                self.save_to_table()
                return
            QMessageBox.information(self.main_win, "Input needed",
                                    "Please select a HDF or CINE file")
            return
        fname = items[0].text()
        full_path = os.path.join(self.selected_folder_path, fname)

        self.current_table = None
        file_obj = None
        try:
            if fname.lower().endswith(util.HDF_EXT):
                hdf_key_path = self.main_win.combo_hdf.currentText().strip()
                if (not hdf_key_path) or (hdf_key_path == "No arrays found"):
                    QMessageBox.information(self.main_win, "Input needed",
                                            "Please select a HDF file and "
                                            "a 1d/2d dataset")
                    return
                data, file_obj = util.load_hdf(full_path, hdf_key_path,
                                               return_file_obj=True)
                win_title = full_path + " <> HDF-key: " + hdf_key_path
            # -----------------------------
            # CINE: timestamps table
            # -----------------------------
            elif fname.lower().endswith(util.CINE_EXT):
                data = util.get_time_stamps_cine(full_path)
                win_title = full_path + " <> Time stamps"
            else:
                QMessageBox.information(self.main_win, "Input needed",
                                        "Please select a HDF file and "
                                        "a 1d/2d dataset")
                return
        except Exception as e:
            if file_obj is not None:
                try:
                    file_obj.close()
                except Exception:
                    pass
            QMessageBox.critical(self.main_win, "Can't read file",
                                 f"File: {fname}\nError: {e}")
            return
        try:
            if hasattr(data, "shape") and (1 in data.shape):
                data = np.squeeze(data)
            if (not hasattr(data, "shape")) or (len(data.shape) not in (1, 2)):
                if fname.lower().endswith(util.HDF_EXT):
                    QMessageBox.information(self.main_win, "Input needed",
                                            "Please select a HDF file and "
                                            "a 1d/2d dataset")
                else:
                    QMessageBox.information(self.main_win, "Invalid Array",
                                            "This function is only for 1D or "
                                            "2D arrays.")
                return
            # Too large -> show as image instead of table
            if data.size > util.TABLE_SIZE_CUTOFF and len(data.shape) == 2:
                info = " !!!Display as image instead table due to size!!!"
                win = ren.Viewer2DWindow(
                    self,
                    title=win_title + info,
                    image=data,
                    file_path=full_path,
                )
                win.parent_app = self
                self._show_window(win)
                self.current_table = None
                return
            win = ren.TableViewerWindow(self.main_win, title=win_title,
                                        data=data)
            self._show_window(win)
            self.current_table = data

        finally:
            if file_obj is not None:
                try:
                    file_obj.close()
                except Exception:
                    pass

    def launch_export(self):
        check = self.check_file_type_in_list()
        if check is None or check == "tif":
            QMessageBox.information(self.main_win, "Input needed",
                                    "Please select a HDF file or a CINE file")
            return

        items = self.main_win.list_files.selectedItems()
        if not items:
            QMessageBox.information(self.main_win, "Input needed",
                                    "Please select a file")
            return

        fname = items[0].text()
        path = os.path.join(self.selected_folder_path, fname)

        ftype = ""
        key = None
        shape = None

        if check == "cine":
            ftype = "cine"
            meta = util.get_metadata_cine(path)
            shape = (meta["TotalImageCount"], meta["biHeight"], meta["biWidth"])
        elif check == "hdf":
            ftype = "hdf"
            key = self.main_win.combo_hdf.currentText().strip()
            if not key or key == "No arrays found":
                QMessageBox.information(self.main_win, "Input needed",
                                        "Please select an HDF array key.")
                return
            try:
                with h5py.File(path, 'r') as f:
                    data = f[key]
                    if len(data.shape) == 2:
                        shape = (1, data.shape[0], data.shape[1])
                    elif len(data.shape) != 3:
                        QMessageBox.critical(self.main_win, "Only for 3d data",
                                             f"Only export 2d/3d data. "
                                             f"Not {len(data.shape)}d")
                        return
                    else:
                        shape = data.shape
            except:
                return

        if ftype:
            win = ren.ExportDialog(self, path, ftype, key, shape)
            self._show_window(win)

    def set_active_viewer(self, viewer):
        self.active_viewer = viewer
        self.main_win.statusBar().showMessage(f"Active: {viewer.windowTitle()}")

    def _get_save_start_path(self, default_ext: str):
        """
        Return a default save path based on the current active viewer file.
        """
        source_path = None

        if self.active_viewer and hasattr(self.active_viewer, "file_path"):
            source_path = self.active_viewer.file_path

        if source_path:
            source_path = os.path.normpath(source_path)

            if os.path.isfile(source_path):
                base_dir = os.path.dirname(source_path)
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                return os.path.join(base_dir, base_name + default_ext)

            if os.path.isdir(source_path):
                return os.path.join(source_path, "output" + default_ext)

        return os.path.join(os.getcwd(), "output" + default_ext)

    def save_to_image(self):
        if self.active_viewer and hasattr(self.active_viewer, 'viewer_state'):
            img = self.active_viewer.viewer_state.get("image")
        elif self.active_viewer and hasattr(self.active_viewer, 'image'):
            img = self.active_viewer.image
        else:
            img = self.current_image
        if img is None:
            QMessageBox.information(self.main_win, "Input needed",
                                    "No active image. Use Interactive-Viewer!")
            return
        default_path = self._get_save_start_path(".tif")
        path, selected_filter = QFileDialog.getSaveFileName(
            self.main_win,
            "Save Image As",
            default_path,
            "TIFF (*.tif);;PNG (*.png);;JPEG (*.jpg)")

        if not path:
            return

        if not os.path.splitext(path)[1]:
            if "PNG" in selected_filter:
                path += ".png"
            elif "JPEG" in selected_filter:
                path += ".jpg"
            else:
                path += ".tif"

        err = util.save_image(path, img)
        if err:
            QMessageBox.critical(self, "Save failed", err)
        else:
            self.main_win.statusBar().showMessage(f"Image saved to: {path}")

    def save_to_table(self):
        if self.active_viewer and hasattr(self.active_viewer, 'viewer_state'):
            data = self.active_viewer.viewer_state.get("table")
            if data is None:
                data = self.current_table
        else:
            data = self.current_table

        if data is None:
            QMessageBox.information(self.main_win, "Input needed",
                                    "No selected data. Use viewers "
                                    "or click image for profile!")
            return

        data = np.asarray(data)
        if data.size > util.MAX_TABLE_SAVE:
            QMessageBox.information(self.main_win, "Array Too Large",
                                    f"Array exceeds maximum save size "
                                    f"({util.MAX_TABLE_SAVE} elements).")
            return

        default_path = self._get_save_start_path(".csv")

        path, _ = QFileDialog.getSaveFileName(self.main_win, "Save Data As",
                                              default_path, "CSV (*.csv)")

        if path:
            if not os.path.splitext(path)[1]:
                path += ".csv"
            err = util.save_table(path, data)
            if err:
                QMessageBox.critical(self, "Save failed", err)
            else:
                self.main_win.statusBar().showMessage(f"Data saved to: {path}")

    def _show_window(self, win):
        self.viewers.append(win)
        win.closed.connect(
            lambda w: self.viewers.remove(w) if w in self.viewers else None)
        win.show()
        return win

    def run(self):
        """Execute the application event loop."""
        self.main_win.show()
        return self.app.exec()
