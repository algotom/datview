import os
import sys
import signal
import argparse
from PySide6.QtCore import QTimer
import datview.lib.utilities as util
from datview.lib.interactions import DatviewInteraction
from datview import __version__

display_msg = """
===============================================================================

              GUI software for viewing HDF/TIFF/TEXT/CINE files

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
    parser.add_argument("path", type=str, nargs="?", default=None,
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

    controller = DatviewInteraction(base_folder=base_folder)
    controller.app.aboutToQuit.connect(print_exit_message)

    def _handle_exit_signal(_signum=None, _frame=None):
        print_exit_message()
        controller.app.quit()

    signal.signal(signal.SIGINT, _handle_exit_signal)
    signal.signal(signal.SIGTERM, _handle_exit_signal)

    _timer = QTimer()
    _timer.start(250)
    _timer.timeout.connect(lambda: None)

    try:
        sys.exit(controller.run())
    except KeyboardInterrupt:
        print_exit_message()
        sys.exit(0)


if __name__ == "__main__":
    main()
