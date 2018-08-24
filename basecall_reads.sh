#!/usr/bin/env bash

# This script handles all of the basecalling and read processing. For each
# of Deepbinner's barcode bins, it will:
#   1) Basecall the reads with Guppy.
#   2) Barcode the reads with Guppy, keeping reads for which Deepbinner and
#      Guppy agree on the barcode.
#   3) Trim the reads with Porechop.


binned_read_dir=/var/lib/MinKNOW/data/deepbinner_reads
output_dir=/var/lib/MinKNOW/data/basecalled_reads


# Choose a config file based on the flowcell type.
flowcell=$1
if [ "$flowcell" == "R9.4" ]; then
    config="dna_r9.4_450bps.cfg"
elif [ "$flowcell" == "R9.4.1" ]; then
    config="dna_r9.4.1_450bps_prom.cfg"
elif [ "$flowcell" == "R9.5" ]; then
    config="dna_r9.5_450bps.cfg"
fi
if [[ -z "${config// }" ]]; then
    echo "Error: must specify flowcell: R9.4, R9.4.1 or R9.5"
    read line; exit 1
fi


# Make sure the read's flowcell matches the specified flowcell.
one_read=$(find $binned_read_dir -type f -name "*.fast5" | head -n1)
detected_flowcell=$(h5dump $one_read | grep -ioP "flo-min\d\d\d" | head -n1 | tr [a-z] [A-Z])
if [ "$flowcell" == "R9.5" ] && [ "$detected_flowcell" == "FLO-MIN106" ]; then
    echo "Error: R9.4 flowcell detected - not compatible with R9.5 basecalling"
    read line; exit 1
fi
if [ "$flowcell" == "R9.4" ] && [ "$detected_flowcell" == "FLO-MIN107" ]; then
    echo "Error: R9.5 flowcell detected - not compatible with R9.4 basecalling"
    read line; exit 1
fi
if [ "$flowcell" == "R9.4.1" ] && [ "$detected_flowcell" == "FLO-MIN107" ]; then
    echo "Error: R9.5 flowcell detected - not compatible with R9.4.1 basecalling"
    read line; exit 1
fi


# Make sure the output directory is ready to go.
mkdir -p $output_dir
if [ ! -z "$(ls -A $output_dir)" ]; then
    echo "Error: the output directory "$output_dir" is not empty"
    echo "       please move/delete existing basecalling before running"
    read line; exit 1
fi


# Find the subdirectories of demultiplexed reads for separate basecalling.
if [ ! -d $binned_read_dir ]; then
    echo "Error: "$binned_read_dir" does not exist"
    read line; exit 1
fi
bin_dirs=$(find $binned_read_dir -mindepth 1 -maxdepth 1 -type d | grep -v "unclassified" | sort)
if [[ -z "${bin_dirs// }" ]]; then
    echo "Error: "$binned_read_dir" has no barcode subdirectories"
    read line; exit 1
fi
printf "\nFound the following directories to basecall:\n"
for bin_dir in $bin_dirs; do
    printf "  "$bin_dir"\n"
done
printf "\n"


# Create the file which will hold per-barcode stats.
stats_file="$output_dir"/read_stats.txt
printf "Barcode\tRead_count\tRead_bases\tN50\n" > "$stats_file"


for bin_dir in $bin_dirs; do
    printf "\nBasecalling "$bin_dir"\n"
    echo "----------------------------------------------------------------------"
    b=$(basename $bin_dir)
    out_dir="$output_dir"/"$b"
    guppy_basecaller --config "$config" --device auto -i "$bin_dir" -s "$out_dir"
    guppy_barcoder -i "$out_dir" -s "$out_dir" --arrangements_files barcode_arrs_nb.cfg --min_score 50

    out_file="$out_dir"/"$b"_untrimmed.fastq.gz
    printf "\nFiltering reads by barcode\n"
    ~/MinION-desktop/filter_by_guppy_barcode.py "$out_dir"/barcoding_summary.txt "$b" "$out_dir"/*.fastq | pigz > "$out_file"
    rm -r "$out_dir"/*.fastq
    printf "\n"

    printf "Trimming reads with Porechop\n"
    porechop_out="$out_dir"/"$b"_trimmed.fastq.gz
    porechop_log="$out_dir"/"$b"_porechop.log
    porechop --check_reads 100 --discard_middle -i "$out_file" 2> "$porechop_log" | pigz > "$porechop_out"

    ~/MinION-desktop/fastq_count "$porechop_out" >> "$stats_file"

    printf "\n"
done

printf "\n\nAll finished!\n\n"
read line
