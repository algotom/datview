import unittest
import tempfile
import os
import shutil
import numpy as np
import h5py
from PIL import Image

import datview.lib.utilities as util


class TestFormatBytes(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(util.format_bytes(100), "100 B")
        self.assertEqual(util.format_bytes(1024), "1.00 KB")
        self.assertEqual(util.format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(util.format_bytes(1024 * 1024 * 1024), "1.00 GB")


class TestIsTextFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_is_text_file_with_valid_text(self):
        path = os.path.join(self.temp_dir, "test.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Hello World, this is a plain text file.")
        self.assertTrue(util.is_text_file(path))

    def test_is_text_file_with_binary_data(self):
        path = os.path.join(self.temp_dir, "test.bin")
        with open(path, "wb") as f:
            f.write(bytes([0, 1, 2, 3, 255, 0, 12, 19]))
        self.assertFalse(util.is_text_file(path))


class TestImageStatistics(unittest.TestCase):
    def test_get_image_statistics(self):
        mat = np.array([[10.0, 20.0], [30.0, 40.0]])
        stats = util.get_image_statistics(mat)
        self.assertIsNotNone(stats)
        self.assertEqual(stats["Minimum"], 10.0)
        self.assertEqual(stats["Maximum"], 40.0)
        self.assertEqual(stats["Mean"], 25.0)
        self.assertEqual(stats["Median"], 25.0)

    def test_empty_image(self):
        stats = util.get_image_statistics(np.array([]))
        self.assertIsNone(stats)


class TestPercentileDensity(unittest.TestCase):
    def test_get_percentile_density(self):
        mat = np.linspace(1, 100, 1000)
        percentiles, density = util.get_percentile_density(mat)
        self.assertEqual(len(percentiles), len(density))
        self.assertTrue(np.any(density > 0))


class TestRescaling(unittest.TestCase):
    def test_apply_rescaling_8bit(self):
        mat = np.array([0.0, 0.5, 1.0])
        rescaled = util.apply_rescaling(mat, nbit=8, minmax=(0.0, 1.0))
        np.testing.assert_array_equal(rescaled, [0, 127, 255])

    def test_apply_rescaling_16bit(self):
        mat = np.array([0.0, 1.0])
        rescaled = util.apply_rescaling(mat, nbit=16, minmax=(0.0, 1.0))
        np.testing.assert_array_equal(rescaled, [0, 65535])

    def test_invalid_nbit(self):
        with self.assertRaises(ValueError):
            util.apply_rescaling(np.array([1, 2]), nbit=12)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_get_config_path = util.get_config_path
        # Force config path into the temp directory
        util.get_config_path = lambda: os.path.join(self.temp_dir,
                                                    "test_config.json")

    def tearDown(self):
        util.get_config_path = self.old_get_config_path
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_config(self):
        # Starts empty
        self.assertIsNone(util.load_config())
        test_data = {"last_folder": "/path/to/folder", "theme": "Dark"}
        util.save_config(test_data)
        loaded = util.load_config()
        self.assertEqual(loaded, test_data)


class TestFindFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_file(self):
        # Create some files
        open(os.path.join(self.temp_dir, "img1.tif"), "w").close()
        open(os.path.join(self.temp_dir, "img2.png"), "w").close()
        open(os.path.join(self.temp_dir, "notes.txt"), "w").close()

        files = util.find_file(self.temp_dir, valid_exts=[".tif", ".png"])
        self.assertEqual(len(files), 2)
        basenames = [os.path.basename(f) for f in files]
        self.assertIn("img1.tif", basenames)
        self.assertIn("img2.png", basenames)


class TestHDFUtilities(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.hdf_path = os.path.join(self.temp_dir, "test.h5")
        with h5py.File(self.hdf_path, "w") as f:
            f.create_dataset("string_dataset", data="test_string")
            f.create_dataset("numeric_dataset", data=42)
            f.create_dataset("array_dataset", data=np.array([1, 2, 3]))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_hdf(self):
        dataset = util.load_hdf(self.hdf_path, "array_dataset")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.shape, (3,))

    def test_get_hdf_data_string(self):
        dtype, value = util.get_hdf_data(self.hdf_path, "string_dataset")
        self.assertEqual(dtype, "string")
        self.assertEqual(value, "test_string")

    def test_get_hdf_data_number(self):
        dtype, value = util.get_hdf_data(self.hdf_path, "numeric_dataset")
        self.assertEqual(dtype, "number")
        self.assertEqual(value, 42)

    def test_get_hdf_data_array(self):
        dtype, value = util.get_hdf_data(self.hdf_path, "array_dataset")
        self.assertEqual(dtype, "array")
        self.assertEqual(value, (3,))


if __name__ == "__main__":
    unittest.main()
