import subprocess
import sys
import os
import platform
import shutil

"""
Script using PyInstaller to generate exe app for convenient local usage.
Make sure to install PyInstaller.
"""

SCRIPT_NAME = "datview.py"
EXE_NAME = "DatView"
ICON_FILE = "icon.png"
OUTPUT_DIR = "build_app"


def main():
    if not os.path.exists(SCRIPT_NAME):
        print(f"Error: Main script '{SCRIPT_NAME}' not found.")
        print("Please make sure this build script is in the same directory.")
        sys.exit(1)

    icon_arg = ""
    if os.path.exists(ICON_FILE):
        icon_arg = f"--icon={os.path.abspath(ICON_FILE)}"
    else:
        print(f"Warning: Icon file '{ICON_FILE}' not found. "
              f"A default icon will be used.")

    dist_path = os.path.join(OUTPUT_DIR, 'dist')
    build_path = os.path.join(OUTPUT_DIR, 'build')
    spec_path = OUTPUT_DIR
    spec_file = os.path.join(spec_path, f"{EXE_NAME}.spec")

    source_app_path = os.path.join(dist_path, EXE_NAME)
    final_app_path = os.path.join(OUTPUT_DIR, EXE_NAME)

    if os.path.isdir(OUTPUT_DIR):
        print(f"Cleaning previous build folder: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    print(f"Creating output directory: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    command = [
        "pyinstaller",
        "--name", EXE_NAME,
        "--noconsole",
        "--onedir",
        f"--hidden-import=hdf5plugin",
        f"--distpath={dist_path}",
        f"--workpath={build_path}",
        f"--specpath={spec_path}",
    ]

    if icon_arg:
        command.append(icon_arg)

    command.append(SCRIPT_NAME)

    print("--- Running PyInstaller Command ---")
    print(" ".join(command))
    print("-----------------------------------")
    print("This may take a few minutes...")

    try:
        subprocess.check_call(command)
        print("\n--- Build Successful! ---")
        # Post-build cleanup and move
        shutil.move(source_app_path, final_app_path)
        print("Cleaning up byproducts (build, dist, spec)...")
        shutil.rmtree(dist_path)
        shutil.rmtree(build_path)
        os.remove(spec_file)
        # Final output
        exe_path = os.path.join(final_app_path, f"{EXE_NAME}.exe")
        if platform.system() == "Darwin":
            exe_path = os.path.join(final_app_path, f"{EXE_NAME}.app")
        print(f"Your application is ready in: '{final_app_path}'")
        print(f"To run it, double-click: {exe_path}")
        print("\nTo move your app to different place, move the entire folder.")
        print("--------------------------------------------------------------")

    except subprocess.CalledProcessError as e:
        print(f"\n--- Build FAILED! ---")
        print(f"Error: {e}")
        print("--------------------------------------------------------------")
    except FileNotFoundError:
        print(f"\n--- Build FAILED! ---")
        print("Error: 'pyinstaller' command not found.")
        print("Please make sure PyInstaller is installed in your environment:\n")
        print("pip install pyinstaller\n")
        print("--------------------------------------------------------------")
        sys.exit(1)


if __name__ == "__main__":
    main()