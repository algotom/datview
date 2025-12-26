import os
import argparse
import datview.lib.utilities as util
from datview.lib.interactions import DatviewInteraction
from datview import __version__


display_msg = """
===============================================================================

              GUI software for viewing HDF/TIFF/TEXT/CINE files

===============================================================================
                     Type: datview to run the software
===============================================================================
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description=display_msg,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version",
                        version=f"Datview {__version__}")
    parser.add_argument("-b", "--base", type=str, default=None,
                        help="Specify the base folder")
    parser.add_argument("path", type=str, nargs='?', default=None,
                        help="Specify the base folder")
    return parser.parse_args()


def get_base_folder():
    """Get the base folder from CLI or config."""
    config_data = util.load_config()
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
