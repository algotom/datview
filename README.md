# DatView
### (Dat)a (View)er software 
![Datview_Logo](https://github.com/algotom/datview/raw/main/icon.png)

---

*Python GUI software for folder browsing and viewing text, image, Cine, and HDF files*

---


Motivation
==========

For synchrotron-based tomography, users need convenient tools to view their 
data, typically in TIF, HDF, or CINE format during experiments, along with 
basic assessment tools such as contrast adjustment, zooming, line-profile 
viewing, histograms, image statistics, or percentile density. However, at synchrotron facilities, 
where Linux OS and open-source software are the primary tools, users often need to switch 
between multiple GUI applications for these tasks such as Nautilus for folder browsing, 
NeXpy or HDFView for HDF files, Gedit for text files, and ImageJ for image viewing.

This separation of tools is inconvenient, especially since many users are not familiar 
with the Linux OS. **DatView** provides a unified GUI for all these tasks, improving 
efficiency and user experience. **DatView** runs across operating systems.

Design Philosophy
=================

DatView has been developed following two key guidelines:
-   Minimize dependencies and the codebase.
-   Maximize functionality and maintainability.

For distributing the software through Pip and Conda, the software is structured based on 
the RUI (Rendering-Utilities-Interactions) concept, which is a user-friendly 
adaptation of the MVC design pattern.

For the easiest usage, a monolithic codebase (**datview.py**) is provided, 
allowing users to simply copy the file and run it without needing to install 
the software through Pip or Conda, provided that their Python environment 
includes H5py, Pillow, and Matplotlib.

Features
========
-   Fast folder browsing and file listing.

    ![Fig1](https://github.com/algotom/datview/raw/main/figs/fig1.png)
  
-   Interactive viewing 1D, 2D, or 3D datasets in an HDF file. Supports ROI zooming, 
    horizontal/vertical line-profile selection, contrast adjustment, and slicing along axis 0 and 1. 

    ![Fig2](https://github.com/algotom/datview/raw/main/figs/fig2.png)

-   Options to display histogram, percentile density, image statistics.

    ![Fig3](https://github.com/algotom/datview/raw/main/figs/fig3.png)

-   View metadata in HDF or CINE files, and display text-file contents.

    ![Fig4](https://github.com/algotom/datview/raw/main/figs/fig4.png)

-   Export to TIF files from HDF or CINE files.

    ![Fig5](https://github.com/algotom/datview/raw/main/figs/fig5.png)

-   Interactive viewing of TIF files in a folder or frames of a CINE file.

-   Interactive viewing of common image formats (JPG, PNG, TIF, ...).
-   Viewing 1D or 2D datasets of an HDF file in table format.
-   Opening multiple interactive viewers simultaneously.
-   Saving a 2D array in a 3D dataset (HDF or CINE) as an image.
-   Saving a 1D or 2D dataset of an HDF file or the current line profile as a CSV file.

Installation
============

Install [Miniconda, Anaconda or Miniforge](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html), then 
open a Linux terminal or the Miniconda/Anaconda PowerShell prompt and use the following commands
for installation.

Using pip:
```commandline
pip install datview
```
Using conda:
```commandline
conda install -c conda-forge datview
```
Once installed, launching Datview with
```commandline
datview
```
Using -h for option usage
```commandline
datview -h
```
---
Installing from source:
- If using a single file:
    + Copy the file *datview.py*. Install python, h5py, pillow, and matplotlib
    + Run:
        ```commandline
        python datview.py
        ```
- If using setup.py
    + Create conda environment
      ```commandline
      conda create -n datview python=3.11
      conda activate datview
      ``` 
    + Clone the source (git needs to be installed)
      ```commandline
      git clone https://github.com/algotom/datview.git
      ```
    + Navigate to the cloned directory (having setup.py file)
      ```commandline
      pip install .
      ```

Generating the executable application

- Install the required Python packages in your environment: PyInstaller, H5py,
  Hdf5plugin, Pillow, Matplotlib

- Use the **build_exe_app.py** script and run the following command:
  ```commandline
  python build_exe_app.py

Usage
=====

- Double-click an HDF or CINE file to display its metadata.
- Click "Interactive Viewer" to view images from a 3D dataset in an HDF file or 
  from a folder of TIFF files.
- Click "Save Image" to save the image you’re currently viewing in the 
  Interactive-Viewer window of an HDF file.
- Click "Save Table" to save a 1D or 2D array from an HDF dataset or a current line-profile
  in interactive viewer, to a CSV file.