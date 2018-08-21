all:kseq.h fastq_count.cpp
		g++ -g -O2 fastq_count.cpp -o fastq_count -lz

clean:
		rm -f *.o fastq_count