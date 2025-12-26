import os
import csv
import json
import platform
import glob
import struct
import h5py
import hdf5plugin
import numpy as np
from PIL import Image

# ==============================================================================
#                          Utility methods
# ==============================================================================

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


def find_file(folder_path, file_ext=None):
    """
    Fast directory scanning using os.scandir.
    Returns sorted full paths of image files.
    """
    if file_ext is None:
        valid_exts = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
    else:
        valid_exts = {".tif", ".tiff"}
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
