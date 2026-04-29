import sys

import numpy
from Cython.Build import cythonize
from setuptools import Extension, setup


compile_args = {
    "linux": ["-std=c++17", "-Wno-unused-variable"],
    "darwin": ["-std=c++17", "-Wno-unused-variable"],
    "win32": ["/EHsc", "/std:c++17"],
}.get(sys.platform, ["-std=c++17"])

extension = Extension(
    "imctermite._imctermite",
    sources=["python/imctermite/_imctermite.pyx"],
    include_dirs=["lib", numpy.get_include()],
    extra_compile_args=compile_args,
    define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
)


setup(
    ext_modules=cythonize(
        [extension],
        language_level=3,
        include_path=["python"],
    ),
    zip_safe=False,
)
