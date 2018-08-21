#!/usr/bin/env python3
"""
This script filters fastqs based on the barcode assigned to them by Guppy.

It takes the following arguments:
  1)  Guppy's barcode_summary.txt file
  2)  The exact name of the barcode to output (e.g. barcode01).
  3+) Guppy's fastq files

It outputs reads which have a matching barcode to stdout.

Example usage:
  python3 filter_by_guppy_barcode.py path/to/barcoding_summary.txt barcode01 \
      guppy_out_dir/*.fastq | gzip > filtered_reads.fastq.gz
"""

import sys


def main():
    guppy_barcodes = load_guppy_barcodes(sys.argv[1])
    pass_count, fail_count = filter_reads(guppy_barcodes, sys.argv[2], sys.argv[3:])
    print('  {:,} reads passed (Deepbinner and Guppy agree)'.format(pass_count), file=sys.stderr)
    print('  {:,} reads failed (Deepbinner and Guppy disagree)'.format(fail_count), file=sys.stderr)


def load_guppy_barcodes(barcoding_summary):
    guppy_barcodes = {}
    with open(barcoding_summary, 'rt') as guppy_barcode_results:
        for line in guppy_barcode_results:
            parts = line.split('\t')
            read_id = parts[0]
            barcode = parts[1]
            guppy_barcodes[read_id] = barcode
    return guppy_barcodes


def filter_reads(guppy_barcodes, correct_barcode, fastq_files):
    pass_count, fail_count = 0, 0
    for fastq_file in fastq_files:
        with open(fastq_file, 'rt') as fastq:
            for header in fastq:
                seq = next(fastq)
                spacer = next(fastq)
                qual = next(fastq)
                read_id = header[1:].split()[0]
                try:
                    barcode = guppy_barcodes[read_id]
                except KeyError:
                    barcode = 'unclassified'
                if barcode == correct_barcode:
                    print(header, end='')
                    print(seq, end='')
                    print(spacer, end='')
                    print(qual, end='')
                    pass_count += 1
                else:
                    fail_count +=1
    return pass_count, fail_count


if __name__ == '__main__':
    main()
