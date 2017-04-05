#!/usr/bin/env python3
from datetime import timedelta
from math import floor
from sys import argv
import bwa

if __name__ == '__main__':
    if argv[1] == 'g':
        bwa.index_anime(argv[2])
    elif argv[1] == 'f':
        results = bwa.find_anime(argv[2])
        for result in results[:5]:
            print("{}%: '{}' | {}s ({})".format(round((1 - result['val'] / bwa.FIND_BOUND) * 10000) / 100, result[
                  'id'], timedelta(seconds=floor(result['position_second'])), result['position_frame']))
