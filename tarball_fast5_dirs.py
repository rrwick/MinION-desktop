#!/usr/bin/env python3
"""
This script looks for fast5 files in the current directory and partitions them
into numbered directories with 4000 files each.
"""

import os
import shutil
import subprocess
import sys



def main():
    cwd = os.getcwd()
    sub_dirs = [x[0] for x in os.walk('.') if x[0] != '.']
    sub_dirs = [x for x in sub_dirs if x.split('/')[-1].isdigit()]

    for d in sorted(sub_dirs):
        assert d.startswith('.')
        fast5_dir = cwd + d[1:]
        location, name = os.path.split(fast5_dir)
        try:
            _ = int(name)
        except ValueError:
            continue

        print()
        print(fast5_dir)
        print('-' * len(fast5_dir))
        cd(location)
        dir_size, file_count, non_fast5s_found = directory_size(fast5_dir)
        if non_fast5s_found:
            sys.exit('Error: non-fast5 files found')
        if dir_size == 0:
            sys.exit('Error: empty directory')
        tarball = make_tarball(name)
        tarball_size = os.path.getsize(tarball)
        print('{} size: {:,} bytes ({:.2f}%)'.format(tarball, tarball_size, 100.0 * tarball_size / dir_size))
        if verify_tarball(tarball, file_count) and sizes_match(tarball_size, dir_size) and not non_fast5s_found:
            print('everything looks good, deleting directory {}'.format(name))
            shutil.rmtree(fast5_dir)
        else:
            print('problems detected, not deleting {} directory'.format(name))
        print()


def make_tarball(name):
    tar_cmd = 'tar -cf - {} | pigz > {}.tar.gz'.format(name, name)
    print('running: {}'.format(tar_cmd))
    subprocess.run(tar_cmd, shell=True)
    return '{}.tar.gz'.format(name)


def verify_tarball(tarball, file_count):
    print('verifying {}... '.format(tarball), end='', flush=True)
    # First check that the gzip file is good.
    code = subprocess.run('gunzip -t {}'.format(tarball), shell=True).returncode
    if code != 0:
        print('BAD')
        return False
    # Then check that the tar itself is good.
    p = subprocess.run('tar -ztf {} | wc -l'.format(tarball),
                       shell=True, stdout=subprocess.PIPE)
    code = p.returncode
    tar_count = int(p.stdout.decode())
    if code == 0 and tar_count == file_count + 1:
        print('good')
        return True
    else:
        print('BAD')
        return False


def sizes_match(tarball_size, dir_size):
    if tarball_size == 0 or dir_size == 0 or tarball_size > dir_size or tarball_size < dir_size / 4:
        print('BAD SIZES')
        return False
    else:
        print('sizes look good')
        return True


def cd(dir):
    if os.getcwd() != dir:
        print('cd {}'.format(dir))
        os.chdir(dir)


def directory_size(path):
    total_size, file_count = 0, 0
    non_fast5s_found = False
    for entry in os.scandir(path):
        if not entry.name.endswith('.fast5'):
            non_fast5s_found = True
        if entry.is_file():
            file_count += 1
            total_size += entry.stat().st_size
        elif entry.is_dir():
            non_fast5s_found = True
    print('file count: {}'.format(file_count))
    print('directory size: {:,} bytes'.format(total_size))
    return total_size, file_count, non_fast5s_found


if __name__ == '__main__':
    main()
