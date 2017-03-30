#!/usr/bin/env python3
from multiprocessing import Pool, cpu_count
from subprocess import call, check_output
from PIL import Image
from os import listdir, remove, makedirs
from os.path import basename, splitext, join, isfile, dirname, realpath
from shutil import rmtree
from sys import executable
from math import sqrt
from __main__ import __file__ as main_file
import bson

BASE_DIR = join(realpath(dirname(main_file)), 'bwa')
TMP_DIR = '/tmp/bwa'
FIND_BOUND = 768
INDEX_BOUND = 768
# DUPLICATE_FRAME_THRESHOLD = 0.1
DUPLICATE_FRAME_THRESHOLD = 0.07


def rgb(i):
    red = i >> 5
    blue = (i >> 2) & 7
    green = i & 7
    return red, green, blue


def color_array_diff(a, b):
    diff = 0
    for i in range(len(a)):
        ar, ag, ab = rgb(a[i])
        br, bg, bb = rgb(b[i])
        diff += sqrt((ar - br) * (ar - br) + (ag - bg)
                     * (ag - bg) + (ab - bb) * (ab - bb))
    return diff


def fast_color_array_diff(a, b):
    return sum(abs(a[i] - b[i]) for i in range(len(a)))


def to_data(bmp_file):
    im = Image.open(bmp_file)
    return bytes(im.getdata())

def generate_indice(col, frame_array):
    # print(col, frame_array[0:2])
    move_front = lambda s, i: bytes(s[i]) + s[:i] + s[i+1:]
    indice = list(range(len(frame_array)))
    indice.sort(key=lambda i: move_front(frame_array[i][1], col), reverse=True)
    return indice

def find_similar(data_file, target):
    similarities = [{'val': FIND_BOUND + 1}]
    id = splitext(basename(data_file))[0]
    db = bson.loads(open(data_file, 'rb').read())
    for frame_i, frame_bytes in db['data_table'].items():
        val = color_array_diff(target, frame_bytes)
        if val < similarities[-1]['val']:
            similarities.append({
                'position_second': int(frame_i) / db['fps'],
                'position_frame': int(frame_i),
                'val': val,
                'id': id
            })
    return similarities[-3:]


def get_fps(video_file):
    return float(check_output(['mediainfo', '--inform=Video;%FrameRate%',
                               video_file], universal_newlines=True).strip())


def find_anime(bmp_file):
    makedirs(TMP_DIR, exist_ok=True)
    tmp_bmp = join(TMP_DIR, bmp_file + '.bmp')
    call(['ffmpeg', '-loglevel', 'panic', '-y', '-i', bmp_file, '-vf',
          'scale=8:8', '-pix_fmt', 'bgr8', tmp_bmp])
    im = Image.open(tmp_bmp)
    b = bytes(im.getdata())
    remove(tmp_bmp)
    with Pool(processes=cpu_count()) as pool:
        results = pool.starmap(find_similar, [(join(BASE_DIR, data_file), b) for data_file in listdir(
            BASE_DIR) if isfile(join(BASE_DIR, data_file)) and splitext(data_file)[1] == '.dat'])
    results = [item for sublist in results for item in sublist]
    results.sort(key=lambda k: k['val'])
    return results

def index_anime(video_file):
    fps = get_fps(video_file)
    video_id = splitext(basename(video_file))[0]
    bmp_dir = join(TMP_DIR, video_id)
    makedirs(bmp_dir, exist_ok=True)
    call(['ffmpeg', '-y', '-i', video_file, '-vf',
          'scale=8:8', '-pix_fmt', 'bgr8', bmp_dir + '/%d.bmp'])
    with Pool(processes=cpu_count()) as pool:
        data_array = pool.map(to_data, (join(bmp_dir, i)
                                        for i in sorted(listdir(bmp_dir), key=lambda f: int(f.split('.')[0]))))
    data_table = []
    left = 0
    right = 0
    l = len(data_array)
    while right != l:
        right = left + 1
        while True:
            if right == l:
                break
            val = color_array_diff(data_array[left], data_array[right]) / INDEX_BOUND
            if val > DUPLICATE_FRAME_THRESHOLD:
                data_table.append([str(left), data_array[left]])
                left = right
                break
            right += 1

    print('First 2 frame data', data_array[:2])
    with Pool(processes=cpu_count()) as pool:
        indice = pool.starmap(generate_indice, [(i, data_table) for i in range(64)])
    print('First 2 column indice', indice[:2])
    makedirs(BASE_DIR, exist_ok=True)
    open(join(BASE_DIR, video_id + '.dat'),
         'wb').write(bson.dumps({'fps': fps, 'data_table': data_table, 'indice': indice}))
    rmtree(bmp_dir)
