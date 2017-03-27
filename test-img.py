#!/usr/bin/env python3
from multiprocessing import Pool
from subprocess import call
from PIL import Image
from sys import argv
from os import listdir, remove, makedirs
from os.path import basename, splitext, join, isfile
import bson

BASE_DIR = '/tmp/bwa'


def diff(a, b):
    return sum(abs(a[i] - b[i]) for i in range(len(a)))


def find_similar(data_file, target):
    similarities = [{'val': 16385}]
    id = splitext(basename(data_file))[0]
    db = bson.loads(open(data_file, 'rb').read())
    for frame_i, frame_bytes in enumerate(db['data_array']):
        val = diff(b, frame_bytes)
        if val < similarities[-1]['val']:
            similarities.append({
                'position_second': frame_i / db['fps'],
                'position_frame': frame_i,
                'val': val,
                'id': id
            })
    return similarities[-3:]

if __name__ == "__main__":
    makedirs(BASE_DIR, exist_ok=True)
    tmp_bmp = join(BASE_DIR, argv[1] + '.bmp')
    call(['ffmpeg', '-y', '-i', argv[1], '-vf',
          'scale=8:8', '-pix_fmt', 'rgb8', tmp_bmp])
    im = Image.open(tmp_bmp)
    b = bytes(im.getdata())
    remove(tmp_bmp)
    with Pool(processes=56) as pool:
        results = pool.starmap(find_similar, [(join(BASE_DIR, data_file), b) for data_file in listdir(
            BASE_DIR) if isfile(join(BASE_DIR, data_file)) and splitext(data_file)[1] == '.dat'])
    results = [item for sublist in results for item in sublist]
    results.sort(key=lambda k: k['val'])
    for result in results[:5]:
        print("{}%: '{}' | {}s".format(round((1 - result['val'] / 16384) * 10000) / 100, result['id'], round(result['position_second'] * 100) / 100))
