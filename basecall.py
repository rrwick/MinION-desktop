#!/usr/bin/env python3
"""
This script is for running Guppy in real time during a MinION run. It will
* wait for new fast5s to appear
* run Guppy on small batches
* consolidate basecalled reads into one file per barcode
* display statistics like barcode distribution and translocation speed

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
import collections
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time


BASECALLING = collections.OrderedDict([
    ('r9.4_fast', ['--config', 'dna_r9.4.1_450bps_fast.cfg']),
    ('r9.4_hac',  ['--config', 'dna_r9.4.1_450bps_hac.cfg']),
    ('r9.4_kp',   ['--config', 'dna_r9.4.1_450bps_hac.cfg',
                   '--model',  'holtlab_kp_large_flipflop_r9.4_r9.4.1_apr_2019.jsn']),
    ('r10_fast',  ['--config', 'TBA']),
    ('r10_hac',   ['--config', 'TBA']),
    ('r10_kp',    ['--config', 'TBA',
                   '--model',  'TBA'])
])

BARCODING = collections.OrderedDict([
    ('native_1-12',  ['--barcode_kits', 'EXP-NBD104', '--trim_barcodes']),
    ('native_13-24', ['--barcode_kits', 'EXP-NBD114', '--trim_barcodes']),
    ('native_1-24',  ['--barcode_kits', '"EXP-NBD104 EXP-NBD114"', '--trim_barcodes']),
    ('rapid_1-12',   ['--barcode_kits', 'SQK-RBK004', '--trim_barcodes']),
    ('none',         [])
])


def get_arguments():
    parser = MyParser(description='Basecall reads in real-time with Guppy',
                      formatter_class=MyHelpFormatter, add_help=False)

    required = parser.add_argument_group('Required')
    required.add_argument('-i', '--in_dir', type=pathlib.Path, required=True,
                          help='Input directory (will be searched recursively for fast5s)')
    required.add_argument('-o', '--out_dir', type=pathlib.Path, required=True,
                          help='Output directory')

    required.add_argument('--barcodes', type=str, required=True,
                          help='Which barcodes to use ({})'.format(join_with_or(BARCODING)))
    required.add_argument('--model', type=str, required=True,
                          help='Which basecalling model to use '
                               '({})'.format(join_with_or(BASECALLING)))

    options = parser.add_argument_group('Options')
    options.add_argument('--batch_size', type=int, required=False, default=10,
                         help='Number of fast5 files to basecall per batch')
    options.add_argument('--stop_time', type=int, required=False, default=30,
                         help="The script will quit when it hasn't seen a new fast5 file for this "
                              "many minutes")
    options.add_argument('-h', '--help', action='help',
                         help='Show this help message and exit')

    args = parser.parse_args()
    check_arguments(args)
    return args


def main():
    check_python_version()
    args = get_arguments()
    check_guppy_version()

    try:
        minutes_since_last_read, waiting = 0.0, False
        while True:
            if minutes_since_last_read >= args.stop_time:
                print_stop_message(args.stop_time)
                break

            new_fast5s = check_for_reads(args.batch_size, args.in_dir, args.out_dir)
            if new_fast5s:
                print_found_read_message(new_fast5s)
                basecall_reads(new_fast5s, args.barcodes, args.model, args.out_dir)
                print_summary_info(args.barcodes)
                minutes_since_last_read, waiting = 0.0, False

            else:  # no new reads
                print_waiting_message(waiting)
                waiting = True
                tick_seconds = 10
                minutes_since_last_read += tick_seconds / 60
                time.sleep(tick_seconds)

    except KeyboardInterrupt:
        print()


def check_arguments(args):
    barcode_choices = list(BARCODING.keys())
    if args.barcodes not in barcode_choices:
        sys.exit('Error: valid --barcodes choices are: {}'.format(join_with_or(barcode_choices)))

    model_choices = list(BASECALLING.keys())
    if args.model not in model_choices:
        sys.exit('Error: valid --model choices are: {}'.format(join_with_or(model_choices)))

    if not args.in_dir.is_dir():
        sys.exit('Error: {} is not a directory'.format(args.in_dir))

    if args.stop_time <= 0:
        sys.exit('Error: --stop_time must be a positive integer')

    if args.batch_size <= 0:
        sys.exit('Error: --batch_size must be a positive integer')

    if args.out_dir.is_file():
        sys.exit('Error: {} is a file (must be a directory)'.format(args.out_dir))
    args.out_dir.mkdir(parents=True, exist_ok=True)


def check_for_reads(batch_size, in_dir, out_dir):
    fast5_files = [x.resolve() for x in in_dir.glob('**/*.fast5')]
    already_basecalled = load_already_basecalled(out_dir)
    fast5_files = [f for f in fast5_files if f.name not in already_basecalled]
    return sorted(f for f in fast5_files)[:batch_size]


def load_already_basecalled(out_dir):
    already_basecalled_files = set()
    already_basecalled_filename = out_dir / 'basecalled_filenames'
    if already_basecalled_filename.is_file():
        with open(str(already_basecalled_filename), 'rt') as already_basecalled:
            for line in already_basecalled:
                already_basecalled_files.add(line.strip())
    return already_basecalled_files


def add_to_already_basecalled(fast5s, out_dir):
    already_basecalled_filename = out_dir / 'basecalled_filenames'
    with open(str(already_basecalled_filename), 'at') as already_basecalled:
        for fast5 in fast5s:
            already_basecalled.write(fast5.name)
            already_basecalled.write('\n')


def print_found_read_message(new_fast5s):
    plural = '' if len(new_fast5s) == 1 else 's'
    print('\nFound {} new read{}'.format(len(new_fast5s), plural))


def print_stop_message(stop_time):
    plural = '' if stop_time == 1 else 's'
    print('\nNo new reads for {} minute{} - stopping now. Bye!'.format(stop_time, plural))


def print_waiting_message(waiting):
    if waiting:
        print('.', end='', flush=True)
    else:
        print('Waiting for new reads (Ctrl-C to quit)', end='', flush=True)


def basecall_reads(new_fast5s, barcodes, model, out_dir):
    with tempfile.TemporaryDirectory() as temp_dir:
        print('created temporary directory', temp_dir)  # TEMP
        temp_in = pathlib.Path(temp_dir) / 'in'
        temp_out = pathlib.Path(temp_dir) / 'out'
        copy_reads_to_temp_in(new_fast5s, temp_in)

        guppy_command = get_guppy_command(temp_in, temp_out, barcodes, model)
        # TODO: run Guppy

        # TODO: merge results from temp dir to final out dir

    add_to_already_basecalled(new_fast5s, out_dir)
    print()


def copy_reads_to_temp_in(new_fast5s, temp_in):
    temp_in.mkdir()
    for f in new_fast5s:
        shutil.copy(str(f), str(temp_in))
        print('copying {} to {}'.format(str(f), str(temp_in)))  # TEMP


def print_summary_info(barcodes):
    # TODO: translocation speed

    if barcodes != 'none':
        # TODO: barcode distribution
        pass


def get_guppy_command(in_dir, out_dir, barcodes, model):
    guppy_command = ['guppy_basecaller',
                     '--input_path', str(in_dir),
                     '--save_path', str(out_dir),
                     '--device', 'auto']
    guppy_command += BASECALLING[model]
    guppy_command += BARCODING[barcodes]
    return guppy_command


def check_python_version():
    try:
        assert sys.version_info >= (3, 5)
    except AssertionError:
        sys.exit('Error: Python 3.5 or greater is required')


def check_guppy_version():
    # TODO: run guppy_basecaller --version and make sure it works
    pass


def join_with_or(str_list):
    if isinstance(str_list, dict):
        str_list = list(str_list.keys())
    if len(str_list) == 0:
        return ''
    if len(str_list) == 1:
        return str_list[0]
    return ', '.join(str_list[:-1]) + ' or ' + str_list[-1]


END_FORMATTING = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


class MyParser(argparse.ArgumentParser):
    """
    This subclass of ArgumentParser changes the error messages, such that if a command is run with
    no other arguments, it will display the help text. If there is a different error, it will give
    the normal response (usage and error).
    """
    def error(self, message):
        if len(sys.argv) == 1:
            self.print_help(file=sys.stderr)
            sys.exit(2)
        else:
            super().error(message)


class MyHelpFormatter(argparse.HelpFormatter):
    """
    This is a custom formatter class for argparse. It adds some custom formatting like dim and bold.
    """
    def __init__(self, prog):
        terminal_width = shutil.get_terminal_size().columns
        os.environ['COLUMNS'] = str(terminal_width)
        max_help_position = min(max(24, terminal_width // 3), 40)
        self.colours = get_colours_from_tput()
        super().__init__(prog, max_help_position=max_help_position)

    def _get_help_string(self, action):
        """
        Override this function to add default values, but only when 'default' is not already in the
        help text.
        """
        help_text = action.help
        if action.default != argparse.SUPPRESS and action.default is not None:
            if 'default' not in help_text.lower():
                help_text += ' (default: {})'.format(action.default)
            elif 'default: DEFAULT' in help_text:
                help_text = help_text.replace('default: DEFAULT',
                                              'default: {}'.format(action.default))
        return help_text

    def start_section(self, heading):
        """
        Override this method to make section headers bold.
        """
        if self.colours > 1:
            heading = BOLD + heading + END_FORMATTING
        super().start_section(heading)

    def _format_action(self, action):
        """
        Override this method to make help descriptions dim.
        """
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = 0
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position
        parts = [action_header]
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            first_line = help_lines[0]
            if self.colours > 8:
                first_line = DIM + first_line + END_FORMATTING
            parts.append('%*s%s\n' % (indent_first, '', first_line))
            for line in help_lines[1:]:
                if self.colours > 8:
                    line = DIM + line + END_FORMATTING
                parts.append('%*s%s\n' % (help_position, '', line))
        elif not action_header.endswith('\n'):
            parts.append('\n')
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))
        return self._join_parts(parts)


def get_colours_from_tput():
    try:
        return int(subprocess.check_output(['tput', 'colors']).decode().strip())
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError, AttributeError):
        return 1


if __name__ == '__main__':
    main()
