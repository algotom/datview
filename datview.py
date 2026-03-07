"""
A single Python file for the DatView GUI software, used for folder browsing and
viewing text, image, HDF, and Cine file formats.

Users can copy this file and run it as:
    python datview.py

Dependencies: h5py, Pillow, pyqtgraph, PySide6. Optional: hdf5plugin
"""

import re
import sys
import os
import csv
import json
import datetime
import platform
import struct
import logging
import warnings
import argparse
import threading
import signal
from pathlib import Path
import h5py
import numpy as np
from PIL import Image
import pyqtgraph as pg

from PySide6.QtCore import (Qt, QTimer, Signal, QAbstractTableModel,
                            QModelIndex, QSortFilterProxyModel, QRect, QFile,
                            QIODevice, QTextStream, QSize)

from PySide6.QtGui import (QFont, QColor, QTextCursor, QTextOption, QIcon,
                           QTextDocument, QPainter, QFontMetrics,
                           QSyntaxHighlighter, QTextCharFormat, QFontDatabase,
                           QCursor)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QLabel, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QListWidget,
                               QComboBox, QSlider, QTextEdit, QMessageBox,
                               QFileDialog, QFrame, QGroupBox, QSplitter,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QPlainTextEdit, QSizePolicy,
                               QRadioButton, QStatusBar, QTableView, QLineEdit,
                               QCheckBox, QMenu, QInputDialog)

try:
    import hdf5plugin  # For viewing compressed HDF files
except ImportError:
    warnings.warn("Optional package 'hdf5plugin' is not installed. "
                  "Compressed HDF5 datasets may not load correctly.",
                  RuntimeWarning)


pg.setConfigOptions(antialias=True, imageAxisOrder='row-major', background='w',
                    foreground='k')
APP_NAME = "DatView"
FONT_SIZE = 13
FONT_WEIGHT = "normal"
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

UI_MARGIN_XS = 2
UI_MARGIN_S = 4
UI_MARGIN_M = 8
UI_MARGIN_L = 10
UI_SPACING_S = 2
UI_SPACING_M = 4
UI_SPACING_L = 8

BTN_H = 35
HIST_MIN_W = 130
HIST_MAX_W = 200
TREE_MIN_W = 280
TABLE_ROW_H = 25

# Data display logic constants
HIST_NUM_BINS = 256
HIST_P_MIN = 0.5
HIST_P_MAX = 99.5
TEXT_LOAD_WHOLE_MAX_BYTES = 5 * 1024 * 1024
TEXT_STREAM_CHUNK = 64 * 1024
TABLE_SIZE_CUTOFF = 200 * 200
MAX_TABLE_SAVE = 2000 * 2000
CSV_MAX_ELEMENTS = 4_000_000
DEBOUNCE_TIMER_MS = 10
FILE_SELECT_DEBOUNCE_MS = 200

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
HDF_EXT = (".nxs", ".nx", ".h5", ".hdf", ".hdf5")
TEXT_EXT = (".json", ".out", ".err", ".txt", ".yaml")
CINE_EXT = ".cine"

THEME_QSS = f"""
    QWidget {{
        font-size: {FONT_SIZE}px;
    }}
    QGroupBox {{
        border: 1px solid rgba(128, 128, 128, 60);
        border-radius: 6px;
        margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
    }}
    QFrame {{
        border-radius: 6px;
    }}
    QPushButton {{
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background-color: #f5f8ff;
        border: 1px solid #3d84ff;
    }}
    QPushButton:pressed {{
        background-color: #eaf1ff;
    }}
    QPushButton:disabled {{
        background-color: #f5f5f5;
        border: 1px solid #dddddd;
        color: #9a9a9a;
    }}
    QPushButton:disabled {{
        opacity: 0.5;
    }}
    QComboBox, QListWidget, QTreeWidget, QTextEdit, QPlainTextEdit, QLineEdit {{
        border: 1px solid rgba(128, 128, 128, 60);
        border-radius: 6px;
        padding: 6px;
    }}
    QStatusBar {{
        border-top: 1px solid rgba(128,128,128,60);
        padding: 10px 10px;
    }}
    QStatusBar::item {{
        border: none;
    }}
    QLabel#StatusPill {{
        border: none;
        padding: 0px 5px 8px 5px;
        margin-left: 5px;
    }}
    QSplitter::handle {{
        background: rgba(128, 128, 128, 40);
    }}
"""

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

logger = logging.getLogger(APP_NAME)


def select_ui_font(point_size: int = 13, weight: int = QFont.Normal) -> QFont:
    """
    Choose a UI font based on OS, using a priority list.
    """
    sysname = platform.system()
    families = set(QFontDatabase.families())

    if sysname == "Linux":
        priority = [
            "Liberation Sans",
            "Cantarell",
            "Ubuntu",
            "Noto Sans",
            "DejaVu Sans",
        ]
    elif sysname == "Windows":
        priority = [
            "Segoe UI",
            "Calibri",
            "Arial",
            "Tahoma",
        ]
    elif sysname == "Darwin":
        priority = [
            ".SF NS Text",
            "Helvetica Neue",
            "Helvetica",
            "Arial",
        ]
    else:
        priority = [
            "Noto Sans",
            "DejaVu Sans",
            "Arial",
        ]

    chosen = None
    for name in priority:
        if name in families:
            chosen = name
            break

    font = QFont(chosen) if chosen else QFont()
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


def calculate_geometry(ratio=0.8):
    """Calculate window size and position centered on screen"""
    screen = QApplication.primaryScreen().availableGeometry()
    width = int(screen.width() * ratio)
    height = int(screen.height() * ratio)
    max_ratio = 1.65
    if width > height:
        current_ratio = width / height
        if current_ratio > max_ratio:
            width = int(max_ratio * height)
    else:
        current_ratio = height / width
        if current_ratio > max_ratio:
            height = int(max_ratio * width)
    x = screen.center().x() - width // 2
    y = screen.center().y() - height // 2
    return QRect(x, y, width, height)


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


def find_file(folder_path, valid_exts=None):
    """
    Fast directory scanning using os.scandir.
    Returns sorted full paths of files matching valid_exts.
    """
    if valid_exts is None:
        valid_exts = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
    else:
        valid_exts = {e.lower() if e.startswith(".") else f".{e.lower()}"
                      for e in valid_exts}
    files = []
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if (entry.is_file() and
                        os.path.splitext(entry.name)[1].lower() in valid_exts):
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
        bmp = struct.unpack('<I2i2H2I2i2I',
                            cinefile.read(bitmap_header_length))
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
        nmin, nmax = np.min(mat), np.max(mat)
        if nmin != nmax:
            mat = np.uint8(255.0 * (mat - nmin) / (nmax - nmin))
        else:
            mat = np.uint8(mat)
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
                if data.size < CSV_MAX_ELEMENTS:
                    writer.writerows(data)
                else:
                    return (f"Array has more than {CSV_MAX_ELEMENTS} "
                            f"elements. Operation not performed.")
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
                mat_cropped = data_obj[0][index, y_start:y_stop,
                                          x_start:x_stop]
            else:
                mat_cropped = data_obj[0][y_start:y_stop, index,
                                          x_start:x_stop]
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
    file_name = os.path.basename(input_path)
    if file_name.lower().endswith(HDF_EXT):
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
        data_objs = None
        try:
            if file_type == "hdf":
                data_objs = load_hdf(input_path, hdf_key, return_file_obj=True)
                if data_objs is None:
                    raise ValueError(f"Could not load HDF dataset: {hdf_key}")
            else:
                data_objs = input_path
            for i_sample, i in enumerate(sample_indices):
                if i_sample % 10 == 0:
                    _report_status(f"Sampling slice "
                                   f"{i_sample + 1}/{len(sample_indices)}...")
                mat_sample = _get_cropped_slice(file_type, data_objs, i, axis,
                                                crop_rect)
                if mat_sample is not None:
                    gmin_list.append(np.percentile(mat_sample, min_percent))
                    gmax_list.append(np.percentile(mat_sample, max_percent))
        finally:
            if file_type == "hdf" and data_objs is not None:
                data_objs[-1].close()
        if not gmin_list or not gmax_list:
            raise ValueError("Failed to gather samples. "
                             "Check slice/crop parameters.")
        gmax = np.max(np.asarray(gmax_list))
        gmin = np.min(np.asarray(gmin_list))
        _report_status(f"Sampling complete. Global min={gmin}, max={gmax}")
    _report_status(f"Starting export for {total_images} images...")
    data_objs = None
    try:
        if file_type == "hdf":
            data_objs = load_hdf(input_path, hdf_key, return_file_obj=True)
            if data_objs is None:
                raise ValueError(f"Could not load HDF dataset: {hdf_key}")
        else:
            data_objs = input_path
        for i_export, i in enumerate(slice_indices):
            mat_out = _get_cropped_slice(file_type, data_objs, i, axis,
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
        if file_type == "hdf" and data_objs is not None:
            data_objs[-1].close()
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


def apply_app_theme(app: QApplication):
    app.setStyle("Fusion")
    pal = app.style().standardPalette()
    app.setPalette(pal)
    app.setStyleSheet(THEME_QSS)


class BaseWindow(QWidget):
    """Base helper for windows to set common properties"""
    closed = Signal(object)

    def __init__(self, parent=None, title="Window", ratio=0.8):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.setGeometry(calculate_geometry(ratio))

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)


class HDFViewerWindow(BaseWindow):
    """Display HDF file hierarchy and dataset info"""

    def __init__(self, parent=None, file_path="", ratio=TEXT_WIN_RATIO):
        super().__init__(parent, f"HDF Viewer: {file_path}", ratio)
        self.file_path = file_path
        # --- Outer layout
        main = QVBoxLayout(self)
        m_val = 4
        main.setContentsMargins(m_val, m_val, m_val, m_val)
        main.setSpacing(2)
        # --- Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(0)
        # ===== Left Pane: Tree (inside a padded frame) =====
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(m_val, m_val, m_val, m_val)
        left_layout.setSpacing(0)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("HDF File Hierarchy")
        self.tree_widget.setIndentation(10)
        self.tree_widget.setUniformRowHeights(True)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        left_layout.addWidget(self.tree_widget)
        self.splitter.addWidget(left_frame)

        # ===== Right Pane: Info (inside a padded frame) =====
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(m_val, m_val, m_val, m_val)
        right_layout.setSpacing(0)

        title = QLabel("Brief Information")
        f = QFont(QApplication.font())
        title.setFont(f)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)

        right_layout.addWidget(title, 0)
        right_layout.addWidget(self.info_text, 1)

        self.splitter.addWidget(right_frame)

        # Split ratio
        self.splitter.setStretchFactor(0, 9)
        self.splitter.setStretchFactor(1, 8)

        main.addWidget(self.splitter, 1)
        try:
            self.hdf_file = h5py.File(file_path, "r")
            self.populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open HDF file: {e}")

    def populate_tree(self):
        def add_node(parent_item, name, obj):
            item = QTreeWidgetItem(parent_item)
            item.setText(0, name.split("/")[-1] if "/" in name else name)
            item.setData(0, Qt.UserRole, name)
            if isinstance(obj, h5py.Group):
                for subname, subobj in obj.items():
                    add_node(item, f"{name}/{subname}".strip("/"), subobj)

        for item_name, item in self.hdf_file.items():
            add_node(self.tree_widget, item_name, item)
        self.tree_widget.expandAll()

    def on_item_double_clicked(self, item, column):
        hdf_path = item.data(0, Qt.UserRole)
        if not hdf_path:
            return
        try:
            obj = self.hdf_file[hdf_path]
        except Exception:
            return
        if isinstance(obj, h5py.Group):
            return
        parent = self.parent()
        if parent and hasattr(parent, "open_hdf_dataset_from_tree"):
            parent.open_hdf_dataset_from_tree(self.file_path, hdf_path)

    def on_selection_changed(self):
        selected = self.tree_widget.selectedItems()
        if not selected:
            return
        hdf_path = selected[0].data(0, Qt.UserRole)

        data_type, value = get_hdf_data(self.file_path, hdf_path)

        info = f"HDF Path: {hdf_path}\n"
        info += f"Data Type: {data_type}\n"
        if data_type == "array":
            info += f"Shape: {value}"
        else:
            info += f"Value: {value}"

        self.info_text.setPlainText(info)

    def closeEvent(self, event):
        if hasattr(self, 'hdf_file'):
            self.hdf_file.close()
        super().closeEvent(event)


class PlotWindow1D(BaseWindow):
    """Window for 1D plots using pyqtgraph"""
    def __init__(self, parent=None, title="", data_x=None, data_y=None,
                 plot_type="plot", help_text="", ratio=PLT_WIN_1D_RATIO):
        super().__init__(parent, title, ratio)
        layout = QVBoxLayout(self)

        self.plot_widget = pg.PlotWidget(title=help_text)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot_widget)
        gui_font = QApplication.font()

        plot_font = QFont(gui_font)
        plot_font.setPointSize(max(8, gui_font.pointSize() - 3))

        for axis_name in ("bottom", "left"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setTickFont(plot_font)
            axis.label.setFont(plot_font)

        self.plot_widget.getPlotItem().titleLabel.setFont(plot_font)

        if plot_type == "plot":
            if data_x is not None:
                self.plot_widget.plot(data_x, data_y, pen='b')
            else:
                self.plot_widget.plot(data_y, pen='b')

        elif plot_type == "histogram":
            flat_data = data_y.ravel()
            try:
                p_min = np.percentile(flat_data, HIST_P_MIN)
                p_max = np.percentile(flat_data, HIST_P_MAX)
                if p_min == p_max:
                    p_min = flat_data.min() - 0.5
                    p_max = flat_data.max() + 0.5
                hist_range = (p_min, p_max)
            except IndexError:
                hist_range = None

            hist, bin_edges = np.histogram(flat_data, bins=HIST_NUM_BINS,
                                           range=hist_range)
            bargraph = pg.BarGraphItem(x=bin_edges[:-1], height=hist,
                                       width=np.diff(bin_edges), brush='b')
            self.plot_widget.addItem(bargraph)
            self.plot_widget.setLabel('bottom', "Grayscale")
            self.plot_widget.setLabel('left', "Frequency (Count)")

        elif plot_type == "percentile":
            self.plot_widget.plot(data_x, data_y, pen='b', symbol='o',
                                  symbolSize=5)
            self.plot_widget.setLabel('bottom', "Percentile")
            self.plot_widget.setXRange(0, 100)
            self.plot_widget.setLabel('left', "Normalized density")
            self.plot_widget.showGrid(x=True, y=True, alpha=0.6)


def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class MiniHighlighter(QSyntaxHighlighter):
    """
    Modes: 'python', 'json', 'yaml', 'log'
    - Python supports triple-quote multiline strings
    - YAML highlights keys, strings, numbers, booleans, comments
    - Log highlights ERROR/WARNING/INFO tokens (and common variants)
    """

    PY_TRIPLE_SINGLE = 1
    PY_TRIPLE_DOUBLE = 2

    def __init__(self, document, mode: str):
        super().__init__(document)
        self.mode = mode.lower()
        self.f_comment = _fmt("#888888", italic=True)
        self.f_string = _fmt("#008000")
        self.f_number = _fmt("#AA00AA")
        self.f_kw = _fmt("#0033CC", bold=True)
        self.f_key = _fmt("#0033CC", bold=True)  # yaml/json keys
        self.f_bool = _fmt("#AA5500", bold=True)

        self.f_err = _fmt("#CC0000", bold=True)
        self.f_warn = _fmt("#CC7A00", bold=True)
        self.f_info = _fmt("#0066CC", bold=True)

        self._re_num = re.compile(r"\b\d+(\.\d+)?([eE][+-]?\d+)?\b")

        if self.mode == "python":
            kws = (
                "and as assert break class continue def del elif else except "
                "False finally for from global if import in is lambda None "
                "nonlocal not or pass raise  return True try while with yield"
            ).split()
            self._py_kw = [re.compile(rf"\b{k}\b") for k in kws]
            self._py_comment = re.compile(r"#.*")
            self._py_sq = re.compile(r"'([^'\\]|\\.)*'")
            self._py_dq = re.compile(r'"([^"\\]|\\.)*"')
        elif self.mode in ("json", "yaml"):
            # YAML: key before ":" ; JSON: "key":
            self._re_yaml_key = re.compile(r"^\s*([A-Za-z0-9_\-\.]+)\s*:", re.M)
            self._re_json_key = re.compile(r'"([^"\\]|\\.)*"\s*:')
            self._re_str = re.compile(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'')
            self._re_bool = re.compile(
                r"\b(true|false|null|True|False|None|yes|no|on|off)\b")
            self._re_comment = re.compile(r"#.*")
        elif self.mode == "log":
            self._re_err = re.compile(r"\b(ERROR|ERR|FATAL|CRITICAL)\b")
            self._re_warn = re.compile(r"\b(WARNING|WARN)\b")
            self._re_info = re.compile(r"\b(INFO)\b")

    def highlightBlock(self, text: str):
        if self.mode == "python":
            self._highlight_python(text)
        elif self.mode == "json":
            self._highlight_json(text)
        elif self.mode == "yaml":
            self._highlight_yaml(text)
        elif self.mode == "log":
            self._highlight_log(text)

    # ---- Python----
    def _highlight_python(self, text: str):
        m = self._py_comment.search(text)
        comment_start = m.start() if m else None
        if m:
            self.setFormat(m.start(), len(text) - m.start(), self.f_comment)
        for pat in (self._py_sq, self._py_dq):
            for mm in pat.finditer(text):
                if comment_start is not None and mm.start() >= comment_start:
                    continue
                self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        limit = comment_start if comment_start is not None else len(text)
        for mm in self._re_num.finditer(text[:limit]):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        for kw in self._py_kw:
            for mm in kw.finditer(text[:limit]):
                self.setFormat(mm.start(), mm.end() - mm.start(), self.f_kw)
        self.setCurrentBlockState(0)
        self._apply_triple_quotes(text, "'''", self.PY_TRIPLE_SINGLE)
        self._apply_triple_quotes(text, '"""', self.PY_TRIPLE_DOUBLE)

    def _apply_triple_quotes(self, text: str, token: str, state_id: int):
        in_state = (self.previousBlockState() == state_id)
        start = 0

        if in_state:
            end = text.find(token, 0)
            if end == -1:
                self.setFormat(0, len(text), self.f_string)
                self.setCurrentBlockState(state_id)
                return
            else:
                end += len(token)
                self.setFormat(0, end, self.f_string)
                start = end
        while True:
            i = text.find(token, start)
            if i == -1:
                break
            j = text.find(token, i + len(token))
            if j == -1:
                self.setFormat(i, len(text) - i, self.f_string)
                self.setCurrentBlockState(state_id)
                return
            else:
                j += len(token)
                self.setFormat(i, j - i, self.f_string)
                start = j

    # ---- JSON / YAML ----
    def _highlight_json(self, text: str):
        for mm in self._re_comment.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_comment)
        # keys: "key":
        for mm in self._re_json_key.finditer(text):
            q1 = text.rfind('"', 0, mm.end())
            q0 = text.rfind('"', 0, q1)
            if q0 != -1 and q1 != -1 and q1 > q0:
                self.setFormat(q0, q1 - q0 + 1, self.f_key)
        # strings
        for mm in self._re_str.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        # numbers
        for mm in self._re_num.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        # booleans / null
        for mm in self._re_bool.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_bool)

    def _highlight_yaml(self, text: str):
        # comments
        for mm in self._re_comment.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_comment)
        # keys (simple): key:
        for mm in self._re_yaml_key.finditer(text):
            self.setFormat(mm.start(1), mm.end(1) - mm.start(1), self.f_key)
        # strings
        for mm in self._re_str.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_string)
        # numbers
        for mm in self._re_num.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_number)
        # booleans
        for mm in self._re_bool.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_bool)

    # ---- Logs ----
    def _highlight_log(self, text: str):
        for mm in self._re_err.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_err)
        for mm in self._re_warn.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_warn)
        for mm in self._re_info.finditer(text):
            self.setFormat(mm.start(), mm.end() - mm.start(), self.f_info)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # monospace font
        f = QFont("DejaVu Sans Mono")
        f.setPointSize(max(9, QApplication.font().pointSize()))
        self.setFont(f)
        # line number area
        self._ln_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.update_line_number_area_width(0)
        # nice defaults
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setTabStopDistance(
            4 * QFontMetrics(self.font()).averageCharWidth())

    def line_number_area_width(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        space = 8 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self._ln_area.scroll(0, dy)
        else:
            self._ln_area.update(0, rect.y(), self._ln_area.width(),
                                 rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self._ln_area.setGeometry(QRect(cr.left(), cr.top(),
                                        self.line_number_area_width(),
                                        cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._ln_area)
        painter.fillRect(event.rect(),
                         self.palette().color(self.backgroundRole()))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        fm = self.fontMetrics()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.palette().color(self.foregroundRole()))
                painter.drawText(0, top, self._ln_area.width() - 4,
                                 fm.height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _on_cursor_moved(self):
        if hasattr(self.parent(), "on_editor_cursor_moved"):
            self.parent().on_editor_cursor_moved()


class TextViewerWindow(BaseWindow):
    def __init__(self, parent=None, title="", file_path=None, content=None,
                 ratio=TEXT_WIN_RATIO):
        super().__init__(parent, title or "Text Viewer", ratio=ratio)
        self.file_path = file_path

        m_val = 4
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m_val, m_val, m_val, m_val)
        layout.setSpacing(4)
        # toolbar: find + wrap toggle + open
        tb = QWidget()
        tb_l = QHBoxLayout(tb)
        tb_l.setContentsMargins(m_val, m_val, m_val, m_val)
        tb_l.setSpacing(4)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find...")
        self.btn_find_next = QPushButton("Find ▶")
        self.btn_find_prev = QPushButton("◀ Prev")
        self.wrap_cb = QCheckBox("Wrap")
        self.btn_open = QPushButton("Open...")

        tb_l.addWidget(self.find_edit, 1)
        tb_l.addWidget(self.btn_find_prev)
        tb_l.addWidget(self.btn_find_next)
        tb_l.addWidget(self.wrap_cb)
        tb_l.addWidget(self.btn_open, 0)
        layout.addWidget(tb, 0)

        # editor
        self.editor = CodeEditor(self)
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor, 1)

        # status row
        status = QWidget()
        s_l = QHBoxLayout(status)
        s_l.setContentsMargins(0, 0, 0, 0)
        s_l.setSpacing(4)
        self.lbl_msg = QLabel(file_path or "")
        self.lbl_pos = QLabel("Ln 1, Col 1")
        self.lbl_size = QLabel("0 KB")
        s_l.addWidget(self.lbl_msg, 1)
        s_l.addWidget(self.lbl_pos, 0)
        s_l.addWidget(self.lbl_size, 0)
        layout.addWidget(status, 0)

        # connect
        self.btn_find_next.clicked.connect(lambda: self._find(step=1))
        self.btn_find_prev.clicked.connect(lambda: self._find(step=-1))
        self.find_edit.returnPressed.connect(lambda: self._find(step=1))
        self.wrap_cb.toggled.connect(self._set_wrap)
        self.btn_open.clicked.connect(self._open_file)
        self.editor.cursorPositionChanged.connect(self._update_cursor_pos)

        if content is not None:
            self.editor.setPlainText(content)
            self.lbl_msg.setText(file_path or "")
            self.editor.moveCursor(QTextCursor.Start)
            self.highlighter = MiniHighlighter(self.editor.document(), "json")
            self._update_cursor_pos()
        elif file_path:
            self.load_file(file_path)

    def _update_cursor_pos(self):
        cur = self.editor.textCursor()
        line = cur.blockNumber() + 1
        col = cur.columnNumber() + 1
        self.lbl_pos.setText(f"Ln {line}, Col {col}")

    def on_editor_cursor_moved(self):
        # called from CodeEditor for the status
        self._update_cursor_pos()

    def _set_wrap(self, enabled: bool):
        if enabled:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def _find(self, step=1):
        txt = self.find_edit.text()
        if not txt:
            return
        flags = QTextDocument.FindFlags()
        if step < 0:
            flags |= QTextDocument.FindBackward
        cursor = self.editor.textCursor()
        if step > 0:
            start = cursor.selectionEnd()
        else:
            start = cursor.selectionStart()
        found = self.editor.find(txt, flags)
        if not found:
            if step > 0:
                self.editor.moveCursor(QTextCursor.Start)
            else:
                self.editor.moveCursor(QTextCursor.End)
            self.editor.find(txt, flags)
        self._update_cursor_pos()

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file",
                                              self.file_path or os.getcwd())
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            f = QFile(path)
            if not f.open(QIODevice.ReadOnly | QIODevice.Text):
                raise RuntimeError("Can't open file")
            size = f.size()
            kb = max(1, int(size // 1024))
            self.lbl_size.setText(f"{kb} KB")
            self.lbl_msg.setText(path)
            if size < TEXT_LOAD_WHOLE_MAX_BYTES:
                txt = bytes(f.readAll()).decode('utf-8', errors='replace')
                self.editor.setPlainText(txt)
            else:
                self.editor.setPlainText("")
                stream = QTextStream(f)
                stream.setCodec('UTF-8')
                self.editor.setUpdatesEnabled(False)
                chunk = []
                while not stream.atEnd():
                    chunk.append(stream.read(TEXT_STREAM_CHUNK))
                self.editor.setPlainText("".join(chunk))
                self.editor.setUpdatesEnabled(True)

            ext = os.path.splitext(path)[1].lower()
            mode = None
            if ext == ".py":
                mode = "python"
            elif ext == ".json":
                mode = "json"
            elif ext in (".yml", ".yaml"):
                mode = "yaml"
            elif ext in (".log", ".out", ".err"):
                mode = "log"

            self.highlighter = MiniHighlighter(self.editor.document(),
                                               mode) if mode else None
            f.close()
            self.editor.moveCursor(QTextCursor.Start)
            self._update_cursor_pos()
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))


class NumpyTableModel(QAbstractTableModel):
    def __init__(self, data: np.ndarray, parent=None):
        super().__init__(parent)
        self._data = np.asarray(data)
        if self._data.ndim == 1:
            self._data = self._data.reshape(-1, 1)

    def rowCount(self, parent=QModelIndex()):
        return int(self._data.shape[0])

    def columnCount(self, parent=QModelIndex()):
        return int(self._data.shape[1])

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            v = self._data[index.row(), index.column()]
            if isinstance(v, (float, np.floating)):
                return f"{float(v):.6g}"
            return str(v)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignRight | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return f"Col {section}"
        return f"Row {section}"


class TableViewerWindow(BaseWindow):
    """Table viewer for 1D/2D arrays"""

    def __init__(self, parent=None, title="", data=None, ratio=TEXT_WIN_RATIO):
        super().__init__(parent, title, ratio)
        m_val = 4
        line_hei = 30
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m_val, m_val, m_val, m_val)
        layout.setSpacing(4)

        # Toolbar row
        bar = QWidget()
        bar.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.edt_find = QLineEdit()
        self.edt_find.setPlaceholderText("Find…")
        self.edt_find.setFixedHeight(line_hei)

        self.btn_copy = QPushButton("Copy selection")
        self.btn_copy.setFixedHeight(line_hei)

        self.btn_save = QPushButton("Save CSV")
        self.btn_save.setFixedHeight(line_hei)

        self.lbl_info = QLabel("")
        self.lbl_info.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        row.addWidget(self.edt_find, 1)
        row.addWidget(self.btn_copy, 0)
        row.addWidget(self.btn_save, 0)
        row.addWidget(self.lbl_info, 0)

        layout.addWidget(bar, 0)

        # Table view (virtualized)
        self.view = QTableView()
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setSortingEnabled(True)
        self.view.setWordWrap(False)
        self.view.setCornerButtonEnabled(False)
        self.view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Headers
        hh = self.view.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setDefaultAlignment(Qt.AlignCenter)

        vh = self.view.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(22)

        layout.addWidget(self.view, 1)

        # Model + proxy (sorting)
        arr = np.asarray(data)
        self.model = NumpyTableModel(arr, self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.view.setModel(self.proxy)

        # Info + actions
        r, c = self.model.rowCount(), self.model.columnCount()
        self.lbl_info.setText(f"{r} × {c}")

        self.edt_find.textChanged.connect(self._on_find_changed)
        self.btn_copy.clicked.connect(self._copy_selection_to_clipboard)
        self.btn_save.clicked.connect(self._save_csv)

        # Make it readable without huge columns
        self.view.resizeColumnsToContents()
        self.view.resizeRowsToContents()

    def _on_find_changed(self, txt: str):
        self.proxy.setFilterFixedString(txt)

    def _copy_selection_to_clipboard(self):
        sel = self.view.selectionModel().selectedIndexes()
        if not sel:
            return
        sel = sorted(sel, key=lambda i: (i.row(), i.column()))
        rows = {}
        for idx in sel:
            rows.setdefault(idx.row(), {})[idx.column()] = idx.data()

        # rectangular output with tabs/newlines (Excel-friendly)
        min_r, max_r = min(rows.keys()), max(rows.keys())
        min_c = min(min(cols.keys()) for cols in rows.values())
        max_c = max(max(cols.keys()) for cols in rows.values())

        lines = []
        for r in range(min_r, max_r + 1):
            cols = rows.get(r, {})
            line = []
            for c in range(min_c, max_c + 1):
                line.append(str(cols.get(c, "")))
            lines.append("\t".join(line))

        QApplication.clipboard().setText("\n".join(lines))

    def _save_csv(self):
        rows = self.proxy.rowCount()
        cols = self.proxy.columnCount()
        if rows <= 0 or cols <= 0:
            QMessageBox.information(self, "Nothing to save", "Table is empty.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Table As", "",
                                              "CSV (*.csv)")
        if not path:
            return
        out = np.empty((rows, cols), dtype=object)
        for r in range(rows):
            for c in range(cols):
                p_idx = self.proxy.index(r, c)
                s_idx = self.proxy.mapToSource(p_idx)
                try:
                    out[r, c] = self.model._data[s_idx.row(), s_idx.column()]
                except Exception:
                    out[r, c] = p_idx.data()

        err = save_table(path, out)
        if err:
            QMessageBox.critical(self, "Save failed", str(err))
        else:
            QMessageBox.information(self, "Saved", f"CSV saved to:\n{path}")


class StatisticsWindow(BaseWindow):
    """Display Image Statistics"""

    def __init__(self, parent=None, title="", stats=None, help_text=""):
        super().__init__(parent, title + " " + help_text, ratio=0.4)
        self.resize(400, 300)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        if stats:
            self.table.setRowCount(len(stats))
            for i, (metric, value) in enumerate(stats.items()):
                self.table.setItem(i, 0, QTableWidgetItem(metric))
                self.table.setItem(i, 1, QTableWidgetItem(f"{value:.5f}"))

        layout.addWidget(self.table)


class Viewer2DWindow(BaseWindow):
    """2D Image Viewer using pyqtgraph"""

    def __init__(self, parent=None, title="", image=None, file_path="",
                 ratio=PLT_WIN_2D_RATIO):
        super().__init__(parent, title, ratio)
        self.parent_app = parent
        self.file_path = file_path
        self.image = np.asarray(image)
        self.is_color = False

        # Preprocessing
        if self.image.ndim == 3 and self.image.shape[2] in [3, 4]:
            self.is_color = True
            nmin, nmax = np.min(self.image), np.max(self.image)
            if nmax > nmin:
                self.image = (self.image - nmin) / (nmax - nmin)
            self.image = np.clip(self.image, 0.0, 1.0)
        if np.isnan(self.image).any():
            self.image = np.nan_to_num(self.image)

        # UI Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                       UI_MARGIN_S)
        main_layout.setSpacing(UI_SPACING_M)
        # Canvas Area
        self.imv = pg.ImageView()
        grid = self.imv.ui.gridLayout
        grid.setHorizontalSpacing(UI_SPACING_M)
        grid.setContentsMargins(UI_MARGIN_XS, UI_MARGIN_XS, UI_MARGIN_XS,
                                UI_MARGIN_XS)
        hist_w = self.imv.getHistogramWidget()
        gui_font = QApplication.font()

        hist_font = QFont(gui_font)
        hist_font.setPointSize(max(8, gui_font.pointSize() - 3))

        hist = self.imv.getHistogramWidget()
        hist_axis = hist.axis

        hist_axis.setTickFont(hist_font)
        hist_axis.label.setFont(hist_font)
        hist_w.setMinimumWidth(HIST_MIN_W)

        self.imv.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imv.ui.roiBtn.hide()
        self.imv.ui.menuBtn.hide()
        self.imv.view.setDefaultPadding(0)

        # Set bright-grey background for Histogram handles (triangles)
        self.imv.getHistogramWidget().setBackground(pg.mkColor(220, 220, 220))

        self.imv.setImage(self.image)
        self.imv.view.autoRange(padding=0)
        main_layout.addWidget(self.imv, 0)

        # --- Control Area: single row, tight layout ---
        controls = QWidget()
        controls.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(controls)
        row.setContentsMargins(UI_MARGIN_XS, UI_MARGIN_XS, UI_MARGIN_S, 0)
        row.setSpacing(UI_SPACING_M)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset)

        self.btn_stats = QPushButton("Statistics")
        self.btn_stats.clicked.connect(self.open_statistics)

        self.btn_hist = QPushButton("Histogram")
        self.btn_hist.clicked.connect(self.open_histogram)

        self.btn_perc = QPushButton("Percentile")
        self.btn_perc.clicked.connect(self.open_percentile)

        self.lbl_aspect = QLabel("Aspect")
        self.lbl_aspect.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["equal", "auto"])
        self.combo_aspect.currentTextChanged.connect(self.update_aspect_ratio)

        # uniform sizing
        buttons = [self.btn_reset, self.btn_stats, self.btn_hist, self.btn_perc]
        for b in buttons:
            b.setFixedHeight(BTN_H)

        max_w = max(b.sizeHint().width() for b in buttons)
        for b in buttons:
            b.setFixedWidth(max_w)

        self.combo_aspect.setFixedHeight(BTN_H)

        row.addWidget(self.btn_reset)
        row.addWidget(self.btn_stats)
        row.addWidget(self.btn_hist)
        row.addWidget(self.btn_perc)
        row.addSpacing(UI_MARGIN_L)
        row.addWidget(self.lbl_aspect)
        row.addWidget(self.combo_aspect)
        row.addStretch(1)

        controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls.setFixedHeight(controls.sizeHint().height())

        main_layout.addWidget(controls, 0)

        # --- Status bar row ---
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)

        self.msg_label = QLabel(self.file_path)
        self.msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.lbl_cursor = QLabel("x=—  y=—  value=—")
        self.lbl_cursor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_cursor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        status_layout.addWidget(self.msg_label, 1)
        status_layout.addWidget(self.lbl_cursor, 0)

        main_layout.addWidget(status_row, 0)
        self.imv.view.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _on_mouse_moved(self, pos):
        if self.image is None or self.image.ndim != 2:
            return
        vb = self.imv.view
        mouse_point = vb.mapSceneToView(pos)
        x = int(np.floor(mouse_point.x()))
        y = int(np.floor(mouse_point.y()))
        h, w = self.image.shape
        if 0 <= x < w and 0 <= y < h:
            v = self.image[y, x]
            if isinstance(v, (float, np.floating)):
                vtxt = f"{float(v):.6g}"
            else:
                vtxt = str(v)
            self.lbl_cursor.setText(f"x={x}  y={y}  value={vtxt}")
        else:
            self.lbl_cursor.setText("x=—  y=—  value=—")

    def update_aspect_ratio(self, text):
        if text == "equal":
            self.imv.view.setAspectLocked(True)
        else:
            self.imv.view.setAspectLocked(False)

    def reset(self):
        if self.image is not None:
            vmin, vmax = np.nanmin(self.image), np.nanmax(self.image)
            if vmin == vmax:
                vmin, vmax = vmin - 0.5, vmax + 0.5
            hist_item = self.imv.getHistogramWidget().item
            hist_item.region.setRegion([vmin, vmax])
            hist_item.gradient.loadPreset('grey')
            self.imv.setLevels(vmin, vmax)
            hist_item.autoHistogramRange()
            self.imv.view.autoRange(padding=0)

            if hasattr(self, "combo_aspect"):
                try:
                    self.combo_aspect.blockSignals(True)
                    self.combo_aspect.setCurrentText("equal")
                finally:
                    self.combo_aspect.blockSignals(False)
            try:
                self.update_aspect_ratio("equal")
            except Exception:
                pass

    def open_statistics(self):
        stats = get_image_statistics(self.image)
        win = StatisticsWindow(self,
                               title=f"Stats: "
                                     f"{os.path.basename(self.file_path)}",
                               stats=stats)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.show()

    def open_histogram(self):
        win = PlotWindow1D(self,
                           title=f"Histogram: "
                                 f"{os.path.basename(self.file_path)}",
                           data_y=self.image, plot_type="histogram")
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.show()

    def open_percentile(self):
        try:
            percentiles, density = get_percentile_density(self.image)
            win = PlotWindow1D(self,
                               title=f"Percentile: "
                                     f"{os.path.basename(self.file_path)}",
                               data_x=percentiles, data_y=density,
                               plot_type="percentile")
            win.setAttribute(Qt.WA_DeleteOnClose)
            win.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def focusInEvent(self, event):
        if self.parent_app and hasattr(self.parent_app, 'set_active_viewer'):
            self.parent_app.set_active_viewer(self)
        super().focusInEvent(event)

    def closeEvent(self, event):
        try:
            self.imv.view.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
        except (TypeError, RuntimeError):
            pass
        try:
            if hasattr(self, "imv") and self.imv is not None:
                try:
                    self.imv.clear()
                except Exception:
                    pass
                try:
                    self.imv.setParent(None)
                except Exception:
                    pass
                try:
                    self.imv.deleteLater()
                except Exception:
                    pass
                self.imv = None
        except Exception:
            pass
        super().closeEvent(event)


class InteractiveViewerWindow(BaseWindow):
    """3D Stack Viewer using pyqtgraph"""

    def __init__(self, parent_app, file_path, file_type, hdf_key=None,
                 list_files=None):
        ratio = PLT_WIN_3D_RATIO
        title = f"Viewing: {os.path.basename(file_path)}"
        super().__init__(parent_app, title, ratio)

        self.parent_app = parent_app
        self.file_path = file_path
        self.file_type = file_type
        self.hdf_key = hdf_key
        self.list_files = list_files
        self.hdf_file_obj = None

        # Initialization logic from original
        if file_type == "tif":
            self.depth = len(list_files)
            initial_image = load_image(list_files[0], average=True)
            self.height, self.width = initial_image.shape[:2]
        elif file_type == "cine":
            metadata = get_metadata_cine(file_path)
            self.width = metadata["biWidth"]
            self.height = metadata["biHeight"]
            self.depth = metadata["TotalImageCount"]
            initial_image = extract_frame_cine(file_path, 0)
        elif file_type == "hdf":
            self.data_obj, self.hdf_file_obj = load_hdf(
                file_path, hdf_key, return_file_obj=True)
            self.depth, self.height, self.width = self.data_obj.shape
            initial_image = self.data_obj[0, :, :]

        self.viewer_state = {
            "image": initial_image,
            "table": None,
            "index": 0,
            "axis": 0,
            "img_width": self.width,
            "img_height": self.height,
            "img_depth": self.depth,
            "last_profile_point": None,
            "last_profile_orientation": None
        }

        # Debounce timer
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(DEBOUNCE_TIMER_MS)
        self.update_timer.timeout.connect(self.perform_update)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                       UI_MARGIN_S)
        main_layout.setSpacing(0)

        # Canvas Area (Image + Plot)
        canvas_widget = QWidget()
        canvas_layout = QHBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(UI_SPACING_S)

        self.imv = pg.ImageView()
        self.imv.view.setMenuEnabled(False)
        self.imv.ui.roiBtn.hide()
        self.imv.ui.menuBtn.hide()

        self.imv.ui.gridLayout.setContentsMargins(UI_MARGIN_XS, UI_MARGIN_XS,
                                                  UI_MARGIN_XS, UI_MARGIN_XS)
        self.imv.ui.gridLayout.setSpacing(UI_SPACING_M)
        self.imv.view.setDefaultPadding(0)

        # --- Darker histogram/LUT background so white triangles are visible ---
        hist_w = self.imv.getHistogramWidget()
        hist_w.setMinimumWidth(HIST_MIN_W)
        hist_w.setMaximumWidth(HIST_MAX_W)
        hist_w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        hist_w.setBackground(pg.mkColor(215, 215, 215))

        # Profile plot
        self.plot_widget = pg.PlotWidget(title="Line Profile")
        self.plot_widget.getViewBox().setDefaultPadding(0)
        self.plot_curve = self.plot_widget.plot(pen='b')

        # --- Make plot fonts match GUI font ---
        gui_font = QApplication.font()
        plot_font = QFont(gui_font)
        plot_font.setPointSize(max(8, gui_font.pointSize() - 3))
        for axis_name in ("bottom", "left"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setTickFont(plot_font)
            axis.label.setFont(plot_font)
        self.plot_widget.getPlotItem().titleLabel.setFont(plot_font)

        hist = self.imv.getHistogramWidget()
        hist_axis = hist.axis
        hist_axis.setTickFont(plot_font)
        hist_axis.label.setFont(plot_font)

        canvas_layout.addWidget(self.imv, 3)
        canvas_layout.addWidget(self.plot_widget, 2)
        main_layout.addWidget(canvas_widget, 1)

        # Interactions
        self.imv.view.scene().sigMouseClicked.connect(self.on_image_click)
        self.imv.view.sigRangeChanged.connect(self.on_view_range_changed)

        # Profile Lines
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen='r')
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen='r')
        self.imv.addItem(self.v_line, ignoreBounds=True)
        self.imv.addItem(self.h_line, ignoreBounds=True)
        self.v_line.hide()
        self.h_line.hide()

        # Controls
        controls = QWidget()
        c_layout = QGridLayout(controls)
        c_layout.setHorizontalSpacing(UI_SPACING_M)
        c_layout.setVerticalSpacing(UI_SPACING_M)
        c_layout.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S, 0)

        # Row 0
        if self.file_type == "hdf" or self.depth > 1:
            self.radio_axis0 = QRadioButton("Axis 0")
            self.radio_axis0.setChecked(True)
            self.radio_axis0.toggled.connect(
                lambda checked: self.on_axis_select(0) if checked else None)
            c_layout.addWidget(self.radio_axis0, 0, 0,
                               alignment=Qt.AlignVCenter)
            self.slider0 = QSlider(Qt.Horizontal)
            self.slider0.setRange(0, self.depth - 1)
            self.slider0.valueChanged.connect(self.on_slice_change_request)
            self.slider0.setFixedHeight(20)
            c_layout.addWidget(self.slider0, 0, 1, alignment=Qt.AlignVCenter)

            self.lbl_slice0 = QLabel("0")
            self.lbl_slice0.setFixedWidth(40)
            c_layout.addWidget(self.lbl_slice0, 0, 2, alignment=Qt.AlignVCenter)
        else:
            c_layout.addWidget(QWidget(), 0, 0, 1, 3)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset)
        c_layout.addWidget(self.btn_reset, 0, 3, alignment=Qt.AlignVCenter)

        self.btn_stats = QPushButton("Statistics")
        self.btn_stats.clicked.connect(self.open_statistics)
        c_layout.addWidget(self.btn_stats, 0, 4, alignment=Qt.AlignVCenter)

        self.btn_save_img = QPushButton("Save Image")
        self.btn_save_img.clicked.connect(self.save_current_image)
        c_layout.addWidget(self.btn_save_img, 0, 5, alignment=Qt.AlignVCenter)

        self.lbl_aspect = QLabel("Aspect")
        self.lbl_aspect.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        c_layout.addWidget(self.lbl_aspect, 0, 6)

        # Row 1
        if self.file_type == "hdf" and self.height > 1 and self.depth > 1:
            self.radio_axis1 = QRadioButton("Axis 1")
            self.radio_axis1.toggled.connect(
                lambda checked: self.on_axis_select(1) if checked else None)
            c_layout.addWidget(self.radio_axis1, 1, 0,
                               alignment=Qt.AlignVCenter)

            self.slider1 = QSlider(Qt.Horizontal)
            self.slider1.setRange(0, self.height - 1)
            self.slider1.setEnabled(False)
            self.slider1.valueChanged.connect(self.on_slice_change_request)
            self.slider1.setFixedHeight(20)
            c_layout.addWidget(self.slider1, 1, 1, alignment=Qt.AlignVCenter)

            self.lbl_slice1 = QLabel("0")
            self.lbl_slice1.setFixedWidth(40)
            c_layout.addWidget(self.lbl_slice1, 1, 2, alignment=Qt.AlignVCenter)
        else:
            c_layout.addWidget(QWidget(), 1, 0, 1, 3)

        self.btn_hist = QPushButton("Histogram")
        self.btn_hist.clicked.connect(self.open_histogram)
        c_layout.addWidget(self.btn_hist, 1, 3, alignment=Qt.AlignVCenter)

        self.btn_perc = QPushButton("Percentile")
        self.btn_perc.clicked.connect(self.open_percentile)
        c_layout.addWidget(self.btn_perc, 1, 4, alignment=Qt.AlignVCenter)

        self.btn_save_tbl = QPushButton("Save Table")
        self.btn_save_tbl.clicked.connect(self.save_current_table)
        c_layout.addWidget(self.btn_save_tbl, 1, 5, alignment=Qt.AlignVCenter)

        self.combo_aspect = QComboBox()
        self.combo_aspect.addItems(["equal", "auto"])
        self.combo_aspect.currentTextChanged.connect(self.update_aspect_ratio)
        self.combo_aspect.setFixedHeight(BTN_H)
        c_layout.addWidget(self.combo_aspect, 1, 6, alignment=Qt.AlignVCenter)

        # --- Make buttons same width/height ---
        buttons_equal = [self.btn_reset, self.btn_stats, self.btn_save_img,
                         self.btn_hist, self.btn_perc, self.btn_save_tbl]
        for b in buttons_equal:
            b.setFixedHeight(BTN_H)
        max_w = max(b.sizeHint().width() for b in buttons_equal)
        for b in buttons_equal:
            b.setFixedWidth(max_w)
        # keep slider column expanding
        c_layout.setColumnStretch(1, 1)
        main_layout.addWidget(controls, 0)

        # Status message
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        self.msg_label = QLabel(self.file_path)
        self.msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_cursor = QLabel("x=—  y=—  value=—")
        self.lbl_cursor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_cursor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        status_layout.addWidget(self.msg_label, 1)
        status_layout.addWidget(self.lbl_cursor, 0)
        main_layout.addWidget(status_row, 0)
        self.imv.view.scene().sigMouseMoved.connect(self._on_mouse_moved)

        self.imv.setImage(self.viewer_state["image"])
        self.imv.view.autoRange(padding=0)

    def _on_mouse_moved(self, pos):
        img = self.viewer_state.get("image")
        if img is None or getattr(img, "ndim", 0) != 2:
            return
        vb = self.imv.view
        mouse_point = vb.mapSceneToView(pos)
        x = int(np.floor(mouse_point.x()))
        y = int(np.floor(mouse_point.y()))
        h, w = img.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            v = img[y, x]
            if isinstance(v, (float, np.floating)):
                vtxt = f"{float(v):.6g}"
            else:
                vtxt = str(v)
            self.lbl_cursor.setText(f"x={x}  y={y}  value={vtxt}")
        else:
            self.lbl_cursor.setText("x=—  y=—  value=—")

    def update_aspect_ratio(self, text):
        if text == "equal":
            self.imv.view.setAspectLocked(True)
        else:
            self.imv.view.setAspectLocked(False)

    def reset(self):
        img = self.viewer_state["image"]
        if img is not None:
            vmin, vmax = np.nanmin(img), np.nanmax(img)
            if vmin == vmax:
                vmin, vmax = vmin - 0.5, vmax + 0.5
            hist_item = self.imv.getHistogramWidget().item
            hist_item.region.setRegion([vmin, vmax])
            hist_item.gradient.loadPreset('grey')
            self.imv.setLevels(vmin, vmax)
            hist_item.autoHistogramRange()
            self.imv.view.autoRange(padding=0)

            if hasattr(self, "combo_aspect"):
                try:
                    self.combo_aspect.blockSignals(True)
                    self.combo_aspect.setCurrentText("equal")
                finally:
                    self.combo_aspect.blockSignals(False)
            try:
                self.update_aspect_ratio("equal")
            except Exception:
                pass

    def on_slice_change_request(self, value):
        if self.depth == 1 or self.height == 1:
            return
        axis = self.viewer_state["axis"]
        if axis == 0:
            self.lbl_slice0.setText(str(value))
        else:
            self.lbl_slice1.setText(str(value))
        self.update_timer.start()

    def perform_update(self):
        axis = self.viewer_state["axis"]
        index = self.slider0.value() if axis == 0 else self.slider1.value()
        prev = self.viewer_state.get("image")
        prev_shape = prev.shape[:2] if (
                prev is not None and hasattr(prev, "shape")) else None
        try:
            if self.file_type == "tif":
                img = load_image(self.list_files[index], average=True)
            elif self.file_type == "cine":
                img = extract_frame_cine(self.file_path, index)
            elif self.file_type == "hdf":
                if axis == 0:
                    img = self.data_obj[index, :, :]
                else:
                    img = self.data_obj[:, index, :]
        except Exception as e:
            logger.error(f"Error loading slice: {e}")
            return

        hei, wid = img.shape[:2]
        self.viewer_state["image"] = img
        self.viewer_state["index"] = index

        shape_changed = False
        if self.file_type == "tif" and prev_shape is not None:
            new_shape = (hei, wid)
            shape_changed = (prev_shape != new_shape)

        if shape_changed:
            self.height, self.width = hei, wid
            self.viewer_state["img_height"] = hei
            self.viewer_state["img_width"] = wid
            if self.viewer_state.get("last_profile_point"):
                y0, x0 = self.viewer_state["last_profile_point"]
                if not (0 <= y0 < hei and 0 <= x0 < wid):
                    self.clear_profile()
            else:
                self.clear_profile()
            self.imv.setImage(img, autoLevels=True, autoRange=True)
            self.reset()
        else:
            self.imv.setImage(img, autoLevels=False, autoRange=False)

        if self.file_type == "tif":
            self.msg_label.setText(
                f"{self.list_files[index]} | Slice: {index} | Axis: "
                f"{axis} | HxW: {hei}x{wid}")
        else:
            self.msg_label.setText(
                f"{self.file_path} | Slice: {index} | Axis: "
                f"{axis} | HxW: {hei}x{wid}")

        if self.viewer_state["last_profile_point"]:
            self.update_profile()
        else:
            self.on_view_range_changed()

    def on_axis_select(self, axis_idx):
        self.viewer_state["axis"] = axis_idx
        if axis_idx == 0:
            self.slider0.setEnabled(True)
            if hasattr(self, 'slider1'):
                self.slider1.setEnabled(False)
        else:
            self.slider0.setEnabled(False)
            if hasattr(self, 'slider1'):
                self.slider1.setEnabled(True)

        self.clear_profile()
        self.perform_update()
        self.reset()

    def clear_profile(self):
        self.viewer_state["table"] = None
        self.viewer_state["last_profile_point"] = None
        self.viewer_state["last_profile_orientation"] = None
        self.v_line.hide()
        self.h_line.hide()
        self.plot_curve.setData([])

    def on_view_range_changed(self):
        if not self.viewer_state["last_profile_point"]:
            return

        orientation = self.viewer_state["last_profile_orientation"]
        data = self.viewer_state["table"]
        if data is None:
            return
        img = self.viewer_state["image"]
        if img is None:
            return
        h, w = img.shape[:2]
        n = w if orientation == "horizontal" else h
        if n <= 1:
            return
        vr = self.imv.view.viewRange()
        if orientation == "horizontal":
            x_min, x_max = vr[0][0], vr[0][1]
        else:
            x_min, x_max = vr[1][0], vr[1][1]

        if not (np.isfinite(x_min) and np.isfinite(x_max)):
            return

        x0 = int(np.clip(np.floor(min(x_min, x_max)), 0, n - 1))
        x1 = int(np.clip(np.ceil(max(x_min, x_max)), 0, n - 1))
        if x1 <= x0:
            return
        # Set plot X range strictly in index space
        self.plot_widget.setXRange(x0, x1, padding=0)
        # Robust Y range from the visible segment
        seg = np.asarray(data[x0:x1], dtype=np.float64)
        seg = seg[np.isfinite(seg)]
        if seg.size == 0:
            return
        lmin = float(seg.min())
        lmax = float(seg.max())
        pad = (lmax - lmin) * 0.05 if lmax != lmin else 1.0
        self.plot_widget.setYRange(lmin - pad, lmax + pad, padding=0)

    def on_image_click(self, event):
        if event.button() not in [Qt.LeftButton, Qt.RightButton]:
            return
        pos = event.pos()
        if self.imv.view.sceneBoundingRect().contains(pos):
            mouse_point = self.imv.view.mapSceneToView(pos)
            x, y = int(mouse_point.x()), int(mouse_point.y())
            img = self.viewer_state["image"]
            h, w = img.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                orientation = 'horizontal' \
                    if event.button() == Qt.LeftButton else 'vertical'
                self.viewer_state["last_profile_point"] = (y, x)
                self.viewer_state["last_profile_orientation"] = orientation
                self.update_profile()

    def update_profile(self):
        if not self.viewer_state["last_profile_point"]:
            return
        y, x = self.viewer_state["last_profile_point"]
        orientation = self.viewer_state["last_profile_orientation"]
        img = self.viewer_state["image"]
        if orientation == 'horizontal':
            self.h_line.setPos(y)
            self.h_line.show()
            self.v_line.hide()
            data = np.asarray(img[y, :], dtype=np.float64)
            self.plot_widget.setTitle(f"Intensity at row: {y}")
        else:
            self.v_line.setPos(x)
            self.v_line.show()
            self.h_line.hide()
            data = np.asarray(img[:, x], dtype=np.float64)
            self.plot_widget.setTitle(f"Intensity at column: {x}")
        if not np.isfinite(data).all():
            data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        self.viewer_state["table"] = data
        self.plot_curve.setData(data)
        self.on_view_range_changed()

    def open_statistics(self):
        stats = get_image_statistics(self.viewer_state["image"])
        win = StatisticsWindow(self, title=f"Stats", stats=stats)
        win.show()

    def open_histogram(self):
        win = PlotWindow1D(self, title="Histogram",
                           data_y=self.viewer_state["image"],
                           plot_type="histogram")
        win.show()

    def open_percentile(self):
        try:
            percentiles, density = get_percentile_density(
                self.viewer_state["image"])
            win = PlotWindow1D(self, title="Percentile", data_x=percentiles,
                               data_y=density, plot_type="percentile")
            win.show()
        except Exception:
            pass

    def save_current_image(self):
        if hasattr(self.parent_app, "set_active_viewer"):
            self.parent_app.set_active_viewer(self)
        self.parent_app.save_to_image()

    def save_current_table(self):
        if hasattr(self.parent_app, "set_active_viewer"):
            self.parent_app.set_active_viewer(self)
        self.parent_app.save_to_table()

    def focusInEvent(self, event):
        p = self.parent_app
        if p and hasattr(p, 'set_active_viewer'):
            p.set_active_viewer(self)
        super().focusInEvent(event)

    def closeEvent(self, event):
        try:
            if hasattr(self, "update_timer") and self.update_timer:
                self.update_timer.stop()
        except Exception:
            pass
        try:
            self.imv.view.scene().sigMouseClicked.disconnect(
                self.on_image_click)
        except (TypeError, RuntimeError):
            pass
        try:
            self.imv.view.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
        except (TypeError, RuntimeError):
            pass
        try:
            self.imv.view.sigRangeChanged.disconnect(self.on_view_range_changed)
        except (TypeError, RuntimeError):
            pass
        if self.hdf_file_obj:
            try:
                self.hdf_file_obj.close()
            except Exception:
                pass
        try:
            if hasattr(self, "imv") and self.imv is not None:
                try:
                    self.imv.clear()
                except Exception:
                    pass
                try:
                    self.imv.setParent(None)
                except Exception:
                    pass
                try:
                    self.imv.deleteLater()
                except Exception:
                    pass
                self.imv = None
        except Exception:
            pass
        try:
            if hasattr(self, "plot_widget") and self.plot_widget is not None:
                try:
                    self.plot_widget.clear()
                except Exception:
                    pass
                try:
                    self.plot_widget.setParent(None)
                except Exception:
                    pass
                try:
                    self.plot_widget.deleteLater()
                except Exception:
                    pass
                self.plot_widget = None
        except Exception:
            pass
        super().closeEvent(event)


class ExportDialog(BaseWindow):
    """
    Dialog for Export parameters
    """

    def __init__(self, parent_app, file_path, file_type, hdf_key=None,
                 shape=None):
        super().__init__(None, f"Export TIF: {os.path.basename(file_path)}",
                         0.5)
        self.input_width = 80
        self.parent_app = parent_app
        self.file_path = file_path
        self.file_type = file_type  # "hdf" | "cine"
        self.hdf_key = hdf_key
        self.shape = tuple(shape) if shape else (0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                  UI_MARGIN_S)
        layout.setSpacing(UI_SPACING_L)

        # ---------------- Destination ----------------
        grp_dest = QGroupBox("Destination")
        gl_dest = QGridLayout(grp_dest)
        gl_dest.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                   UI_MARGIN_S)
        gl_dest.setHorizontalSpacing(UI_SPACING_S)
        gl_dest.setVerticalSpacing(UI_SPACING_S)

        self.txt_path = QLabel("No folder selected...")
        self.txt_path.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        btn_browse = QPushButton("Browse base folder")
        btn_browse.clicked.connect(self.browse_folder)

        self.edt_subfolder = QLineEdit("tifs")
        btn_mkdir = QPushButton("Make subfolder")
        btn_mkdir.clicked.connect(self.make_subfolder)

        gl_dest.addWidget(self.txt_path, 0, 0)
        gl_dest.addWidget(btn_browse, 0, 1)
        gl_dest.addWidget(self.edt_subfolder, 1, 0)
        gl_dest.addWidget(btn_mkdir, 1, 1)

        layout.addWidget(grp_dest)

        # ---------------- Slicing ----------------
        grp_slice = QGroupBox("Slicing")
        gl_slice = QGridLayout(grp_slice)
        gl_slice.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                    UI_MARGIN_S)
        gl_slice.setHorizontalSpacing(UI_SPACING_S)
        gl_slice.setVerticalSpacing(UI_SPACING_S)

        self.combo_axis = QComboBox()
        self.combo_axis.addItems(["Axis 0", "Axis 1"])
        if file_type == "cine":
            self.combo_axis.setEnabled(False)

        gl_slice.addWidget(QLabel("Export along:"), 0, 0)
        gl_slice.addWidget(self.combo_axis, 0, 1)

        gl_slice.addWidget(QLabel("Start:"), 1, 0)
        self.edt_start = QLineEdit("0")
        gl_slice.addWidget(self.edt_start, 1, 1, alignment=Qt.AlignLeft)

        gl_slice.addWidget(QLabel("Stop (-1=End):"), 1, 2)
        self.edt_stop = QLineEdit("-1")
        gl_slice.addWidget(self.edt_stop, 1, 3, alignment=Qt.AlignLeft)

        gl_slice.addWidget(QLabel("Step:"), 1, 4)
        self.edt_step = QLineEdit("1")
        gl_slice.addWidget(self.edt_step, 1, 5, alignment=Qt.AlignLeft)
        layout.addWidget(grp_slice)

        # ---------------- Cropping ----------------
        grp_crop = QGroupBox("Cropping")
        gl_crop = QGridLayout(grp_crop)
        gl_crop.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                   UI_MARGIN_S)
        gl_crop.setHorizontalSpacing(UI_SPACING_S)
        gl_crop.setVerticalSpacing(UI_SPACING_S)
        gl_crop.setColumnStretch(0, 0)
        gl_crop.setColumnStretch(1, 0)
        gl_crop.setColumnStretch(2, 0)
        gl_crop.setColumnStretch(3, 0)
        gl_crop.setColumnStretch(4, 1)

        gl_crop.addWidget(QLabel("Y-Start:"), 0, 0)
        self.edt_ystart = QLineEdit("0")
        gl_crop.addWidget(self.edt_ystart, 0, 1)

        gl_crop.addWidget(QLabel("Y-Stop (-1):"), 0, 2)
        self.edt_ystop = QLineEdit("-1")
        gl_crop.addWidget(self.edt_ystop, 0, 3)

        gl_crop.addWidget(QLabel("X-Start:"), 1, 0)
        self.edt_xstart = QLineEdit("0")
        gl_crop.addWidget(self.edt_xstart, 1, 1)

        gl_crop.addWidget(QLabel("X-Stop (-1):"), 1, 2)
        self.edt_xstop = QLineEdit("-1")
        gl_crop.addWidget(self.edt_xstop, 1, 3)
        layout.addWidget(grp_crop)

        # ---------------- Rescaling ----------------
        grp_rescale = QGroupBox("Rescaling")
        gl_resc = QGridLayout(grp_rescale)
        gl_resc.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                   UI_MARGIN_S)
        gl_resc.setHorizontalSpacing(UI_SPACING_S)
        gl_resc.setVerticalSpacing(UI_SPACING_S)

        self.combo_rescale = QComboBox()
        self.combo_rescale.addItems(["None", "8-bit", "16-bit"])
        gl_resc.addWidget(QLabel("Rescale to:"), 0, 0)
        gl_resc.addWidget(self.combo_rescale, 0, 1)

        gl_resc.addWidget(QLabel("Min %:"), 1, 0)
        self.edt_minp = QLineEdit("0")
        gl_resc.addWidget(self.edt_minp, 1, 1)

        gl_resc.addWidget(QLabel("Max %:"), 1, 2)
        self.edt_maxp = QLineEdit("100")
        gl_resc.addWidget(self.edt_maxp, 1, 3)

        gl_resc.addWidget(QLabel("Sample Step:"), 1, 4)
        self.edt_samp = QLineEdit("10")
        gl_resc.addWidget(self.edt_samp, 1, 5)
        layout.addWidget(grp_rescale)

        # ---------------- Run ----------------
        h_run = QHBoxLayout()
        h_run.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                 UI_MARGIN_S)
        h_run.setSpacing(UI_SPACING_S)

        h_run.addWidget(QLabel("Prefix:"))
        self.edt_prefix = QLineEdit("img")
        self.edt_prefix.setAlignment(Qt.AlignLeft)
        h_run.addWidget(self.edt_prefix)
        h_run.addStretch(0)

        self.btn_export = QPushButton("Export")
        self.btn_export.setFixedWidth(150)
        self.btn_export.clicked.connect(self.run_export)
        h_run.addWidget(self.btn_export)

        layout.addLayout(h_run)

        self.lbl_status = QLabel(f"Shape: {self.shape}")
        layout.addWidget(self.lbl_status)

        for w in (
                self.edt_start,
                self.edt_stop,
                self.edt_step,
                self.edt_ystart,
                self.edt_ystop,
                self.edt_xstart,
                self.edt_xstop,
                self.edt_minp,
                self.edt_maxp,
                self.edt_samp,
                self.edt_prefix,
        ):
            w.setAlignment(Qt.AlignLeft)
            w.setFixedWidth(self.input_width)

        self.adjustSize()
        self.setMinimumSize(self.sizeHint())

    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Destination")
        if d:
            self.txt_path.setText(os.path.normpath(d))

    def make_subfolder(self):
        base = self.txt_path.text().strip()
        sub = self.edt_subfolder.text().strip()

        if base == "No folder selected..." or not os.path.isdir(base):
            QMessageBox.critical(self, "Error",
                                 "Please select a base folder first.")
            return
        if not sub:
            QMessageBox.information(self, "Input needed",
                                    "Please give name for the new folder.")
            return

        path = os.path.join(base, sub)
        try:
            os.makedirs(path, exist_ok=True)
            self.txt_path.setText(path)
            self.edt_subfolder.setText("")
            QMessageBox.information(self, "Success", f"Folder created:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    @staticmethod
    def _parse_int(value, default=0, allow_negative=False):
        try:
            v = int(str(value).strip())
            if not allow_negative and v < 0 and v != -1:
                return default
            return v
        except Exception:
            return default

    def _axis(self) -> int:
        return 0 if self.combo_axis.currentIndex() == 0 else 1

    def validate_export_parameters(self):
        out_path = self.txt_path.text().strip()
        if not os.path.isdir(out_path):
            QMessageBox.critical(self, "Invalid Input",
                                 "Please select a valid folder.")
            return None

        prefix = self.edt_prefix.text().strip()
        if not prefix:
            QMessageBox.critical(self, "Invalid Input",
                                 "Please enter a file prefix.")
            return None

        depth, height, width = self.shape
        axis = self._axis()
        slice_dim = depth if axis == 0 else height
        s_start = self._parse_int(self.edt_start.text(), 0)
        s_stop = self._parse_int(self.edt_stop.text(), slice_dim,
                                 allow_negative=True)
        s_step = self._parse_int(self.edt_step.text(), 1)
        if s_step == 0:
            s_step = 1

        if s_stop == -1 or s_stop > slice_dim:
            s_stop = slice_dim
        if s_start < 0:
            s_start = 0
        if s_start >= s_stop:
            QMessageBox.critical(self, "Invalid Input",
                                 "Start index must be < Stop index.")
            return None
        # Crop dims: for axis==0, each slice is (height, width)
        # for axis==1, each slice is (depth, width)
        y_dim = height if axis == 0 else depth
        x_dim = width

        y_start = self._parse_int(self.edt_ystart.text(), 0)
        y_stop = self._parse_int(self.edt_ystop.text(), y_dim,
                                 allow_negative=True)
        x_start = self._parse_int(self.edt_xstart.text(), 0)
        x_stop = self._parse_int(self.edt_xstop.text(), x_dim,
                                 allow_negative=True)

        if y_stop == -1 or y_stop > y_dim:
            y_stop = y_dim
        if x_stop == -1 or x_stop > x_dim:
            x_stop = x_dim

        y_start = max(0, min(y_start, y_dim))
        x_start = max(0, min(x_start, x_dim))

        if y_start >= y_stop or x_start >= x_stop:
            QMessageBox.critical(self, "Invalid Input",
                                 "Invalid crop dimensions.")
            return None
        # Rescale
        rescale = self.combo_rescale.currentText()

        try:
            min_p = float(self.edt_minp.text().strip())
            max_p = float(self.edt_maxp.text().strip())
        except Exception:
            QMessageBox.critical(self, "Invalid Input",
                                 "Percentiles must be numbers.")
            return None
        if min_p >= max_p:
            QMessageBox.critical(self, "Invalid Input",
                                 "Min Percentile must be < Max.")
            return None

        slice_skip = self._parse_int(self.edt_samp.text(), 1)
        if slice_skip <= 0:
            slice_skip = 1

        return {
            "output_path": out_path,
            "input_path": self.file_path,
            "hdf_key": self.hdf_key,
            "prefix": prefix,
            "axis": axis,
            "slice_start": s_start,
            "slice_stop": s_stop,
            "slice_step": s_step,
            "y_start": y_start,
            "y_stop": y_stop,
            "x_start": x_start,
            "x_stop": x_stop,
            "rescale": rescale,
            "min_percent": min_p,
            "max_percent": max_p,
            "slice_skip": slice_skip,
        }

    def run_export(self):
        params = self.validate_export_parameters()
        if params is None:
            return

        self.btn_export.setEnabled(False)

        def _status(msg):
            self.lbl_status.setText(str(msg))
            QApplication.processEvents()

        _status("Exporting...")

        try:
            res = export_hdf_cine_to_tif(params, _status)
            if res == "Success":
                QMessageBox.information(self, "Done",
                                        f"Export Complete\n\nSaved to:"
                                        f"\n{params['output_path']}")
                self.lbl_status.setText(f"Shape: {self.shape}")
            else:
                self.lbl_status.setText(str(res))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.lbl_status.setText(f"Shape: {self.shape}")
        finally:
            self.btn_export.setEnabled(True)


class DatviewMainWindow(QMainWindow):
    """Main Application Window"""

    def __init__(self, base_folder="."):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}")
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(calculate_geometry(MAIN_WIN_RATIO))

        self.base_folder = Path(base_folder).expanduser()
        if not self.base_folder.exists():
            self.base_folder = Path.home()

        self.active_viewer = None
        self.viewers = []
        self.current_table = None
        self.current_image = None
        self.listing_counter = 0

        # Central Widget & Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QGridLayout(central)
        main_layout.setContentsMargins(UI_MARGIN_M, UI_MARGIN_M, UI_MARGIN_M,
                                       UI_MARGIN_M)
        main_layout.setSpacing(UI_SPACING_L)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(UI_MARGIN_M, 0, 0, 0)
        header_layout.setSpacing(UI_SPACING_L)

        title = QLabel("Current base: ")
        self.lbl_base_folder = QLabel(str(self.base_folder))
        self.lbl_base_folder.setTextInteractionFlags(Qt.TextSelectableByMouse)

        btn_select_folder = QPushButton("Select Base Folder")
        btn_select_folder.clicked.connect(self.select_base_folder)

        header_layout.addWidget(title, 0)
        header_layout.addWidget(self.lbl_base_folder, 1)
        header_layout.addWidget(btn_select_folder, 0)

        main_layout.addWidget(header, 0, 0, 1, 3)

        # --- Body Splitter ---
        body_splitter = QSplitter(Qt.Horizontal)

        # Left: Folder Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(TREE_MIN_W)
        self.tree.itemExpanded.connect(self.on_tree_expand)
        self.tree.itemSelectionChanged.connect(self.on_folder_select)
        body_splitter.addWidget(self.tree)

        # Right: File list + actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(UI_SPACING_M)

        # File list
        self.list_files = QListWidget()
        self.list_files.itemSelectionChanged.connect(self.on_file_select_change)
        self.list_files.itemDoubleClicked.connect(self.on_file_double_click)
        self.list_files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_files.customContextMenuRequested.connect(
            self.on_file_context_menu)
        right_layout.addWidget(self.list_files, 1)

        actions_group = QGroupBox("")
        vs_layout = QGridLayout(actions_group)
        vs_layout.setContentsMargins(UI_MARGIN_S, UI_MARGIN_S, UI_MARGIN_S,
                                     UI_MARGIN_S)
        vs_layout.setHorizontalSpacing(UI_SPACING_M)
        vs_layout.setVerticalSpacing(UI_SPACING_M)

        btn_inter = QPushButton("Interactive Viewer")
        btn_inter.setToolTip(
            "View HDF dataset (array), CINE, or TIF stack in folder")
        btn_inter.clicked.connect(self.launch_interactive_viewer)
        vs_layout.addWidget(btn_inter, 0, 0)

        btn_table = QPushButton("Table Viewer")
        btn_table.setToolTip("Show table of 1D/2D dataset in a HDF file")
        btn_table.clicked.connect(self.launch_table_viewer)
        vs_layout.addWidget(btn_table, 0, 1)

        self.combo_hdf = QComboBox()
        self.combo_hdf.setToolTip("HDF keys to array-like datasets")
        self.combo_hdf.setEnabled(False)
        self.combo_hdf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_hdf.setFixedHeight(BTN_H)
        vs_layout.addWidget(self.combo_hdf, 0, 2)
        self.combo_hdf.currentIndexChanged.connect(
            lambda _idx: self.list_files.setFocus())

        btn_export = QPushButton("Export to TIF")
        btn_export.setToolTip("Export 3D HDF/CINE dataset to TIF files")
        btn_export.clicked.connect(self.launch_export)
        vs_layout.addWidget(btn_export, 0, 3)

        # --- Uniform button sizing ---
        buttons_equal = [btn_inter, btn_table, btn_export]

        for b in buttons_equal:
            b.setMinimumHeight(BTN_H)

        max_width = max(b.sizeHint().width() for b in buttons_equal)
        for b in buttons_equal:
            b.setFixedWidth(max_width)

        right_layout.addWidget(actions_group, 0)
        body_splitter.addWidget(right_panel)

        # Make right side larger by default
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(body_splitter, 1, 0, 1, 3)

        self._init_statusbar()

        main_layout.setRowStretch(1, 1)
        main_layout.setColumnStretch(1, 1)

        self.populate_tree_root()

    def _init_statusbar(self):
        sb = QStatusBar(self)
        sb.setSizeGripEnabled(True)
        self.setStatusBar(sb)
        sb.showMessage("Ready")

        self.sb_filetype = QLabel("")
        self.sb_dims = QLabel("")

        self.sb_filetype.setObjectName("StatusPill")
        self.sb_dims.setObjectName("StatusPill")

        sb.addPermanentWidget(self.sb_filetype)
        sb.addPermanentWidget(self.sb_dims)

    def _show_window(self, win):
        self.viewers.append(win)
        win.closed.connect(
            lambda w: self.viewers.remove(w) if w in self.viewers else None)
        win.show()
        return win

    def select_base_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Base Folder",
                                             str(self.base_folder))
        if d:
            self.base_folder = Path(d)
            self.lbl_base_folder.setText(str(self.base_folder))
            self.populate_tree_root()
            self.combo_hdf.clear()
            self.combo_hdf.setEnabled(False)
            save_config({"last_folder": str(self.base_folder)})

    def populate_tree_root(self):
        self.tree.clear()
        item = QTreeWidgetItem(self.tree)
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
            logger.error(f"Error reading folder: {e}")

    def on_folder_select(self):
        items = self.tree.selectedItems()
        if not items:
            return
        path = items[0].data(0, Qt.UserRole)
        if not path or not os.path.isdir(path):
            return

        self.listing_counter += 1
        current_request_id = self.listing_counter
        self.selected_folder_path = path
        self.statusBar().showMessage(path)

        self.list_files.clear()
        self.combo_hdf.clear()
        self.combo_hdf.setEnabled(False)

        threading.Thread(target=self._populate_files_thread,
                         args=(path, current_request_id),
                         daemon=True).start()

    def _populate_files_thread(self, path, request_id):
        try:
            files = sorted([f.name for f in os.scandir(path) if f.is_file()])

            def update_ui():
                if request_id == self.listing_counter:
                    self.list_files.addItems(files)

            QTimer.singleShot(0, self, update_ui)
        except Exception as e:
            logger.error(f"Error populating files: {e}")

    def refresh_current_folder(self, refresh_tree: bool = False):
        if not hasattr(self,
                       "selected_folder_path") or not self.selected_folder_path:
            return

        path = self.selected_folder_path
        self.listing_counter += 1
        current_request_id = self.listing_counter

        self.list_files.clear()
        self.combo_hdf.clear()
        self.combo_hdf.setEnabled(False)

        threading.Thread(
            target=self._populate_files_thread,
            args=(path, current_request_id),
            daemon=True
        ).start()

        if refresh_tree:
            items = self.tree.selectedItems()
            if items:
                try:
                    self.on_tree_expand(items[0])
                except Exception:
                    pass

    def on_file_select_change(self):
        QTimer.singleShot(FILE_SELECT_DEBOUNCE_MS, self,
                          self._handle_file_single_click)

    def _handle_file_single_click(self):
        items = self.list_files.selectedItems()
        if not items:
            if hasattr(self, 'selected_folder_path'):
                self.statusBar().showMessage(self.selected_folder_path)
            return
        fname = items[0].text()
        if not hasattr(self, 'selected_folder_path'):
            return
        full = os.path.join(self.selected_folder_path, fname)
        self.statusBar().showMessage(full)

        if fname.lower().endswith(HDF_EXT):
            self.populate_hdf_keys(full)
        else:
            self.combo_hdf.clear()
            self.combo_hdf.setEnabled(False)

    def populate_hdf_keys(self, file_path: str):
        selected_items = self.list_files.selectedItems()
        selected_row = self.list_files.row(
            selected_items[0]) if selected_items else None

        self.combo_hdf.blockSignals(True)
        self.combo_hdf.clear()
        self.combo_hdf.setEnabled(True)

        def find_array_datasets(hdf_obj, base_path=""):
            """Find datasets that are 1D/2D/3D numeric arrays (shape tuple)."""
            out = []
            for key, item in hdf_obj.items():
                current_path = f"{base_path}/{key}".strip("/")
                if isinstance(item, h5py.Group):
                    out.extend(find_array_datasets(item, current_path))
                elif isinstance(item, h5py.Dataset):
                    data_type, value = get_hdf_data(file_path, current_path)
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
                self.combo_hdf.addItems(dataset_paths)
                self.combo_hdf.setCurrentIndex(0)
                self.combo_hdf.setEnabled(True)
            else:
                self.combo_hdf.addItem("No valid arrays found")
                self.combo_hdf.setEnabled(False)

        except Exception as e:
            self.combo_hdf.clear()
            self.combo_hdf.addItem("No valid arrays found")
            self.combo_hdf.setEnabled(False)

        finally:
            self.combo_hdf.blockSignals(False)

            # Restore selection + focus back to file list (Tkinter-like UX)
            if (selected_row is not None and
                    0 <= selected_row < self.list_files.count()):
                self.list_files.setCurrentRow(selected_row)
            self.list_files.setFocus()

    def on_file_double_click(self, item):
        fname = item.text()
        full = os.path.join(self.selected_folder_path, fname)
        ext = Path(full).suffix.lower()

        if ext in TEXT_EXT or ext == CINE_EXT:
            self.display_text_file(full)
        elif ext in IMAGE_EXT:
            self.display_image_file(full)
        elif ext in HDF_EXT:
            self.display_hdf_file(full)
        elif is_text_file(full):
            self.display_text_file(full)
        else:
            QMessageBox.warning(self, "Warning", "Unsupported file format")

    def _format_bytes(self, n: int) -> str:
        # Human readable size
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = float(max(n, 0))
        i = 0
        while size >= 1024.0 and i < len(units) - 1:
            size /= 1024.0
            i += 1
        if i == 0:
            return f"{int(size)} {units[i]}"
        return f"{size:.2f} {units[i]}"

    def on_file_context_menu(self, pos):
        # Must have a selected folder
        if not hasattr(self,
                       "selected_folder_path") or not self.selected_folder_path:
            return

        item = self.list_files.itemAt(pos)
        menu = QMenu(self)
        act_mkdir = menu.addAction("Make sub-folder")

        act_copy = None
        act_rename = None
        full_path = None

        if item is not None:
            fname = item.text()
            full_path = os.path.join(self.selected_folder_path, fname)
            act_copy = menu.addAction("Copy full path")
            act_rename = menu.addAction("Change file name")

        if item is not None and full_path and os.path.exists(full_path):
            try:
                st = os.stat(full_path)
                if hasattr(st, "st_birthtime"):
                    created_ts = st.st_birthtime
                    created_label = "Created"
                else:
                    created_ts = st.st_ctime
                    created_label = "Changed"

                created_str = datetime.datetime.fromtimestamp(
                    created_ts).strftime("%Y-%m-%d %H:%M:%S")

                size_bytes = st.st_size
                size_str = self._format_bytes(size_bytes)

                menu.addSeparator()

                info1 = menu.addAction(f"{created_label}: {created_str}")
                info1.setEnabled(False)

                info2 = menu.addAction(
                    f"Size: {size_str} ({size_bytes:,} bytes)")
                info2.setEnabled(False)

            except Exception:
                pass

        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return

        if chosen == act_mkdir:
            self.make_subfolder_in_current()
        elif act_copy is not None and chosen == act_copy:
            self.copy_full_path(full_path)
        elif act_rename is not None and chosen == act_rename:
            self.rename_selected_file(item)

    def copy_full_path(self, full_path: str):
        if not full_path:
            return
        QApplication.clipboard().setText(os.path.normpath(full_path))
        self.statusBar().showMessage(f"Copied: {full_path}", 2500)

    def rename_selected_file(self, item):
        if item is None:
            return
        if not hasattr(self,
                       "selected_folder_path") or not self.selected_folder_path:
            return

        old_name = item.text()
        old_path = os.path.join(self.selected_folder_path, old_name)

        new_name, ok = QInputDialog.getText(
            self, "Change file name", "New name:", QLineEdit.Normal, old_name
        )
        if not ok:
            return

        new_name = (new_name or "").strip()
        if not new_name:
            return

        # Optional: prevent path separators
        if (os.sep in new_name) or (os.altsep and os.altsep in new_name):
            QMessageBox.warning(self, "Invalid name",
                                "Name must not contain path separators.")
            return

        new_path = os.path.join(self.selected_folder_path, new_name)

        if os.path.exists(new_path):
            QMessageBox.warning(self, "Already exists",
                                f"Target already exists:\n{new_path}")
            return
        try:
            os.rename(old_path, new_path)
            item.setText(new_name)
            QTimer.singleShot(0, self, self._handle_file_single_click)
            self.refresh_current_folder(refresh_tree=False)
            self.statusBar().showMessage(f"Renamed to: {new_name}", 2500)
        except Exception as e:
            QMessageBox.critical(self, "Rename failed", str(e))

    def make_subfolder_in_current(self):
        if not hasattr(self,
                       "selected_folder_path") or not self.selected_folder_path:
            return

        name, ok = QInputDialog.getText(
            self, "Make sub-folder", "Folder name:", QLineEdit.Normal, ""
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if (os.sep in name) or (os.altsep and os.altsep in name):
            QMessageBox.warning(self, "Invalid name",
                                "Folder name must not contain path separators.")
            return
        new_dir = os.path.join(self.selected_folder_path, name)
        try:
            os.makedirs(new_dir, exist_ok=False)
            self.statusBar().showMessage(f"Created folder: {new_dir}", 2500)
            self.refresh_current_folder(refresh_tree=True)
        except FileExistsError:
            QMessageBox.warning(self, "Already exists",
                                f"Folder already exists:\n{new_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Create folder failed", str(e))

    def display_text_file(self, path):
        try:

            if path.lower().endswith(CINE_EXT):
                meta = get_metadata_cine(path)
                content = json.dumps(meta, indent=4)
            else:
                content = None
            win = TextViewerWindow(self, title=f"Viewing: {path}",
                                   file_path=path, content=content,
                                   ratio=TEXT_WIN_RATIO)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def display_image_file(self, path):
        try:
            img = load_image(path)
            win = Viewer2DWindow(self,
                                 title=f"Viewing: {os.path.basename(path)}. "
                                       f"(Height, Width) = {img.shape}",
                                 image=img, file_path=path)
            self._show_window(win)
            self.active_viewer = win
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def display_hdf_file(self, path):
        try:
            win = HDFViewerWindow(self, file_path=path, ratio=TEXT_WIN_RATIO)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_hdf_dataset_from_tree(self, file_path: str, hdf_key: str):
        data_type, value = get_hdf_data(file_path, hdf_key)
        file_obj = None
        if data_type != "array" or not isinstance(value, tuple):
            return
        ndim = len(value)
        try:
            data_obj, file_obj = load_hdf(file_path, hdf_key,
                                          return_file_obj=True)
            if ndim == 1:
                data = data_obj[:]
                win = TableViewerWindow(self, title=file_path, data=data)
                self._show_window(win)
                return
            if ndim == 2:
                data = data_obj[:]
                win = Viewer2DWindow(self, title=os.path.basename(file_path),
                                     image=data, file_path=file_path)
                self._show_window(win)
                self.active_viewer = win
                return
            if ndim == 3:
                win = InteractiveViewerWindow(self, file_path, "hdf", hdf_key,
                                              None)
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
        if self.list_files.count() == 0:
            return None
        items = self.list_files.selectedItems()
        if not items:
            try:
                if hasattr(self, 'selected_folder_path'):
                    for entry in os.scandir(self.selected_folder_path):
                        if entry.name.lower().endswith(IMAGE_EXT):
                            return "tif"
            except:
                pass
            return None
        fname = items[0].text().lower()
        if fname.endswith(IMAGE_EXT):
            return "tif"
        if fname.endswith(HDF_EXT):
            return "hdf"
        if fname.endswith(CINE_EXT):
            return "cine"
        return None

    def launch_interactive_viewer(self):
        check = self.check_file_type_in_list()
        if check is None:
            msg = ("Please select a HDF file, a CINE file, or any TIF file "
                   "in a folder")
            QMessageBox.information(self, "Input needed", msg)
            return

        items = self.list_files.selectedItems()
        if not items and check != "tif":
            QMessageBox.information(self, "Input needed",
                                    "Please select a file")
            return

        fname = items[0].text() if items else ""
        path = os.path.join(self.selected_folder_path, fname)

        ftype = check
        hdf_key = None
        list_files = None

        if check == "tif":
            list_files = find_file(self.selected_folder_path)
            if not list_files:
                QMessageBox.critical(self, "No Files",
                                     f"No image files found in: "
                                     f"{self.selected_folder_path}")
                return
            path = self.selected_folder_path
        elif check == "hdf":
            hdf_key = self.combo_hdf.currentText().strip()
            if not hdf_key or hdf_key == "No arrays found":
                QMessageBox.information(self, "Input needed",
                                        "Please select an HDF array key.")
                return

            try:
                data_obj, file_obj = load_hdf(path, hdf_key,
                                              return_file_obj=True)
                data_ndim = len(data_obj.shape)
                if data_ndim == 1:
                    data = data_obj[:]
                    self.current_table = data
                    win = PlotWindow1D(self, title=path, data_y=data,
                                       help_text="HDF-key: " + hdf_key)
                    self._show_window(win)
                    file_obj.close()
                    return
                elif data_ndim == 2:
                    data = data_obj[:]
                    self.current_image = data
                    win = Viewer2DWindow(self,
                                         title=f"Viewing: "
                                               f"{os.path.basename(path)}",
                                         image=data, file_path=path)
                    self._show_window(win)
                    self.active_viewer = win
                    file_obj.close()
                    return
                elif data_ndim != 3:
                    QMessageBox.critical(self, "Can't show data",
                                         f"Only can show 1d, 2d, or 3d data. "
                                         f"Not {data_ndim}d")
                    file_obj.close()
                    return
                file_obj.close()
            except Exception as e:
                QMessageBox.critical(self, "Can't read file",
                                     f"File: {fname}\nError: {e}")
                return

        try:
            win = InteractiveViewerWindow(self, path, ftype, hdf_key,
                                          list_files)
            self._show_window(win)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch: {e}")

    def launch_table_viewer(self):
        items = self.list_files.selectedItems()
        if not items:
            if self.active_viewer:
                self.save_to_table()
                return
            QMessageBox.information(self, "Input needed",
                                    "Please select a HDF or CINE file")
            return
        fname = items[0].text()
        full_path = os.path.join(self.selected_folder_path, fname)

        self.current_table = None
        file_obj = None
        try:
            if fname.lower().endswith(HDF_EXT):
                hdf_key_path = self.combo_hdf.currentText().strip()
                if (not hdf_key_path) or (hdf_key_path == "No arrays found"):
                    QMessageBox.information(self, "Input needed",
                                            "Please select a HDF file and "
                                            "a 1d/2d dataset")
                    return
                data, file_obj = load_hdf(full_path, hdf_key_path,
                                          return_file_obj=True)
                win_title = full_path + " <> HDF-key: " + hdf_key_path
            # -----------------------------
            # CINE: timestamps table
            # -----------------------------
            elif fname.lower().endswith(CINE_EXT):
                data = get_time_stamps_cine(full_path)
                win_title = full_path + " <> Time stamps"
            else:
                QMessageBox.information(self, "Input needed",
                                        "Please select a HDF file and "
                                        "a 1d/2d dataset")
                return
        except Exception as e:
            if file_obj is not None:
                try:
                    file_obj.close()
                except Exception:
                    pass
            QMessageBox.critical(self, "Can't read file",
                                 f"File: {fname}\nError: {e}")
            return
        try:
            if hasattr(data, "shape") and (1 in data.shape):
                data = np.squeeze(data)
            if (not hasattr(data, "shape")) or (len(data.shape) not in (1, 2)):
                if fname.lower().endswith(HDF_EXT):
                    QMessageBox.information(self, "Input needed",
                                            "Please select a HDF file and "
                                            "a 1d/2d dataset")
                else:
                    QMessageBox.information(self, "Invalid Array",
                                            "This function is only for 1D or "
                                            "2D arrays.")
                return
            # Too large -> show as image instead of table
            if data.size > TABLE_SIZE_CUTOFF:
                info = " !!!Display as image instead table due to size!!!"
                win = Viewer2DWindow(
                    self,
                    title=win_title + info,
                    image=data,
                    file_path=full_path,
                )
                self._show_window(win)
                self.current_table = None
                return
            win = TableViewerWindow(self, title=win_title, data=data)
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
            QMessageBox.information(self, "Input needed",
                                    "Please select a HDF file or a CINE file")
            return

        items = self.list_files.selectedItems()
        if not items:
            QMessageBox.information(self, "Input needed",
                                    "Please select a file")
            return

        fname = items[0].text()
        path = os.path.join(self.selected_folder_path, fname)

        ftype = ""
        key = None
        shape = None

        if check == "cine":
            ftype = "cine"
            meta = get_metadata_cine(path)
            shape = (meta["TotalImageCount"], meta["biHeight"], meta["biWidth"])
        elif check == "hdf":
            ftype = "hdf"
            key = self.combo_hdf.currentText().strip()
            if not key or key == "No arrays found":
                QMessageBox.information(self, "Input needed",
                                        "Please select an HDF array key.")
                return
            try:
                with h5py.File(path, 'r') as f:
                    data = f[key]
                    if len(data.shape) == 2:
                        shape = (1, data.shape[0], data.shape[1])
                    elif len(data.shape) != 3:
                        QMessageBox.critical(self, "Only for 3d data",
                                             f"Only export 2d/3d data. "
                                             f"Not {len(data.shape)}d")
                        return
                    else:
                        shape = data.shape
            except:
                return

        if ftype:
            win = ExportDialog(self, path, ftype, key, shape)
            self._show_window(win)

    def set_active_viewer(self, viewer):
        self.active_viewer = viewer
        self.statusBar().showMessage(f"Active: {viewer.windowTitle()}")

    def save_to_image(self):
        if self.active_viewer and hasattr(self.active_viewer, 'viewer_state'):
            img = self.active_viewer.viewer_state.get("image")
        elif self.active_viewer and hasattr(self.active_viewer, 'image'):
            img = self.active_viewer.image
        else:
            img = self.current_image
        if img is None:
            QMessageBox.information(self, "Input needed",
                                    "No active image. Use Interactive-Viewer!")
            return

        path, _ = QFileDialog.getSaveFileName(self,
                                              "Save Image As", "",
                                              "TIFF (*.tif);;PNG (*.png);;"
                                              "JPEG (*.jpg)")
        if path:
            save_image(path, img)
            self.statusBar().showMessage(f"Image saved to: {path}")

    def save_to_table(self):
        if self.active_viewer and hasattr(self.active_viewer, 'viewer_state'):
            data = self.active_viewer.viewer_state.get("table")
            if data is None:
                data = self.current_table
        else:
            data = self.current_table

        if data is None:
            QMessageBox.information(self, "Input needed",
                                    "No selected data. Use viewers "
                                    "or click image for profile!")
            return

        data = np.asarray(data)
        if data.size > MAX_TABLE_SAVE:
            QMessageBox.information(self, "Array Too Large",
                                    f"Array exceeds maximum save size "
                                    f"({MAX_TABLE_SAVE} elements).")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Data As", "",
                                              "CSV (*.csv)")
        if path:
            save_table(path, data)
            self.statusBar().showMessage(f"Data saved to: {path}")


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
    parser.add_argument("path", type=str, nargs="?", default=None,
                        help="Specify the base folder")
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


exit_printed = False


def print_exit_message(*_args):
    global exit_printed
    if exit_printed:
        return
    exit_printed = True
    print("\n************")
    print("Exit the app")
    print("************\n")


def main():
    args = parse_args()
    if args.base is not None:
        base_folder = os.path.abspath(args.base)
    elif args.path is not None:
        base_folder = os.path.abspath(args.path)
    else:
        base_folder = get_base_folder()

    app = QApplication(sys.argv)
    app.aboutToQuit.connect(print_exit_message)

    def _handle_sigint(_signum=None, _frame=None):
        print_exit_message()
        app.quit()

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    _timer = QTimer()
    _timer.start(250)
    _timer.timeout.connect(lambda: None)

    app.setApplicationName(APP_NAME)
    app.setFont(select_ui_font(point_size=FONT_SIZE, weight=QFont.Normal))
    apply_app_theme(app)
    win = DatviewMainWindow(base_folder)
    win.show()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print_exit_message()
        sys.exit(0)


if __name__ == "__main__":
    main()
