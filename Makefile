all:kseq.h fast_count.cpp
		g++ -g -O2 fast_count.cpp -o fast_count -lz

clean:
		rm -f *.o fast_count