# MinION desktop

This repo contains scripts and programs for the Holt Lab's MinION-running computer. They are custom-tailored to our workflow, but may still be of interest to others who are doing similar things!



### fastq_count

This is a little C program that reports some basic stats on a fastq file: the number of reads, the total size (in bp) and the N50 size. I threw it together using [this example](https://bioinformatics.stackexchange.com/a/937) as a starting point. Because it uses the wonderful[kseq.h](http://attractivechaos.github.io/klib/#Kseq%3A%20stream%20buffer%20and%20FASTA%2FQ%20parser) header file, it's very fast.



### License

[GNU General Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.html)