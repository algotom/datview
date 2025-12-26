import pathlib
import setuptools

dependencies = [
    "h5py",
    "hdf5plugin",
    "pillow",
    "matplotlib"
]

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setuptools.setup(
    name="datview",
    version="1.4.0",
    author="Nghia Vo",
    author_email="nvo@bnl.gov",
    description="GUI software for viewing images, text, cine, and HDF files.",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords=['HDF Viewer', 'CINE viewer', 'NXS Viewer', 'Image viewer',
              "Data viewer"],
    url="https://github.com/algotom/datview",
    download_url="https://github.com/algotom/datview.git",
    license="Apache 2.0",
    platforms="Any",
    packages=setuptools.find_packages(include=["datview", "datview.*"]),
    package_data={"datview.assets": ["datview_icon.png"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering"
    ],
    install_requires=dependencies,
    entry_points={'console_scripts': ['datview = datview.main:main']},
    python_requires='>=3.9',
)
