#!/usr/bin/env bash

binned_read_dir=/var/lib/MinKNOW/data/deepbinner_reads

bin_dirs=$(find $binned_read_dir -mindepth 1 -maxdepth 1 -type d | sort)

for bin_dir in $bin_dirs; do
    cd $bin_dir

    printf "\n"$bin_dir"\n"
    echo "----------------------------------------------------------------------"

    ~/MinION-desktop/partition_fast5s_into_directories.py
    if [ $? -eq 0 ]; then
        echo "File partitioning complete"
    else
        echo "Quitting due to error in file partitioning"
        read line
        exit 1
    fi

    ~/MinION-desktop/tarball_fast5_dirs.py
    if [ $? -eq 0 ]; then
        echo ""
    else
        echo "Quitting due to error making tarball"
        read line
        exit 1
    fi
done

printf "\nAll done!\n"
read line
