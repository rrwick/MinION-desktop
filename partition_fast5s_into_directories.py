#!/usr/bin/env python3
"""
This script looks for fast5 files in the current directory and partitions them
into numbered directories with 4000 files each.
"""

import glob
import math
import pathlib
import shutil
import sys


files_per_dir = 4000

files = glob.glob('**/*.fast5', recursive=True)
if len(files) == 0:
	sys.exit('Error: no fast5 files found')
directories = math.ceil(len(files) / files_per_dir)
digits = len(str(directories - 1))
format_str = '%0' + str(digits) + 'd'

for i, fast5 in enumerate(files):
    dir_num = i // files_per_dir
    dir_name = format_str % dir_num
    dir_path = pathlib.Path(dir_name)
    if not dir_path.is_dir():
    	dir_path.mkdir()
    	print(str(dir_path.resolve()))
    shutil.move(fast5, dir_name)
