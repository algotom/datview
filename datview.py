"""
A single Python file for the DatView GUI software, used for folder browsing and
viewing text, image, HDF, and Cine file formats.

Users can copy this file and run it as:
    python datview_mono.py

Dependencies (must be installed before use): h5py, Pillow, matplotlib.
"""
import os
import sys
import csv
import json
import platform
import glob
import gc
import struct
import threading
import signal
import logging
from pathlib import Path
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, filedialog, messagebox
import h5py
import hdf5plugin  # For viewing compressed HDF files
import numpy as np
from PIL import Image
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rc
from matplotlib.widgets import Slider, RadioButtons
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
matplotlib.use("TkAgg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

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
CINE_LOOKUP_TABLE = np.array([
        2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 17, 18, 19, 20, 21,
        22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 33, 34, 35, 36, 37, 38,
        39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 48, 49, 50, 51, 52, 53, 54, 55,
        56, 57, 58, 59, 60, 61, 62, 63, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
        73, 74, 75, 76, 77, 78, 79, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
        90, 91, 92, 93, 94, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
        105, 106, 107, 108, 109, 110, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 125, 126, 127, 128, 129, 130,
        131, 132, 133, 134, 135, 136, 137, 137, 138, 139, 140, 141, 142, 143,
        144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 156, 157, 158,
        159, 160, 161, 162, 163, 164, 165, 167, 168, 169, 170, 171, 172, 173,
        175, 176, 177, 178, 179, 181, 182, 183, 184, 186, 187, 188, 189, 191,
        192, 193, 194, 196, 197, 198, 200, 201, 202, 204, 205, 206, 208, 209,
        210, 212, 213, 215, 216, 217, 219, 220, 222, 223, 225, 226, 227, 229,
        230, 232, 233, 235, 236, 238, 239, 241, 242, 244, 245, 247, 249, 250,
        252, 253, 255, 257, 258, 260, 261, 263, 265, 266, 268, 270, 271, 273,
        275, 276, 278, 280, 281, 283, 285, 287, 288, 290, 292, 294, 295, 297,
        299, 301, 302, 304, 306, 308, 310, 312, 313, 315, 317, 319, 321, 323,
        325, 327, 328, 330, 332, 334, 336, 338, 340, 342, 344, 346, 348, 350,
        352, 354, 356, 358, 360, 362, 364, 366, 368, 370, 372, 374, 377, 379,
        381, 383, 385, 387, 389, 391, 394, 396, 398, 400, 402, 404, 407, 409,
        411, 413, 416, 418, 420, 422, 425, 427, 429, 431, 434, 436, 438, 441,
        443, 445, 448, 450, 452, 455, 457, 459, 462, 464, 467, 469, 472, 474,
        476, 479, 481, 484, 486, 489, 491, 494, 496, 499, 501, 504, 506, 509,
        511, 514, 517, 519, 522, 524, 527, 529, 532, 535, 537, 540, 543, 545,
        548, 551, 553, 556, 559, 561, 564, 567, 570, 572, 575, 578, 581, 583,
        586, 589, 592, 594, 597, 600, 603, 606, 609, 611, 614, 617, 620, 623,
        626, 629, 632, 635, 637, 640, 643, 646, 649, 652, 655, 658, 661, 664,
        667, 670, 673, 676, 679, 682, 685, 688, 691, 694, 698, 701, 704, 707,
        710, 713, 716, 719, 722, 726, 729, 732, 735, 738, 742, 745, 748, 751,
        754, 758, 761, 764, 767, 771, 774, 777, 781, 784, 787, 790, 794, 797,
        800, 804, 807, 811, 814, 817, 821, 824, 828, 831, 834, 838, 841, 845,
        848, 852, 855, 859, 862, 866, 869, 873, 876, 880, 883, 887, 890, 894,
        898, 901, 905, 908, 912, 916, 919, 923, 927, 930, 934, 938, 941, 945,
        949, 952, 956, 960, 964, 967, 971, 975, 979, 982, 986, 990, 994, 998,
        1001, 1005, 1009, 1013, 1017, 1021, 1025, 1028, 1032, 1036, 1040, 1044,
        1048, 1052, 1056, 1060, 1064, 1068, 1072, 1076, 1080, 1084, 1088, 1092,
        1096, 1100, 1104, 1108, 1112, 1116, 1120, 1124, 1128, 1132, 1137, 1141,
        1145, 1149, 1153, 1157, 1162, 1166, 1170, 1174, 1178, 1183, 1187, 1191,
        1195, 1200, 1204, 1208, 1212, 1217, 1221, 1225, 1230, 1234, 1238, 1243,
        1247, 1251, 1256,
        1260, 1264, 1269, 1273, 1278, 1282, 1287, 1291, 1295, 1300, 1304, 1309,
        1313, 1318, 1322, 1327, 1331, 1336, 1340, 1345, 1350, 1354, 1359, 1363,
        1368, 1372, 1377, 1382, 1386, 1391, 1396, 1400, 1405, 1410, 1414, 1419,
        1424, 1428, 1433, 1438, 1443, 1447, 1452, 1457, 1462, 1466, 1471, 1476,
        1481, 1486, 1490, 1495, 1500, 1505, 1510, 1515, 1520, 1524, 1529, 1534,
        1539, 1544, 1549, 1554, 1559, 1564, 1569, 1574, 1579, 1584, 1589, 1594,
        1599, 1604, 1609, 1614, 1619, 1624, 1629, 1634, 1639, 1644, 1649, 1655,
        1660, 1665, 1670, 1675, 1680, 1685, 1691, 1696, 1701, 1706, 1711, 1717,
        1722, 1727, 1732, 1738, 1743, 1748, 1753, 1759, 1764, 1769, 1775, 1780,
        1785, 1791, 1796, 1801, 1807, 1812, 1818, 1823, 1828, 1834, 1839, 1845,
        1850, 1856, 1861, 1867, 1872, 1878, 1883, 1889, 1894, 1900, 1905, 1911,
        1916, 1922, 1927, 1933, 1939, 1944, 1950, 1956, 1961, 1967, 1972, 1978,
        1984, 1989, 1995, 2001, 2007, 2012, 2018, 2024, 2030, 2035, 2041, 2047,
        2053, 2058, 2064, 2070, 2076, 2082, 2087, 2093, 2099, 2105, 2111, 2117,
        2123, 2129, 2135, 2140, 2146, 2152, 2158, 2164, 2170, 2176, 2182, 2188,
        2194, 2200, 2206, 2212, 2218, 2224, 2231, 2237, 2243, 2249, 2255, 2261,
        2267, 2273, 2279, 2286, 2292, 2298, 2304, 2310, 2317, 2323, 2329, 2335,
        2341, 2348, 2354, 2360, 2366, 2373, 2379, 2385, 2392, 2398, 2404, 2411,
        2417, 2423, 2430, 2436, 2443, 2449, 2455, 2462, 2468, 2475, 2481, 2488,
        2494, 2501, 2507, 2514, 2520, 2527, 2533, 2540, 2546, 2553, 2559, 2566,
        2572, 2579, 2586, 2592, 2599, 2605, 2612, 2619, 2625, 2632, 2639, 2645,
        2652, 2659, 2666, 2672, 2679, 2686, 2693, 2699, 2706, 2713, 2720, 2726,
        2733, 2740, 2747, 2754, 2761, 2767, 2774, 2781, 2788, 2795, 2802, 2809,
        2816, 2823, 2830, 2837, 2844, 2850, 2857, 2864, 2871, 2878, 2885, 2893,
        2900, 2907, 2914, 2921, 2928, 2935, 2942, 2949, 2956, 2963, 2970, 2978,
        2985, 2992, 2999, 3006, 3013, 3021, 3028, 3035, 3042, 3049, 3057, 3064,
        3071, 3078, 3086, 3093, 3100, 3108, 3115, 3122, 3130, 3137, 3144, 3152,
        3159, 3166, 3174, 3181, 3189, 3196, 3204, 3211, 3218, 3226, 3233, 3241,
        3248, 3256, 3263, 3271, 3278, 3286, 3294, 3301, 3309, 3316, 3324, 3331,
        3339, 3347, 3354, 3362, 3370, 3377, 3385, 3393, 3400, 3408, 3416, 3423,
        3431, 3439, 3447, 3454, 3462, 3470, 3478, 3486, 3493, 3501, 3509, 3517,
        3525, 3533, 3540, 3548, 3556, 3564, 3572, 3580, 3588, 3596, 3604, 3612,
        3620, 3628, 3636, 3644, 3652, 3660, 3668, 3676, 3684, 3692, 3700, 3708,
        3716, 3724, 3732, 3740, 3749, 3757, 3765, 3773, 3781, 3789, 3798, 3806,
        3814, 3822, 3830, 3839, 3847, 3855, 3863, 3872, 3880, 3888, 3897, 3905,
        3913, 3922, 3930, 3938, 3947, 3955, 3963, 3972, 3980, 3989, 3997, 4006,
        4014, 4022, 4031, 4039, 4048, 4056, 4064, 4095, 4095, 4095, 4095, 4095,
        4095, 4095, 4095, 4095])

# ==============================================================================
#                          Utility methods
# ==============================================================================


def load_image(file_path, average=False):
    """Load an image and convert it to a 2D/3D array"""
    file_path = os.path.normpath(file_path)
    try:
        mat = np.array(Image.open(file_path), dtype=np.float32)
    except Exception as e:
        raise ValueError(f"File reading error: {e}")
    if len(mat.shape) > 2 and average is True:
        axis_m = np.argmin(mat.shape)
        mat = np.mean(mat, axis=axis_m)
    return mat


def load_hdf(file_path, key_path, return_file_obj=False):
    """Load a dataset from a hdf file"""
    try:
        hdf_object = h5py.File(file_path, "r")
    except IOError:
        raise ValueError("Couldn't open file: {}".format(file_path))
    check = key_path in hdf_object
    if not check:
        raise ValueError(
            "Couldn't open object with the given key: {}".format(key_path))
    if return_file_obj:
        return hdf_object[key_path], hdf_object
    else:
        return hdf_object[key_path]


def get_hdf_data(file_path, dataset_path):
    """Get data type and value of a dataset in a hdf file"""
    with h5py.File(file_path, "r") as file:
        if dataset_path not in file:
            return "not path", None
        try:
            item = file[dataset_path]
            if isinstance(item, h5py.Group):
                return "group", None
            data_type, value = "unknown", None
            # Check the type and shape of a dataset
            if item.dtype.kind == "S":  # Fixed-length bytes
                data = item[()]
                if item.size == 1:  # Single string or byte
                    if isinstance(data, bytes):
                        data_type, value = "string", data.decode("utf-8")
                    elif isinstance(data.flat[0], bytes):
                        data_type = "string"
                        value = data.flat[0].decode("utf-8")
                else:
                    data_type = "array"
                    value = [d.decode("utf-8") for d in data]
            elif item.dtype.kind == "U":  # Fixed-length Unicode
                data = item[()]
                if item.size == 1:  # Single string
                    data_type, value = "string", data
                else:
                    data_type, value = "array", list(data)
            elif h5py.check_dtype(vlen=item.dtype) in [str, bytes]:
                data = item[()]
                if isinstance(data, (str, bytes)):
                    data_type = "string"
                    value = data if isinstance(data, str) else data.decode(
                        "utf-8")
                else:
                    joined_data = ''.join(
                        [d if isinstance(d, str) else d.decode("utf-8") for d
                         in data])
                    data_type, value = "string", joined_data
            elif item.dtype.kind in ["i", "f", "u"]:
                if item.shape == () or item.size == 1:
                    data_type, value = "number", item[()]
                else:
                    data_type, value = "array", item.shape
            elif item.dtype.kind == "b":  # Boolean type
                data_type, value = "boolean", int(item[()])
            return data_type, value
        except Exception as error:
            return str(error), None


def find_file(path):
    """Find files matching a given pattern"""
    file_path = glob.glob(path)
    if len(file_path) == 0:
        raise ValueError("!!! No files found in: {}".format(path))
    for i in range(len(file_path)):
        file_path[i] = os.path.normpath(file_path[i])
    return sorted(file_path)


def is_text_file(file_path, num_bytes=1024):
    """Check if a file is a valid text file by trying to read its content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(num_bytes)
        return True
    except (OSError, UnicodeDecodeError, FileNotFoundError):
        return False


def get_metadata_cine(cine_path):
    """
    Reads metadata from a Phantom .cine file and returns it as a dictionary.
    """
    with open(cine_path, "rb") as cinefile:
        header_length = 44
        bitmap_header_length = 40
        cinefile.seek(0)
        hdr = struct.unpack('<2s3HiIi6I', cinefile.read(header_length))
        metadata = {
            "Headersize": hdr[1],
            "Compression": hdr[2],
            "Version": hdr[3],
            "TotalImageCount": hdr[5],
            "ImageCount": hdr[7],
            "OffImageHeader": hdr[8],
            "OffSetup": hdr[9],
            "OffImageOffsets": hdr[10],
            "TriggerTime": (hdr[11], hdr[12])
        }
        bmp = struct.unpack('<I2i2H2I2i2I', cinefile.read(bitmap_header_length))
        metadata.update({
            "biWidth": bmp[1],
            "biHeight": bmp[2],
            "biBitCount": bmp[4],
            "biCompression": bmp[5]
        })
        return metadata


def __unpack_10bit_cine(data, width, height):
    """Unpacks 10-bit packed images into 16-bit."""
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")
    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111) << 4) | (
                packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111) << 6) | (
                packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]
    return CINE_LOOKUP_TABLE[unpacked].astype(np.uint16)


def __unpack_12bit_cine(data, width, height):
    """Unpacks 12-bit packed images into 16-bit."""
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")
    unpacked.flat[::2] = (packed[::3] << 4) | packed[1::3] >> 4
    unpacked.flat[1::2] = ((packed[1::3] & 0b00001111) << 8) | packed[2::3]
    return unpacked


def __create_raw_array_cine(data, metadata):
    """Convert raw image data into a numpy array"""
    width, height = metadata["biWidth"], metadata["biHeight"]
    if metadata["biCompression"] == 0:  # Uncompressed
        dtype = np.uint8 if metadata["biBitCount"] == 8 else np.uint16
        raw_image = np.frombuffer(data, dtype=dtype).reshape((height, width))
    elif metadata["biCompression"] == 256:  # 10-bit compressed
        raw_image = __unpack_10bit_cine(data, width, height)
    elif metadata["biCompression"] == 1024:  # 12-bit compressed
        raw_image = __unpack_12bit_cine(data, width, height)
    else:
        raise ValueError("Unsupported biCompression format")
    return raw_image


def extract_frame_cine(cine_path, frame_index):
    """
    Extract a specific frame from the .cine file.
    Code adapted from https://github.com/ottomatic-io/pycine.git
    """
    metadata = get_metadata_cine(cine_path)
    with open(cine_path, "rb") as cinefile:
        width, height = metadata["biWidth"], metadata["biHeight"]
        total_frames = metadata["TotalImageCount"]
        if frame_index < 0 or frame_index >= total_frames:
            raise ValueError(f"Frame index {frame_index} is out of "
                             f"range (0-{total_frames - 1})")
        cinefile.seek(metadata["OffImageOffsets"])
        pointer_array = struct.unpack(f"<{total_frames}Q",
                                      cinefile.read(total_frames * 8))
        cinefile.seek(pointer_array[frame_index])
        annotation_size = struct.unpack('<I', cinefile.read(4))[0]
        string_size = annotation_size - 8
        image_size = struct.unpack(f"<{string_size}s I",
                                   cinefile.read(annotation_size - 4))[1]
        image_data = cinefile.read(image_size)
        return __create_raw_array_cine(image_data, metadata)


def get_time_stamps_cine(cine_path):
    """
    Return a list of frame timestamps (in milliseconds), compared to the first
    frame, extracted from a .cine file.
    Code adapted from https://github.com/soft-matter/pims.git
    """
    fraction_mask = 0xFFFFFFFF
    with open(cine_path, 'rb') as f:
        hdr = f.read(44)
        header = struct.unpack('<2s3HiIi6I', hdr)
        off_setup = header[9]
        off_img_offsets = header[10]
        f.read(40)
        f.seek(off_setup)
        setup_block = f.read(144)
        setup_length = struct.unpack("<H", setup_block[-2:])[0]
        tagged_start = off_setup + setup_length
        timestamps = []
        offset = 0
        while tagged_start + offset < off_img_offsets:
            f.seek(tagged_start + offset)
            block_header = f.read(8)
            if len(block_header) < 8:
                break
            block_size, tag_type, _ = struct.unpack("<IHH", block_header)
            if tag_type in (1001, 1002):
                data = f.read(block_size - 8)
                count = (block_size - 8) // 8
                for v in struct.unpack("<" + "Q" * count, data):
                    t_sec = v >> 32
                    t_frac = (v & fraction_mask) / 2 ** 32
                    timestamps.append((t_sec + t_frac) * 1000.0)
            else:
                f.seek(block_size - 8, 1)
            offset += block_size
        timestamps = np.asarray(timestamps)
        return timestamps - timestamps[0]


def save_image(file_path, mat):
    """Save 2D array to an image (tif, jpg, png,...)"""
    file_ext = os.path.splitext(file_path)[-1]
    if not ((file_ext == ".tif") or (file_ext == ".tiff")):
        mat = np.uint8(
            255.0 * (mat - np.min(mat)) / (np.max(mat) - np.min(mat)))
    else:
        if mat.dtype != np.float32:
            mat = mat.astype(np.float32)
    image = Image.fromarray(mat)
    try:
        image.save(file_path)
    except Exception as error:
        return str(error)


def save_table(file_path, data):
    """Save data to a table format, csv"""
    try:
        data = np.asarray(data)
        with open(file_path, "w", newline='') as file:
            writer = csv.writer(file)
            if data.ndim == 1:
                for item in data:
                    writer.writerow([item])
            elif data.ndim == 2:
                if data.shape[0] * data.shape[1] < 4000000:
                    writer.writerows(data)
                else:
                    return "Array has more than 4,000,000 elements. " \
                           "Operation not performed."
            else:
                return "Data must be a 1D or 2D array"
    except Exception as error:
        return str(error)


def save_config(data):
    """
    Save data (dictionary) to the config file (json format).
    """
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f)


def get_config_path():
    """
    Get path to save a config file depending on the OS system.
    """
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        return os.path.join(home, "AppData", "Roaming", "DatView",
                            "data_viewer_config.json")
    elif platform.system() == "Darwin":
        return os.path.join(home, "Library", "Application Support", "DatView",
                            "data_viewer_config.json")
    else:
        return os.path.join(home, ".data_viewer", "data_viewer_config.json")


def load_config():
    """
    Load the config file.
    """
    config_path = get_config_path()
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# ==============================================================================
#                          GUI Rendering
# ==============================================================================


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
            icon = tk.PhotoImage(file="./datview_icon.png")
            self.iconphoto(True, icon)
        except tk.TclError:
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
                metadata = get_metadata_cine(file_path)
                formatted_metadata = json.dumps(metadata, indent=4)
                text_area.insert(tk.END, formatted_metadata)
            else:
                with open(file_path, "r") as file:
                    content = file.read()
                text_area.insert(tk.END, content)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the file: {e}")

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
            list_files = find_file(file_path + "/*tif*")
            if not list_files:
                messagebox.showerror("No Files",
                                     f"No TIF files found in: {file_path}")
                return
            img = load_image(list_files[0])
            (height, width) = img.shape
            depth = len(list_files)
            current_path = file_path

        elif file_type == "cine":
            cine_metadata = get_metadata_cine(file_path)
            width = cine_metadata["biWidth"]
            height = cine_metadata["biHeight"]
            depth = cine_metadata["TotalImageCount"]
            img = extract_frame_cine(file_path, 0)
            current_path = file_path

        else:  # HDF5
            selected_index = self.file_list_view.curselection()
            selected_file = self.file_list_view.get(selected_index[0])
            full_path = os.path.join(self.selected_folder_path, selected_file)
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data = load_hdf(full_path, hdf_key_path)
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
                    img = load_image(list_files[index])
                    message_text_var.set(list_files[index])
                elif file_type == "cine":
                    img = extract_frame_cine(file_path, index)
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


# ==============================================================================
#                          GUI Interactions
# ==============================================================================


class DatviewInteraction(DatviewRendering):
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

        rc("font", size=PLT_MAIN_FONTSIZE)
        rc("axes", titlesize=PLT_MAIN_FONTSIZE)
        rc("axes", labelsize=PLT_MAIN_FONTSIZE)
        rc("xtick", labelsize=PLT_MAIN_FONTSIZE)
        rc("ytick", labelsize=PLT_MAIN_FONTSIZE)

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
            save_config(config_data)

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
                    data_type, value = get_hdf_data(file_path,
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
        if selected_file.endswith(HDF_EXT):
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
            img = load_image(file_path)
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
                TEXT_WIN_RATIO)
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
                data_type, value = get_hdf_data(file_path, hdf_path)
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
        if selected_file.endswith(TEXT_EXT) or selected_file.endswith(CINE_EXT):
            self.display_text_file(full_path)
        elif selected_file.endswith(IMAGE_EXT):
            self.display_image_file(full_path)
        elif selected_file.endswith(HDF_EXT):
            self.display_hdf_file(full_path)
        else:
            if is_text_file(full_path):
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
        elif file_name.lower().endswith(HDF_EXT):
            return "hdf"
        elif file_name.lower().endswith(CINE_EXT):
            return "cine"
        return None

    def launch_table_viewer(self, event):
        selected_index = self.file_list_view.curselection()
        if len(selected_index) == 0:
            messagebox.showinfo("Input needed", "Please select a file")
            return
        selected_file = self.file_list_view.get(selected_index[0])
        full_path = os.path.join(self.selected_folder_path, selected_file)
        if selected_file.lower().endswith(HDF_EXT):
            hdf_key_path = self.hdf_key_list.get().strip()
            try:
                data = load_hdf(full_path, hdf_key_path)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(IMAGE_EXT):
            try:
                data = load_image(full_path, average=True)
            except Exception as e:
                messagebox.showerror("Can't read file",
                                     f"File: {selected_file}\nError: {e}")
                return
        elif selected_file.lower().endswith(CINE_EXT):
            data = get_time_stamps_cine(full_path)
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

            save_image(file_path, self.current_image)
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
            save_table(file_path, self.current_table)
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


def main():
    if len(sys.argv) > 1:
        base_folder = os.path.abspath(sys.argv[1])
    else:
        config_data = load_config()
        if config_data is None:
            base_folder = "."
        else:
            try:
                base_folder = config_data["last_folder"]
            except KeyError:
                base_folder = "."
        base_folder = os.path.abspath(base_folder)
    app = DatviewInteraction(base_folder)
    app.mainloop()


if __name__ == "__main__":
    main()
