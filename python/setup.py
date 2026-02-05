from setuptools import Extension, setup
from Cython.Build import cythonize
import sys
import numpy

print("building on platform: "+sys.platform)

cmpArgs = {
    "linux": ['-std=c++17','-Wno-unused-variable'],
    "darwin": ['-std=c++17','-Wno-unused-variable'],
    "win32": ['/EHsc','/std:c++17']
}

extension = Extension(
    "imctermite._imctermite",
    sources=["imctermite/_imctermite.pyx"],
    include_dirs=["lib", numpy.get_include()],
    extra_compile_args=cmpArgs[sys.platform],
    define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
)

setup(
    ext_modules=cythonize(extension, language_level=3),
    zip_safe=False
)
