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
import datetime
import os
import pathlib
import re
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
    options.add_argument('--stop_time', type=int, required=False, default=60,
                         help="Automatically stop when a new fast5 file hasn't been seen for this "
                              "many minutes")
    options.add_argument('--cpu', action='store_true',
                         help='Use the CPU for basecalling (default: use the GPU)')
    options.add_argument('-h', '--help', action='help',
                         help='Show this help message and exit')

    args = parser.parse_args()
    check_arguments(args)
    return args


def main():
    check_python_version()
    args = get_arguments()
    check_guppy_version()
    make_output_directory(args.out_dir)

    try:
        minutes_since_last_read, waiting = 0.0, False
        while True:
            if minutes_since_last_read >= args.stop_time:
                print_stop_message(args.stop_time)
                break

            new_fast5s = check_for_reads(args.batch_size, args.in_dir, args.out_dir)
            if new_fast5s:
                basecall_reads(new_fast5s, args.barcodes, args.model, args.cpu, args.out_dir)
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
    args.barcodes = args.barcodes.lower()
    if args.barcodes not in barcode_choices:
        sys.exit('Error: valid --barcodes choices are: {}'.format(join_with_or(barcode_choices)))

    model_choices = list(BASECALLING.keys())
    args.model = args.model.lower()
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


def print_basecalling_message():
    print('\n\n\n')
    print('RUNNING GUPPY BASECALLING')
    print('-------------------------')


def print_stop_message(stop_time):
    plural = '' if stop_time == 1 else 's'
    print('\nNo new reads for {} minute{} - stopping now. Bye!'.format(stop_time, plural))


def print_waiting_message(waiting):
    if waiting:
        print('.', end='', flush=True)
    else:
        print('Waiting for new reads (Ctrl-C to quit)', end='', flush=True)


def basecall_reads(new_fast5s, barcodes, model, cpu, out_dir):
    print_basecalling_message()
    with tempfile.TemporaryDirectory() as temp_dir:
        # print('Creating temporary directory: {}\n'.format(temp_dir))
        temp_in = pathlib.Path(temp_dir) / 'in'
        temp_out = pathlib.Path(temp_dir) / 'out'
        copy_reads_to_temp_in(new_fast5s, temp_in)
        guppy_command = get_guppy_command(temp_in, temp_out, barcodes, model, cpu)
        execute_with_output(guppy_command)
        merge_results(temp_out, out_dir, barcodes)
    add_to_already_basecalled(new_fast5s, out_dir)


def copy_reads_to_temp_in(new_fast5s, temp_in):
    temp_in.mkdir()
    plural = '' if len(new_fast5s) == 1 else 's'
    print('Read{} to be basecalled:'.format(plural))
    for f in new_fast5s:
        shutil.copy(str(f), str(temp_in))
        print('    {}'.format(str(f)))
    print()


def print_summary_info(barcodes):
    translocation_speed_summary()
    if barcodes != 'none':
        barcode_distribution_summary()
    overall_summary()


def translocation_speed_summary():
    pass
    # TODO: read through sequencing_summary.txt file, getting the following for each read:
    #       run_id, start_time, duration, sequence_length_template
    # TODO: look at the fast5 files and get the exp_start_time for each run_id
    # TODO: use the run exp_start_time and each read's info to build a table of read times and
    #       translation speeds
    # TODO: draw an ASCII plot showing the mean translocation speeds for time windows


def barcode_distribution_summary():
    pass
    # TODO: read through sequencing_summary.txt file, getting the following for each read:
    #       sequence_length_template, barcode_arrangement
    # TODO: for each barcode, draw an ASCII bar plot for the number of bases and the N50 read size
    # TODO: print the classified vs unclassified ratio


def overall_summary():
    pass
    # TODO: read through sequencing_summary.txt file, getting the following for each read:
    #       sequence_length_template
    # TODO: print the number of reads, total bases and N50 read length


def get_guppy_command(in_dir, out_dir, barcodes, model, cpu):
    guppy_command = ['guppy_basecaller',
                     '--input_path', str(in_dir),
                     '--save_path', str(out_dir)]
    if not cpu:
        guppy_command += ['--device', 'auto']
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


def execute_with_output(cmd):
    """
    Run a command and display its output.
    https://stackoverflow.com/a/4417735/2438989
    """
    print_formatted_guppy_command(cmd)
    print()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for c in iter(lambda: p.stdout.read(1), b''):
        print(c.decode(), end='', flush=True)
    p.stdout.close()
    return_code = p.wait()
    print()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def print_formatted_guppy_command(cmd):
    cmd = ' '.join(cmd)
    cmd = cmd.replace('--save_path', '\\\n                 --save_path')
    cmd = cmd.replace('--config', '\\\n                 --config')
    cmd = cmd.replace('--model', '\\\n                 --model')
    cmd = cmd.replace('--barcode_kits', '\\\n                 --barcode_kits')
    print(cmd)


def merge_results(temp_out, out_dir, barcodes):
    log_dir = out_dir / 'guppy_logs'
    log_filename = None
    for filename in temp_out.glob('**/guppy_basecaller_log*'):
        shutil.copy(str(filename), str(log_dir))
        log_filename = filename

    telemetry_dir = out_dir / 'guppy_telemetry'
    timestamp = get_timestamp(log_filename)
    for filename in temp_out.glob('**/sequencing_telemetry.js'):
        new_filename = telemetry_dir / 'sequencing_telemetry-{}.js'.format(timestamp)
        shutil.copyfile(str(filename), str(new_filename))

    for filename in temp_out.glob('**/sequencing_summary.txt'):
        destination_filename = out_dir / 'sequencing_summary.txt'
        merge_summary(filename, destination_filename)

    for filename in temp_out.glob('**/*.fastq'):
        destination_filename = get_destination_filename(barcodes, out_dir, filename)
        merge_fastq(filename, destination_filename)


def get_destination_filename(barcodes, out_dir, source_filename):
    if barcodes == 'none':
        return str(out_dir / 'reads.fastq')
    else:
        match = re.search(r'barcode\d\d', str(source_filename))
        if match:
            barcode = match.group(0)
        else:
            barcode = 'unclassified'
        return str(out_dir / (barcode + '.fastq'))


def merge_fastq(source_filename, destination_filename):
    # print('Merging contents of {} into {}'.format(source_filename, destination_filename))
    destination_filename = str(destination_filename)  # path to str
    with open(source_filename, 'rt') as source:
        with open(destination_filename, 'at') as destination:
            for line in source:
                destination.write(line)


def merge_summary(source_filename, destination_filename):
    # print('Merging contents of {} into {}'.format(source_filename, destination_filename))
    include_header = not destination_filename.is_file()
    destination_filename = str(destination_filename)  # path to str
    with open(source_filename, 'rt') as source:
        with open(destination_filename, 'at') as destination:
            for line in source:
                if not include_header and line.startswith('filename'):
                    continue
                destination.write(line)


def get_timestamp(log_filename):
    """
    Tries to get a timestamp from the log filename so the telemetry filename can be made to match.
    But if it can't, it will just use the current timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if log_filename is not None:
        match = re.search(r'\d\d\d\d-\d\d-\d\d_\d\d-\d\d-\d\d', str(log_filename))
        if match:
            timestamp = match.group(0)
    return timestamp


def make_output_directory(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    log_dir = out_dir / 'guppy_logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    telemetry_dir = out_dir / 'guppy_telemetry'
    telemetry_dir.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    main()
