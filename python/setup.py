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
    "imctermite",
    sources=["imctermite.pyx"],
    include_dirs=[numpy.get_include()],
    extra_compile_args=cmpArgs[sys.platform]
)

setup(
    ext_modules=cythonize(extension,language_level=3)
)
