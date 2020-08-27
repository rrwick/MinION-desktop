#include <zlib.h>
#include <stdio.h>
#include "kseq.h"
#include <vector>
#include <functional>   // std::greater
#include <algorithm>

KSEQ_INIT(gzFile, gzread)


void print_header() {
    printf("filename\tseq_count\ttotal_length\tn99_length\tn90_length\tn50_length\tn10_length\tn01_length\n");
}

void process_one_file(char* f) {
    gzFile fp;
    kseq_t *seq;
    int l;
    fp = gzopen(f, "r");
    seq = kseq_init(fp);
    int seqCount = 0;
    long long totalLen = 0;
    std::vector<int> readLengths;
    while ((l = kseq_read(seq)) >= 0) {
        seqCount = seqCount + 1;
        int readLen = int(strlen(seq->seq.s));
        readLengths.push_back(readLen);
        totalLen += readLen;
    }
    kseq_destroy(seq);
    gzclose(fp);

    // Find the N01, N10, N50, N90 and N99.
    std::sort(readLengths.begin(), readLengths.end(), std::greater<long>());
    long long target_01 = totalLen / 100;
    long long target_10 = totalLen / 10;
    long long target_50 = totalLen / 2;
    long long target_90 = totalLen * 9 / 10;
    long long target_99 = totalLen * 99 / 100;
    long long lenSoFar = 0;
    int n01 = 0, n10 = 0, n50 = 0, n90 = 0, n99 = 0;
    bool set_01 = false, set_10 = false, set_50 = false, set_90 = false, set_99 = false;
    for (int i = 0; i < seqCount; ++i) {
        lenSoFar += readLengths[i];
        if (lenSoFar >= target_01 && !set_01) {
            n01 = readLengths[i];
            set_01 = true;
        }
        if (lenSoFar >= target_10 && !set_10) {
            n10 = readLengths[i];
            set_10 = true;
        }
        if (lenSoFar >= target_50 && !set_50) {
            n50 = readLengths[i];
            set_50 = true;
        }
        if (lenSoFar >= target_90 && !set_90) {
            n90 = readLengths[i];
            set_90 = true;
        }
        if (lenSoFar >= target_99 && !set_99) {
            n99 = readLengths[i];
            set_99 = true;
        }
        if (set_01 && set_10 && set_50 && set_90 && set_99) {
            break;
        }
    }
    printf("%s\t%d\t%lld\t%d\t%d\t%d\t%d\t%d\n", f, seqCount, totalLen, n99, n90, n50, n10, n01);
}

int main(int argc, char *argv[]) {
    if (argc == 1) {
        print_header();
        return 0;
    }
    for (int i = 1; i < argc; ++i) {
        process_one_file(argv[i]);
    }
}
