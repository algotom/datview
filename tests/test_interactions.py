import unittest
import tempfile
import os
import shutil
import sys
import numpy as np
import h5py

from PySide6.QtWidgets import QApplication, QListWidgetItem

from datview.lib.interactions import DatviewInteraction
import datview.lib.rendering as ren
import datview.lib.utilities as util

app = QApplication.instance() or QApplication(sys.argv)


class TestDatviewInteraction(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_get_config_path = util.get_config_path
        util.get_config_path = lambda: os.path.join(self.temp_dir,
                                                    "test_config.json")

        # Save a basic config
        util.save_config({"last_folder": self.temp_dir, "theme": "Light"})

    def tearDown(self):
        util.get_config_path = self.old_get_config_path
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        controller = DatviewInteraction(base_folder=self.temp_dir)
        self.assertIsNotNone(controller.main_win)
        # base_folder is a Path object; compare as strings
        self.assertEqual(str(controller.base_folder),
                         os.path.abspath(self.temp_dir))
        self.assertEqual(len(controller.viewers), 0)
        controller.main_win.close()

    def test_check_file_type_in_list_empty(self):
        controller = DatviewInteraction(base_folder=self.temp_dir)
        self.assertIsNone(controller.check_file_type_in_list())
        controller.main_win.close()

    def test_check_file_type_in_list_with_selection(self):
        controller = DatviewInteraction(base_folder=self.temp_dir)

        # Mocking file list addition and selection
        item_tif = QListWidgetItem("test_image.tif")
        controller.main_win.list_files.addItem(item_tif)
        controller.main_win.list_files.setCurrentItem(item_tif)
        self.assertEqual(controller.check_file_type_in_list(), "tif")

        item_hdf = QListWidgetItem("test_data.nxs")
        controller.main_win.list_files.addItem(item_hdf)
        controller.main_win.list_files.setCurrentItem(item_hdf)
        self.assertEqual(controller.check_file_type_in_list(), "hdf")

        item_cine = QListWidgetItem("test_video.cine")
        controller.main_win.list_files.addItem(item_cine)
        controller.main_win.list_files.setCurrentItem(item_cine)
        self.assertEqual(controller.check_file_type_in_list(), "cine")

        controller.main_win.close()

    def test_populate_hdf_keys(self):
        # Create a dummy HDF5 file
        hdf_path = os.path.join(self.temp_dir, "keys_test.h5")
        with h5py.File(hdf_path, "w") as f:
            f.create_dataset("group1/array3d", data=np.zeros((2, 2, 2)))
            f.create_dataset("array2d", data=np.zeros((5, 5)))
            f.create_dataset("string_val", data="hello")

        controller = DatviewInteraction(base_folder=self.temp_dir)
        controller.populate_hdf_keys(hdf_path)

        combo = controller.main_win.combo_hdf
        self.assertTrue(combo.isEnabled())

        # Verify the array datasets are listed in the combo box
        items = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn("group1/array3d", items)
        self.assertIn("array2d", items)
        # Verify non-array string datasets are ignored
        self.assertNotIn("string_val", items)

        controller.main_win.close()

    def test_on_theme_changed(self):
        controller = DatviewInteraction(base_folder=self.temp_dir)

        # Switch to Dark theme
        controller.on_theme_changed("Dark")
        self.assertEqual(ren.sel_theme["BG"], "#1a1d23")

        # Check config persistence
        cfg = util.load_config()
        self.assertEqual(cfg["theme"], "Dark")

        # Switch back to Light theme
        controller.on_theme_changed("Light")
        self.assertEqual(ren.sel_theme["BG"], "#f4f6f9")

        controller.main_win.close()


if __name__ == "__main__":
    unittest.main()
