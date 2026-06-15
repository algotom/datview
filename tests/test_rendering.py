import unittest
import tempfile
import os
import shutil
import sys
import numpy as np
import h5py
from PIL import Image

from PySide6.QtWidgets import QApplication

import datview.lib.rendering as ren
import datview.lib.utilities as util

app = QApplication.instance() or QApplication(sys.argv)


class TestRenderingHelpers(unittest.TestCase):
    def test_select_ui_font(self):
        font = ren.select_ui_font(12)
        self.assertIsNotNone(font)
        self.assertEqual(font.pointSize(), 12)

    def test_calculate_geometry(self):
        rect = ren.calculate_geometry(0.5)
        self.assertIsNotNone(rect)
        self.assertTrue(rect.width() > 0)
        self.assertTrue(rect.height() > 0)


class TestGUIWindows(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_get_config_path = util.get_config_path
        util.get_config_path = lambda: os.path.join(self.temp_dir,
                                                    "test_config.json")

    def tearDown(self):
        util.get_config_path = self.old_get_config_path
        shutil.rmtree(self.temp_dir)

    def test_base_window(self):
        win = ren.BaseWindow(title="Test Base Window")
        self.assertEqual(win.windowTitle(), "Test Base Window")
        win.close()

    def test_plot_window_1d(self):
        data_y = np.array([1, 4, 9, 16])
        win = ren.PlotWindow1D(title="Test Plot Window 1D", data_y=data_y)
        self.assertEqual(win.windowTitle(), "Test Plot Window 1D")
        win.close()

    def test_text_viewer_window(self):
        win = ren.TextViewerWindow(title="Test Text Viewer",
                                   content="Sample Text Content")
        self.assertEqual(win.windowTitle(), "Test Text Viewer")
        self.assertEqual(win.editor.toPlainText(), "Sample Text Content")
        win.close()

    def test_table_viewer_window(self):
        data = np.array([[1, 2], [3, 4]])
        win = ren.TableViewerWindow(title="Test Table Viewer", data=data)
        self.assertEqual(win.windowTitle(), "Test Table Viewer")
        win.close()

    def test_viewer_2d_window(self):
        img = np.zeros((20, 20))
        win = ren.Viewer2DWindow(title="Test 2D Viewer", image=img,
                                 file_path="test.png")
        self.assertEqual(win.windowTitle(), "Test 2D Viewer")
        win.close()

    def test_export_dialog(self):
        # We can construct ExportDialog using mock attributes
        win = ren.ExportDialog(parent_app=None, file_path="dummy.h5",
                               file_type="hdf", hdf_key="data",
                               shape=(10, 20, 30))
        self.assertEqual(win.shape, (10, 20, 30))
        self.assertEqual(win.file_type, "hdf")
        win.close()

    def test_interactive_viewer_window_tif(self):
        # Save a dummy TIF file
        img_path = os.path.join(self.temp_dir, "frame_00000.tif")
        Image.fromarray(np.zeros((10, 10), dtype=np.uint8)).save(img_path)

        win = ren.InteractiveViewerWindow(None, file_path=self.temp_dir,
                                          file_type="tif", hdf_key=None,
                                          list_files=[img_path])
        self.assertEqual(win.file_type, "tif")
        self.assertEqual(win.depth, 1)
        self.assertEqual(win.height, 10)
        self.assertEqual(win.width, 10)
        win.close()

    def test_interactive_viewer_window_hdf(self):
        # Create a dummy HDF5 file with 3D dataset
        hdf_path = os.path.join(self.temp_dir, "test3d.h5")
        with h5py.File(hdf_path, "w") as f:
            f.create_dataset("data3d", data=np.zeros((5, 10, 15)))

        win = ren.InteractiveViewerWindow(None, file_path=hdf_path,
                                          file_type="hdf", hdf_key="data3d")
        self.assertEqual(win.file_type, "hdf")
        self.assertEqual(win.depth, 5)
        self.assertEqual(win.height, 10)
        self.assertEqual(win.width, 15)
        win.close()

    def test_datview_main_window(self):
        win = ren.DatviewMainWindow(base_folder=self.temp_dir)
        self.assertEqual(win.windowTitle(), util.APP_NAME)
        self.assertEqual(str(win.base_folder), os.path.abspath(self.temp_dir))
        win.close()


if __name__ == "__main__":
    unittest.main()
