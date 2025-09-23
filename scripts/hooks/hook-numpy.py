"""
PyInstaller hook for numpy
解决numpy在打包后的导入问题
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 收集numpy的数据文件
datas = collect_data_files('numpy')

# 收集numpy的动态链接库
binaries = collect_dynamic_libs('numpy')

# 确保numpy的内部模块被正确导入
hiddenimports = [
    'numpy.core._dtype_ctypes',
    'numpy.core._multiarray_umath',
    'numpy.core._multiarray_tests',
    'numpy.linalg._umath_linalg',
    'numpy.fft._pocketfft_internal',
    'numpy.random._common',
    'numpy.random._bounded_integers',
    'numpy.random._mt19937',
    'numpy.random._philox',
    'numpy.random._pcg64',
    'numpy.random._sfc64',
    'numpy.random._generator',
    'numpy.random.bit_generator',
    'numpy.random.mtrand',
    'numpy.random._pickle',
    'numpy.linalg.linalg',
    'numpy.fft.fftpack_lite',
    'numpy._distributor_init',
    'numpy.__config__',
]