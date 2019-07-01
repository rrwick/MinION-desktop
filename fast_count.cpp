#include <zlib.h>
#include <stdio.h>
#include "kseq.h"
#include <vector>
#include <functional>   // std::greater
#include <algorithm>

KSEQ_INIT(gzFile, gzread)

int main(int argc, char *argv[])
{
    gzFile fp;
    kseq_t *seq;
    int l;
    if (argc == 1) {
        fprintf(stderr, "Usage: %s <in.seq>\n", argv[0]);
        return 1;
    }
    fp = gzopen(argv[1], "r");
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

    // Find the N50.
    std::sort(readLengths.begin(), readLengths.end(), std::greater<long>());
    long long target = totalLen / 2;
    long long lenSoFar = 0;
    int n50 = 0;
    for (int i = 0; i < seqCount; ++i) {
        lenSoFar += readLengths[i];
        if (lenSoFar >= target) {
            n50 = readLengths[i];
            break;
        }
    }

    printf("%s\t%d\t%lld\t%d\n", argv[1], seqCount, totalLen, n50);
    return 0;
}
