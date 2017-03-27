#!/usr/bin/env python3
from PIL import Image
from multiprocessing import Pool
from os import listdir
import binascii
import os.path

BASE_DIR = '/tmp/test'

def to_txt(bmp_file):
    f = os.path.join(BASE_DIR, bmp_file)
    im = Image.open(f)
    hex_b = binascii.hexlify(bytearray(im.getdata()))
    open(f + '.txt', 'wb').write(hex_b)

if __name__ == "__main__":
    with Pool(processes=56) as pool:
        pool.map(to_txt, listdir(BASE_DIR))
