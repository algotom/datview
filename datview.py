"""
A single Python file for the DatView GUI software, used for folder browsing and
viewing text, image, HDF, and Cine file formats.

Users can copy this file and run it as:
    python datview.py

Dependencies: h5py, Pillow, matplotlib. Optional: hdf5plugin
"""
import os
import csv
import json
import platform
import gc
import struct
import signal
import logging
import argparse
import threading
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
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
matplotlib.use("TkAgg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

FONT_SIZE = 12
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


def find_file(folder_path):
    """
    Fast directory scanning using os.scandir.
    Returns sorted full paths of image files.
    """
    valid_exts = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
    files = []
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file() and os.path.splitext(entry.name)[
                    1].lower() in valid_exts:
                    files.append(entry.path)
    except OSError:
        return []
    return sorted(files)


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
        # width, height = metadata["biWidth"], metadata["biHeight"]
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
        data_type = str(mat.dtype)
        if "complex" in data_type:
            raise ValueError(f"Can't save to tiff with format: {data_type}")
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


def get_image_statistics(mat):
    """Calculates a standard set of statistics for a given image"""
    if mat is None or mat.size == 0:
        return None
    flat_data = mat.ravel()
    stats_data = {
        "Minimum": np.min(flat_data),
        "Maximum": np.max(flat_data),
        "Mean": np.mean(flat_data),
        "Median": np.median(flat_data),
        "Std. Deviation": np.std(flat_data),
    }
    percentiles = [1, 5, 95, 99]
    percentile_values = np.percentile(flat_data, percentiles)
    stats_data["1st Percentile"] = percentile_values[0]
    stats_data["5th Percentile"] = percentile_values[1]
    stats_data["95th Percentile"] = percentile_values[2]
    stats_data["99th Percentile"] = percentile_values[3]
    return stats_data


def get_percentile_density(mat):
    """
    Compute a percentile-based histogram normalized by bin width.
    Bin widths are calculated using the percentile.

    Returns
    -------
    percentiles : array-like
        Percentile values for the valid bins (after dropping zero-width bins).
    density : array-like
        Normalized density (sum = 1).
    """
    mat = np.asarray(mat).ravel()
    npoint = mat.size
    if npoint == 0:
        raise ValueError("Input data is empty.")
    # Compute percentile-based bin edges
    num_bin = 101
    percentiles = np.linspace(0, 100, num_bin)
    bin_edges = np.percentile(mat, percentiles)
    # Compute histogram counts
    counts, _ = np.histogram(mat, bins=bin_edges)
    bin_widths = np.diff(bin_edges)
    valid = bin_widths > 0
    counts = counts[valid]
    bin_widths = bin_widths[valid]
    percentiles = percentiles[0:num_bin - 1] + 0.5
    percentiles = percentiles[valid]
    density = counts / (npoint * bin_widths)
    # Normalize by sum(density)
    if np.any(density > 0):
        density = density / np.sum(density)
    return percentiles, density


def apply_rescaling(mat, nbit=16, minmax=None):
    """
    Rescale a 32-bit array to 16-bit/8-bit data.
    """
    if nbit != 8 and nbit != 16:
        raise ValueError("Only two options for nbit: 8 or 16 !!!")
    if minmax is None:
        gmin, gmax = np.min(mat), np.max(mat)
    else:
        (gmin, gmax) = minmax
    if gmax > gmin:
        mat = np.clip(mat, gmin, gmax)
        mat = (mat - gmin) / (gmax - gmin)
    if nbit == 8:
        mat = np.uint8(np.clip(mat * 255, 0, 255))
    else:
        mat = np.uint16(np.clip(mat * 65535, 0, 65535))
    return mat


def _get_cropped_slice(file_type, data_obj, index, axis, crop_rect):
    """
    Internal helper to extract a single, cropped 2D slice.
    data_obj is either a CINE file path or an open HDF5 dataset.
    crop_rect is (y_start, y_stop, x_start, x_stop)
    """
    y_start, y_stop, x_start, x_stop = crop_rect
    try:
        if file_type == "cine":
            mat = extract_frame_cine(data_obj, index)
            mat_cropped = mat[y_start:y_stop, x_start:x_stop]
        else:
            if axis == 0:
                mat_cropped = data_obj[0][index, y_start:y_stop, x_start:x_stop]
            else:
                mat_cropped = data_obj[0][y_start:y_stop, index, x_start:x_stop]
        if mat_cropped.size == 0:
            raise ValueError("Crop parameters result in an empty image.")
        return mat_cropped
    except (IndexError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to crop slice at index {index}. "
                         f"Check crop parameters. Error: {e}")
    except Exception as e:
        raise IOError(f"Failed to read data for slice {index}. Error: {e}")


def export_hdf_cine_to_tif(parameters_dict, status_callback=None):
    """
    Export to tif from hdf/cine file given a parameters dictionary.
    Includes an optional status_callback function to report progress.
    """

    def _report_status(message):
        if status_callback:
            status_callback(message)

    try:
        output_path = parameters_dict["output_path"]
        input_path = parameters_dict["input_path"]
        prefix = parameters_dict["prefix"]
        axis = parameters_dict["axis"]
        slice_start = parameters_dict["slice_start"]
        slice_stop = parameters_dict["slice_stop"]
        slice_step = parameters_dict["slice_step"]
        y_start = parameters_dict["y_start"]
        y_stop = parameters_dict["y_stop"]
        x_start = parameters_dict["x_start"]
        x_stop = parameters_dict["x_stop"]
        rescale = parameters_dict["rescale"]
        min_percent = parameters_dict["min_percent"]
        max_percent = parameters_dict["max_percent"]
        slice_skip = parameters_dict["slice_skip"]
        hdf_key = parameters_dict.get("hdf_key")
    except KeyError as e:
        raise ValueError(f"Missing required parameter: {e}")
    _report_status("Parameters validated...")
    hdf_ext = (".nxs", "nx", ".h5", ".hdf", ".hdf5")
    file_name = os.path.basename(input_path)
    if file_name.lower().endswith(hdf_ext):
        file_type = "hdf"
        if hdf_key is None:
            raise ValueError("HDF file selected, but no HDF key was provided.")
    elif file_name.lower().endswith("cine"):
        file_type = "cine"
    else:
        raise ValueError(f"Invalid file type: {file_name}")
    crop_rect = (y_start, y_stop, x_start, x_stop)
    slice_indices = range(slice_start, slice_stop, slice_step)
    if len(slice_indices) == 0:
        raise ValueError(
            "Slice Start, Stop, and Step result in 0 images to export.")
    total_images = len(slice_indices)
    gmin, gmax = None, None
    if rescale in ("8-bit", "16-bit"):
        _report_status("Starting sampling pass...")
        gmin_list = []
        gmax_list = []
        sample_step = max(slice_skip, slice_step)
        sample_indices = range(slice_start, slice_stop, sample_step)

        if len(sample_indices) == 0:
            raise ValueError("Sampling step or slice step is too large, "
                             "resulting in 0 samples.")
        data_obj = None
        try:
            if file_type == "hdf":
                data_obj = load_hdf(input_path, hdf_key, return_file_obj=True)
                if data_obj is None:
                    raise ValueError(f"Could not load HDF dataset: {hdf_key}")
            else:
                data_obj = input_path
            for i_sample, i in enumerate(sample_indices):
                if i_sample % 10 == 0:
                    _report_status(f"Sampling slice "
                                   f"{i_sample + 1}/{len(sample_indices)}...")
                mat_sample = _get_cropped_slice(file_type, data_obj, i, axis,
                                                crop_rect)
                if mat_sample is not None:
                    gmin_list.append(np.percentile(mat_sample, min_percent))
                    gmax_list.append(np.percentile(mat_sample, max_percent))
        finally:
            if file_type == "hdf" and data_obj is not None:
                data_obj[-1].close()
        if not gmin_list or not gmax_list:
            raise ValueError("Failed to gather samples. "
                             "Check slice/crop parameters.")
        gmax = np.max(np.asarray(gmax_list))
        gmin = np.min(np.asarray(gmin_list))
        _report_status(f"Sampling complete. Global min={gmin}, max={gmax}")
    _report_status(f"Starting export for {total_images} images...")
    data_obj = None
    try:
        if file_type == "hdf":
            data_obj = load_hdf(input_path, hdf_key, return_file_obj=True)
            if data_obj is None:
                raise ValueError(f"Could not load HDF dataset: {hdf_key}")
        else:
            data_obj = input_path
        for i_export, i in enumerate(slice_indices):
            mat_out = _get_cropped_slice(file_type, data_obj, i, axis,
                                         crop_rect)
            if gmin is not None and gmax is not None:
                if rescale == "8-bit":
                    mat_out = apply_rescaling(mat_out, nbit=8,
                                              minmax=(gmin, gmax))
                elif rescale == "16-bit":
                    mat_out = apply_rescaling(mat_out, nbit=16,
                                              minmax=(gmin, gmax))
            file_name = f"{prefix}_{i:05}.tif"
            save_path = os.path.join(output_path, file_name)
            save_image(save_path, mat_out)
            if (i_export + 1) % 10 == 0 or (i_export + 1) == total_images:
                _report_status(
                    f"Exported image {i_export + 1}/{total_images}...")
    finally:
        if file_type == "hdf" and data_obj is not None:
            data_obj[-1].close()
    _report_status("Export complete.")
    return "Success"


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
        # Export-to-tif button
        self.export_tif_button = ttk.Button(viewer_saver_frame, width=20,
                                            text="Export to tif")
        self.export_tif_button.grid(row=1, column=2, sticky="w", padx=5,
                                    pady=(0, 5))
        ttip_export_tif_button = "Export 3d-array HDF/CINE dataset to TIF files"
        ToolTip(self.export_tif_button, ttip_export_tif_button)
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

    def show_1d_data(self, array_1d, help_text="", title=""):
        """Display a graph of 1d data."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
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
                                        (height / dpi) * PLT_1D_RATIO), dpi=dpi)
        ax.plot(array_1d, color="blue", linewidth=1.0)
        ax.set_aspect("auto")
        if len(help_text) > 0:
            ax.set_title(help_text)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def table_viewer(self, data, title="Array Table Viewer"):
        """Display 1d or 2d-data as table format"""
        window = tk.Toplevel(self)
        window.title(title)
        width, height, x_offset, y_offset = self.define_window_geometry(
            TEXT_WIN_RATIO)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        text_widget = tk.Text(window, wrap="none", font=("Courier", 11))
        text_widget.grid(row=0, column=0, sticky="nsew")
        vsb = tk.Scrollbar(window, orient="vertical", command=text_widget.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = tk.Scrollbar(window, orient="horizontal",
                           command=text_widget.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        def format_value(val):
            """Format the values with proper width"""
            if isinstance(val, float):
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
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)

        def on_close():
            self.current_image = None
            self.current_table = None
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def show_histogram(self, mat, help_text="", title=""):
        """Display histogram of an image."""
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
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

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

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
        window = tk.Toplevel(self)
        window.title(title + " | " + help_text)
        window.resizable(True, False)
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        win_w = window.winfo_width()
        win_h = window.winfo_height()
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        window.geometry(f"+{x}+{y}")

        tree = ttk.Treeview(window, columns=("Metric", "Value"),
                            show="headings")
        tree.heading("Metric", text="Metric")
        tree.heading("Value", text="Value")
        tree.column("Metric", width=150)
        tree.column("Value", width=220, anchor="e")
        tree.pack(padx=10, pady=10)
        for metric, value in stats_dict.items():
            formatted_value = f"{value:.5f}"
            tree.insert("", "end", values=(metric, formatted_value))
        window.update_idletasks()

    def show_percentile_plot(self, percentiles, density, help_text="",
                             title=""):
        """
        Displays a percentile density plot.
        percentiles: The x-axis values (percentiles).
        density: The y-axis values (normalized density).
        """
        width, height, x_offset, y_offset = self.define_window_geometry(
            PLT_WIN_1D_RATIO)
        window = tk.Toplevel(self)
        window.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
        window.title(title)
        try:
            dpi = window.winfo_fpixels("1i") + 20
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

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, window)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_close():
            plt.close(fig)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

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
            if nmax > nmin:
                self.current_image = (self.current_image - nmin) / (nmax - nmin)
            self.current_image = np.clip(self.current_image, 0.0, 1.0)
        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)

        settings = self.define_window_geometry(PLT_WIN_2D_RATIO)
        win_width, win_height, x_offset, y_offset = settings

        window = tk.Toplevel(self)
        window.title(f"Viewing: {os.path.basename(file_path)}")
        window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")
        window.message_text_var = tk.StringVar(master=window, value=file_path)

        min_contrast_var = tk.DoubleVar(master=window, value=0.0)
        max_contrast_var = tk.DoubleVar(master=window, value=1.0)
        min_contrast_label_var = tk.StringVar(master=window, value="0.0")
        max_contrast_label_var = tk.StringVar(master=window, value="100.0")


        try:
            dpi = window.winfo_fpixels("1i") + 20
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

        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=0)
        window.rowconfigure(2, weight=0)
        window.columnconfigure(0, weight=1)

        canvas_frame = ttk.Frame(window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame,
                                  textvariable=window.message_text_var,
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
        window.update_idletasks()
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

            aspect_var = tk.StringVar(master=window, value="equal")
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
                if self.current_image is None:
                    return
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

            def open_statistics():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                stats = get_image_statistics(self.current_image)
                title = f"Statistics: {os.path.basename(file_path)}"
                self.show_statistics_table(stats, title=title)

            def open_histogram():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                title = f"Histogram: {os.path.basename(file_path)}"
                self.show_histogram(self.current_image, help_text="",
                                    title=title)

            def open_percentile():
                if self.current_image is None:
                    messagebox.showwarning("No Image",
                                           "No image data to analyze.")
                    return
                try:
                    percentiles, density = get_percentile_density(
                        self.current_image)
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
            self.current_image = None
            self.current_table = None
            plt.close(fig_img)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

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
        self.current_idx = 0
        self.current_axis = 0

        if file_type == "tif":
            list_files = find_file(file_path)
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
                self.show_1d_data(self.current_table,
                                  help_text="HDF-key: " + hdf_key_path,
                                  title=file_path)
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

        window = tk.Toplevel(self)
        window.update_job = None
        window.title(f"Viewing: {os.path.basename(current_path)}")
        window.geometry(f"{win_width}x{win_height}+{x_offset}+{y_offset}")

        message_text_var = tk.StringVar(master=window, value=current_path)
        axis_var = tk.StringVar(master=window, value="axis 0")
        slice0_var = tk.IntVar(master=window, value=0)
        slice1_var = tk.IntVar(master=window, value=0)
        min_contrast_var = tk.DoubleVar(master=window, value=0.0)
        max_contrast_var = tk.DoubleVar(master=window, value=1.0)

        slice0_label_var = tk.StringVar(master=window, value="0")
        slice1_label_var = tk.StringVar(master=window, value="0")
        min_contrast_label_var = tk.StringVar(master=window, value="0.0")
        max_contrast_label_var = tk.StringVar(master=window, value="100.0")

        try:
            dpi = window.winfo_fpixels("1i") + 20
        except:
            dpi = 96
        try:
            default_font = tkFont.nametofont("TkDefaultFont")
            font_family = default_font.cget("family")
            plt.rcParams.update(
                {'font.family': font_family, 'font.size': FONT_SIZE})
        except:
            pass

        # --- Configure window's grid ---
        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=0)
        window.rowconfigure(2, weight=0)
        window.columnconfigure(0, weight=1)
        # --- Create and grid the frames ---
        canvas_frame = ttk.Frame(window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        control_frame = ttk.Frame(window)
        control_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        status_frame = ttk.Frame(window, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        message_label = ttk.Label(status_frame, textvariable=message_text_var,
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
        # Figure 1: To show image
        fig_img, ax_img = plt.subplots(constrained_layout=True, dpi=dpi)
        ax_img.set_title(f"Axis: {0}. Index: {0}. "
                         f"H x W: {height} x {width}")
        ax_img.set_xlabel("X")
        ax_img.set_ylabel("Y")
        ax_img.set_aspect("equal")
        if np.isnan(self.current_image).any():
            self.current_image = np.nan_to_num(self.current_image)
        vmin_init = np.percentile(self.current_image, 0)
        vmax_init = np.percentile(self.current_image, 100)

        slice0 = ax_img.imshow(self.current_image, cmap="gray", vmin=vmin_init,
                               vmax=vmax_init)
        slice0.set_extent([0, width, height, 0])
        # Figure 2: To show intensity-plot
        fig_plot, ax_plot = plt.subplots(constrained_layout=False, dpi=dpi)
        ax_plot.set_title("Line Profile")
        ax_plot.set_box_aspect(np.clip(0.95 * width / height, 0.8, 1.1))

        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        window.update_idletasks()
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
        control_frame.columnconfigure(1, weight=3)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=0)
        control_frame.columnconfigure(4, weight=2)
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
                              textvariable=min_contrast_label_var, width=5)
        min_label.grid(row=0, column=5, sticky='w', padx=(0, 10))

        ttk.Label(control_frame, text="Max %:").grid(row=1, column=3,
                                                     sticky='w', padx=(10, 5),
                                                     pady=2)
        max_slider = ttk.Scale(control_frame, from_=0.0, to=1.0,
                               orient=tk.HORIZONTAL, variable=max_contrast_var)
        max_slider.grid(row=1, column=4, sticky='ew', padx=5, pady=2)
        max_label = ttk.Label(control_frame,
                              textvariable=max_contrast_label_var, width=5)
        max_label.grid(row=1, column=5, sticky='w', padx=(0, 10))

        style = ttk.Style()
        style.theme_use(TTK_THEME)
        style.configure("Short.TButton", padding=[5, 1, 5, 1])

        reset_button = ttk.Button(control_frame, text="Reset",
                                  style="Short.TButton")
        reset_button.grid(row=0, column=6, sticky='ew', padx=5, pady=(5, 0))

        def open_statistics():
            """
            Wrapper to calculate stats and then call the display function.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            stats = get_image_statistics(self.current_image)
            title = f"Statistics: {os.path.basename(current_path)}"
            help_text = f" Slice: {self.current_idx}. Axis {self.current_axis}"
            self.show_statistics_table(stats, title=title, help_text=help_text)

        statistics_button = ttk.Button(control_frame, text="Statistics",
                                       command=open_statistics,
                                       style="Short.TButton")
        statistics_button.grid(row=0, column=7, sticky='ew', padx=(0, 5),
                               pady=(5, 0))

        def open_histogram():
            """
            Wrapper function to get the current image and show its histogram.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            title = f"{os.path.basename(current_path)}"
            help_text = f" slice: {self.current_idx} axis: {self.current_axis}."
            self.show_histogram(self.current_image, help_text=help_text,
                                title=title)

        histogram_button = ttk.Button(control_frame, text="Histogram",
                                      command=open_histogram,
                                      style="Short.TButton")
        histogram_button.grid(row=1, column=6, sticky='ew', padx=5, pady=5)

        def open_percentile():
            """
            Wrapper to calculate percentile density and display the plot.
            """
            if self.current_image is None:
                messagebox.showwarning("No Image", "No image data to analyze.")
                return
            try:
                percentiles, density = get_percentile_density(
                    self.current_image)
            except ValueError as e:
                messagebox.showerror("Error",
                                     f"Could not calculate percentiles:\n{e}")
                return
            title = f"Percentile Plot: {os.path.basename(current_path)}"
            help_text = f" slice: {self.current_idx} axis: {self.current_axis}"
            self.show_percentile_plot(percentiles, density,
                                      help_text=help_text, title=title)
        percentile_button = ttk.Button(control_frame, text="Percentile",
                                       command=open_percentile,
                                       style="Short.TButton")
        percentile_button.grid(row=1, column=7, sticky='ew', padx=(0, 5),
                               pady=5)

        ttk.Label(control_frame, text="Aspect").grid(row=0, column=8,
                                                     sticky='w', padx=(0, 5),
                                                     pady=5)
        aspect_var = tk.StringVar(master=window, value="equal")
        aspect_combo = ttk.Combobox(control_frame, textvariable=aspect_var,
                                    values=["equal", "auto"], width=5)
        aspect_combo.grid(row=1, column=8, sticky='ewns', padx=(0, 5), pady=5)

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

            px_min, px_max = ax_plot.get_xlim()
            idx_start = int(max(0, min(px_min, px_max)))
            idx_end = int(min(len(self.current_table), max(px_min, px_max)))
            if idx_end > idx_start:
                local_data = self.current_table[idx_start:idx_end]
                if local_data.size > 0:
                    local_min = np.nanmin(local_data)
                    local_max = np.nanmax(local_data)
                    yrange = local_max - local_min
                    pad = yrange * 0.05 if yrange != 0 else 1.0
                    ax_plot.set_ylim(local_min - pad, local_max + pad)
            canvas_plot.draw_idle()

        def perform_update(value):
            """
            The HEAVY function: Reads from disk and redraws Matplotlib.
            Only runs when the user stops dragging the slider.
            """
            nonlocal img, height, width
            window.update_job = None
            active_axis = axis_var.get()
            p_min = min_contrast_var.get() * 100.0
            p_max = max_contrast_var.get() * 100.0
            raw_aspect = aspect_var.get().strip()
            aspect_val = "equal"
            if raw_aspect.lower() in ["equal", "auto"]:
                aspect_val = raw_aspect.lower()
            else:
                try:
                    aspect_val = float(raw_aspect)
                except ValueError:
                    pass

            if active_axis == "axis 0" or data is None:
                index = slice0_var.get()
                self.current_axis = 0
                if file_type == "tif":
                    img = load_image(list_files[index])
                    message_text_var.set(list_files[index])
                    (new_height, new_width) = img.shape
                    if new_height != height or new_width != width:
                        clear_plot_lines(clear_all=True)
                    height, width = new_height, new_width
                elif file_type == "cine":
                    img = extract_frame_cine(file_path, index)
                    message_text_var.set(file_path)
                else:
                    img = data[index, :, :]
                    message_text_var.set(current_path)
                ax_img.set_title(
                    f"Axis: 0. Index: {index}. H x W: {height} x {width}")
                slice0.set_extent([0, width, height, 0])
                ax_img.set_aspect(aspect_val)
            else:  # axis 1 (HDF5 only)
                index = slice1_var.get()
                self.current_axis = 1
                img = data[:, index, :]
                message_text_var.set(current_path)
                ax_img.set_title(
                    f"Axis: 1. Index: {index}. H x W: {depth} x {width}")
                slice0.set_extent([0, width, depth, 0])
                ax_img.set_aspect(aspect_val)

            self.current_idx = index
            self.current_image = img

            if np.isnan(self.current_image).any():
                self.current_image = np.nan_to_num(self.current_image)

            vmin = np.percentile(self.current_image, p_min)
            vmax = np.percentile(self.current_image, p_max)
            if vmin == vmax:
                vmin = vmin - 0.5
                vmax = vmax + 0.5
            slice0.set_data(self.current_image)
            slice0.set_clim(vmin, vmax)
            canvas_img.draw_idle()
            update_profile_plot()

        def on_slice_change(value):
            """
            Lightweight debouncer.
            """
            active_axis = axis_var.get()
            if value is None:
                if active_axis == "axis 0":
                    value = slice0_var.get()
                else:
                    value = slice1_var.get()
            val_int = int(float(value))
            if active_axis == "axis 0":
                slice0_label_var.set(f"{val_int}")
            else:
                slice1_label_var.set(f"{val_int}")
            if window.update_job:
                try:
                    window.after_cancel(window.update_job)
                except ValueError:
                    pass
            window.update_job = window.after(10, lambda: perform_update(value))

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

        def update_aspect_ratio(event=None):
            """
            Updates the aspect ratio. If input is invalid, resets UI to 'equal'.
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
            update_profile_plot()

        aspect_combo.bind("<<ComboboxSelected>>", update_aspect_ratio)
        aspect_combo.bind("<Return>", update_aspect_ratio)

        def on_close():
            self.current_image = None
            self.current_table = None
            try:
                canvas_img.get_tk_widget().destroy()
                canvas_plot.get_tk_widget().destroy()
            except:
                pass
            plt.close(fig_img)
            plt.close(fig_plot)
            window.destroy()
            gc.collect()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def export_tif_window(self, file_path, file_type):
        """
        Creates the window for exporting HDF/CINE data to TIF files.
        """
        input_path = None
        hdf_key_path = None
        if file_type == "cine":
            cine_metadata = get_metadata_cine(file_path)
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
                data = load_hdf(full_path, hdf_key_path)
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
                                         f"{depth, height, width}")
        }

        def on_close_window():
            """
            Cleanup variables explicitly to satisfy the Garbage Collector
            before destroying the Tcl widget.
            """
            export_window.vars.clear()
            export_window.destroy()
            gc.collect()

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
                                                    sticky="ew", padx=5, pady=5)
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
                                                             sticky="w", padx=5,
                                                             pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_start"],
                  width=8).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Y-stop:").grid(row=0, column=2, sticky="w",
                                                   padx=(15, 5), pady=5)
        ttk.Entry(crop_frame, textvariable=export_window.vars["y_stop"],
                  width=8).grid(row=0, column=3, sticky="w", padx=5, pady=5)
        ttk.Label(crop_frame, text="Width  | X-start:").grid(row=1, column=0,
                                                             sticky="w", padx=5,
                                                             pady=5)
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
        ttk.Entry(naming_frame, textvariable=export_window.vars["prefix"]).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5)

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
            params['slice_start'] = parse_int(export_window.vars["start"].get(),
                                              0)
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
                params['min_percent'] = float(export_window.vars["min_p"].get())
                params['max_percent'] = float(export_window.vars["max_p"].get())
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
                result = export_hdf_cine_to_tif(params, _gui_status_callback)
                if result == "Success":
                    messagebox.showinfo("Export Complete",
                                        f"Saved to:\n{params['output_path']}",
                                        parent=export_window)
            except Exception as e:
                messagebox.showerror("Export Error", f"An error occurred:\n{e}",
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
        self.export_tif_button.bind("<Button-1>", self.launch_export_tif_window)

        # Initialize parameters
        self.populate_tree_view()
        self.listing_counter = 0
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
                gc.collect()

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
        win_title = "Array Table Viewer"
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
                win_title = full_path + " | HDF-key: " + hdf_key_path
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

    def launch_export_tif_window(self, event):
        """Launch the interactive viewer for the selected folder/file."""
        check = self.check_file_type_in_listbox()
        if check is None or check == "tif":
            msg = "Please select a HDF file or a CINE file"
            messagebox.showinfo("Input needed", msg)
            return
        if check == "cine":
            selected_index = self.file_list_view.curselection()
            selected_file = self.file_list_view.get(selected_index)
            file_path = os.path.join(self.selected_folder_path, selected_file)
            self.export_tif_window(file_path, file_type="cine")
        else:
            selected_index = self.file_list_view.curselection()
            if len(selected_index) == 0:
                messagebox.showinfo("Input needed", "Please select a hdf file")
                return
            self.export_tif_window(self.selected_folder_path, file_type="hdf")

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


display_msg = """
===============================================================================

              GUI software for viewing HDF/TIFF/TEXT/CINE files
              
===============================================================================
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description=display_msg,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-b", "--base", type=str, default=None,
                        help="Specify the base folder")
    parser.add_argument("path", type=str, nargs='?', default=None,
                        help="Specify the base folder (positional alternative)")
    return parser.parse_args()


def get_base_folder():
    """Get the base folder from CLI or config."""
    config_data = load_config()
    base_folder = "."
    if config_data is not None:
        try:
            base_folder = config_data["last_folder"]
        except KeyError:
            base_folder = "."
    return os.path.abspath(base_folder)


def main():
    args = parse_args()
    if args.base is not None:
        base_folder = os.path.abspath(args.base)
    elif args.path is not None:
        base_folder = os.path.abspath(args.path)
    else:
        base_folder = get_base_folder()
    app = DatviewInteraction(base_folder)
    app.mainloop()


if __name__ == "__main__":
    main()
