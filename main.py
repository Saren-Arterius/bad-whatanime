#!/usr/bin/env python3
from sys import argv
from bwa import BWA

if __name__ == '__main__':
    bwa = BWA(__file__)
    if argv[1] == 'g':
        bwa.index_anime(argv[2])
    elif argv[1] == 'f':
        results = bwa.find_anime(argv[2])
        for result in results[:5]:
            print("{}%: '{}' | {}s".format(round((1 - result['val'] / 16384) * 10000) / 100, result[
                  'id'], round(result['position_second'] * 100) / 100))
