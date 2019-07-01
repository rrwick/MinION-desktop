#!/usr/bin/env python3
"""


This program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not,
see <https://www.gnu.org/licenses/>.
"""

import argparse
import sys
import time


def get_arguments():
    parser = argparse.ArgumentParser(description='Basecall reads in real time with Guppy')

    parser.add_argument('--batch_size', type=int, required=False, default=10,
                        help='Number of fast5 files to basecall per batch')
    parser.add_argument('--stop_time', type=int, required=False, default=30,
                        help="The script will quit when it hasn't seen a new fast5 file for this "
                             "many minutes")

    args = parser.parse_args()
    return args


def main():
    args = get_arguments()
    check_current_directory()
    batch_number = get_current_batch_number()

    minutes_since_last_read = 0.0
    waiting = False

    while True:
        if minutes_since_last_read >= args.stop_time:
            print('\nNo new reads for {} minutes - stopping script'.format(args.stop_time))
            break

        new_fast5s = check_for_reads(args.batch_size)
        if new_fast5s:
            print_found_read_message(new_fast5s)
            basecall_reads(new_fast5s)
            print_translocation_speed()
            print_barcode_distribution()
            minutes_since_last_read = 0.0
            waiting = False

        else:
            if not waiting:
                print('Waiting for new reads', end='', flush=True)
                waiting = True
            print('.', end='', flush=True)
            time.sleep(12)
            minutes_since_last_read += 0.2
            continue







def check_current_directory():
    # TODO: make sure that there is a 'fast5' directory here.
    pass


def get_current_batch_number():
    # TODO: see if some basecalling already exists, and if so, return the next available batch number.
    return 1


def check_for_reads(batch_size):
    already_basecalled = load_already_basecalled()
    # TODO: check to see if there are new fast5s and if so, return them.
    return None


def load_already_basecalled():
    # TODO: load the filenames for already-basecalled fast5s.
    return set()


def print_found_read_message(new_fast5s):
    print('\nFound {} new read{}'.format(len(new_fast5s),
                                         '' if len(new_fast5s) == 1 else 's'))


def basecall_reads(new_fast5s):
    # TODO: run Guppy
    # TODO: save reads to already-basecalled file
    # TODO: merge results
    pass


def print_translocation_speed():
    # TODO
    pass


def print_barcode_distribution():
    # TODO
    pass


if __name__ == '__main__':
    main()
