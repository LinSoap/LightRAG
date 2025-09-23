"""
PyInstaller hook for pandas
解决pandas在打包后的导入问题
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 收集pandas的数据文件
datas = collect_data_files('pandas')

# 收集pandas的动态链接库
binaries = collect_dynamic_libs('pandas')

# 确保pandas的内部模块被正确导入
hiddenimports = [
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.dtypes',
    'pandas._libs.tslibs.conversion',
    'pandas._libs.tslibs.timestamps',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.periods',
    'pandas._libs.tslibs.strptime',
    'pandas._libs.tslibs.parsing',
    'pandas._libs.tslibs.tzconversion',
    'pandas._libs.tslibs.vectorized',
    'pandas._libs.tslibs.strftime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.ccalendar',
    'pandas._libs.tslibs.fields',
    'pandas._libs.tslibs.ccalendar',
    'pandas._libs.tslibs.offsets',
    'pandas._libs.lib',
    'pandas._libs.missing',
    'pandas._libs.interval',
    'pandas._libs.hashing',
    'pandas._libs.ops',
    'pandas._libs.reduction',
    'pandas._libs.writers',
    'pandas._libs.json',
    'pandas._libs.testing',
    'pandas._libs.groupby',
    'pandas._libs.reshape',
    'pandas._libs.window',
    'pandas._libs.skiplist',
    'pandas._libs.hashtable',
    'pandas._libs.properties',
    'pandas._libs.parsers',
    'pandas._libs.compressors',
]