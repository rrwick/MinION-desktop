#!/usr/bin/env bash

cd /var/lib/MinKNOW/data

deepbinner realtime --in_dir reads --out_dir deepbinner_reads -s ~/Deepbinner/models/EXP-NBD103_read_starts -e ~/Deepbinner/models/EXP-NBD103_read_ends
