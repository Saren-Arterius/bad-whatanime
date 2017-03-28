#!/usr/bin/env python3
from sys import argv
import bwa
from bwa import BWA

if __name__ == '__main__':
    b = bwa.BWA(__file__)
    if argv[1] == 'g':
        b.index_anime(argv[2])
    elif argv[1] == 'f':
        results = b.find_anime(argv[2])
        for result in results[:5]:
            print("{}%: '{}' | {}s".format(round((1 - result['val'] / bwa.FIND_BOUND) * 10000) / 100, result[
                  'id'], round(result['position_second'] * 100) / 100))
