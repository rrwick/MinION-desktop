# MinION desktop

This repo contains scripts and programs for the Holt Lab's MinION-running computer. This computer is a fairly beefy desktop that (thanks to its GTX 1080 GPU) can demultiplex with Deepbinner and basecall with Guppy.

The contents of these repo are custom-tailored to our setup and workflow (i.e. I make no promises that they may work for you), but I made them publicly available in case others are interested!



### Setup

The [setup.md](setup.md) file contains my crude notes on setting up the software on the desktop. They are not exhaustive and some of the steps are applicable only to our computer/environment.



### start_deepbinner.sh

The [start_deepbinner.sh](start_deepbinner.sh) script can be run during a MinION run to demultiplex the reads in real time.

To make it easy to run, I made this desktop file for the Ubuntu desktop:
```
[Desktop Entry]
Version=1.0
Exec=/home/holt-ont/MinION-desktop/start_deepbinner.sh
Name=Start Deepbinner
GenericName=Start Deepbinner
Comment=Start running Deepbinner on MinKNOW's reads
Encoding=UTF-8
Terminal=true
Type=Application
```



### basecall_reads.sh

The [basecall_reads.sh](basecall_reads.sh) script is intended to be executed after a run finishes. It does the following steps:
* Basecalls each of Deepbinner's barcode directories using Guppy.
* Runs Guppy's barcoder and saves reads where Deepbinner and Guppy agree on the barcode (using the [filter_by_guppy_barcode.py](filter_by_guppy_barcode.py) script).
* Runs Porechop on the reads (only for simple adapter-trimming, not demultiplexing).
* Saves some read stats to file using the `fastq_count` program (more details below).

This script takes only one argument: the flowcell type. It must be `R9.4`, `R9.4.1` or `R9.5`.

To make this script easy to run, I made a few desktop files (one for each flowcell type) to put on the Ubuntu desktop that look like this:
```
[Desktop Entry]
Version=1.0
Exec=/home/holt-ont/MinION-desktop/basecall_reads.sh R9.4.1
Name=Basecall reads R9.4.1
GenericName=Basecall reads R9.4.1
Comment=Basecall Deepbinner's reads using Guppy
Encoding=UTF-8
Terminal=true
Type=Application
```


### fastq_count

This is a little C program that reports some basic stats on a fastq file: the number of reads, the total size (in bp) and the N50 size. I threw it together using [this example](https://bioinformatics.stackexchange.com/a/937) as a starting point. Because it uses the wonderful[kseq.h](http://attractivechaos.github.io/klib/#Kseq%3A%20stream%20buffer%20and%20FASTA%2FQ%20parser) header file, it's very fast.

To build it, just run `make`.



### License

[GNU General Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.html)
