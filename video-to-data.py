#!/usr/bin/env python3
from multiprocessing import Pool
from subprocess import call, check_output
from PIL import Image
from sys import argv
from os import listdir, makedirs
from os.path import basename, splitext, join, dirname
from shutil import rmtree
import binascii
import bson

BASE_DIR = join(dirname(__file__), 'bwa')


def to_data(bmp_file):
    im = Image.open(bmp_file)
    return bytes(im.getdata())


def get_fps(video_file):
    return float(check_output(['mediainfo', '--inform=Video;%FrameRate%',
                               video_file], universal_newlines=True).strip())

if __name__ == '__main__':
    fps = get_fps(argv[1])
    video_id = splitext(basename(argv[1]))[0]
    bmp_dir = join(BASE_DIR, video_id)
    makedirs(bmp_dir, exist_ok=True)
    call(['ffmpeg', '-y', '-i', argv[1], '-vf',
          'scale=8:8', '-pix_fmt', 'rgb8', bmp_dir + '/%d.bmp'])
    with Pool(processes=56) as pool:
        data_array = pool.map(to_data, (join(bmp_dir, i)
                                        for i in sorted(listdir(bmp_dir), key=lambda f: int(f.split('.')[0]))))
    open(join(BASE_DIR, video_id + '.dat'),
         'wb').write(bson.dumps({'fps': fps, 'data_array': data_array}))
    rmtree(bmp_dir)
