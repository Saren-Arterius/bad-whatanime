#!/usr/bin/env python3
from sys import argv
from PIL import Image
from os import listdir
from subprocess import call
import binascii
import os.path

BASE_DIR = '/tmp/test'


def diff(a, b):
    return sum(a[i] != b[i] for i in range(len(a)))

if __name__ == "__main__":
    call(['ffmpeg', '-y', '-i', argv[1], '-vf',
          'scale=8:8', '-pix_fmt', 'rgb8', argv[1] + '.bmp'])
    im = Image.open(argv[1] + '.bmp')
    hex_b = str(binascii.hexlify(bytearray(im.getdata())))
    min_diff = 128
    min_diff_file = None
    for f in listdir(BASE_DIR):
        f = os.path.join(BASE_DIR, f)
        s = str(open(f, 'rb').read())
        try:
            val = diff(s, hex_b)
            if val < min_diff:
                min_diff = val
                min_diff_file = f
        except:
            print(f)
    print(min_diff, min_diff_file)
    print(str(open(min_diff_file, 'rb').read()))
    print(hex_b)
