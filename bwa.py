#!/usr/bin/env python3
from __main__ import __file__ as main_file
from multiprocessing import Pool, cpu_count
from subprocess import call, check_output
from PIL import Image
from os import listdir, remove, makedirs
from os.path import basename, splitext, join, isfile, dirname, realpath
from shutil import rmtree
from sys import executable
from math import sqrt
from struct import unpack
from time import time, sleep
import colorsys
import bson

BASE_DIR = join(realpath(dirname(main_file)), 'bwa')
TMP_DIR = '/tmp/bwa'
VALUE_TORLENCE_FACTOR = 0.5
INDEX_BOUND = 2 * ((8 * 8) * 16) + VALUE_TORLENCE_FACTOR * ((8 * 8) * 16)
FIND_BOUND = INDEX_BOUND
HUE_DIFF_ALLOWANCE = 1
CANDIDATES_LEFTOVER_THRESHOLD = 50
DUPLICATE_FRAME_THRESHOLD = 0.05
INDEX_COLS = [i * 9 for i in range(8)] + [i * 7 for i in range(1, 9)]  # backslash + forward slash
index_cols_map = {}
for i, val in enumerate(INDEX_COLS):
    index_cols_map[val] = i
"""
def compress_bytes(bs):
    compressed = b''
    for i in range(int(len(bs) / 2)):
        compressed += bytes([(bs[i * 2] << 4) + bs[i * 2 + 1]])
    return compressed


def decompress_bytes(bs):
    decompressed = b''
    for b in bs:
        decompressed += bytes([b >> 4]) + bytes([b & 15])
    return decompressed


def compress_data_table(dt):
    for frame in dt:
        for i, hsv_array in enumerate(frame[1]):
            frame[1][i] = compress_bytes(hsv_array)


def decompress_data_table(dt):
    for frame in dt:
        for i, hsv_array in enumerate(frame[1]):
            frame[1][i] = decompress_bytes(hsv_array)
"""


def hsv_array_diff(a, b):
    diff = 0
    for i in range(len(a[0])):
        hd, sd, vd = abs(a[0][i] - b[0][i]), abs(a[1][i] - b[1][i]), abs(a[2][i] - b[2][i])
        if hd > HUE_DIFF_ALLOWANCE:
            return INDEX_BOUND
        diff += hd + sd + VALUE_TORLENCE_FACTOR * vd
    return diff


def rgb_to_hsv_16(rgb):
    return tuple(map(lambda v: round(v * 15), colorsys.rgb_to_hsv(*map(lambda c: c / 255, rgb))))


def tuples_to_hsv_array(tuples):
    return [bytes([tuples[j][i] for j in range(len(tuples))]) for i in range(3)]


def to_data(bmp_file):
    im = Image.open(bmp_file)
    hsv_array = [rgb_to_hsv_16(rgb) for rgb in im.getdata()]
    return tuples_to_hsv_array(hsv_array)


def move_front(s, i):
    arr = list(s)
    arr.insert(0, arr.pop(i))
    return bytes(arr)


def generate_indice(col, frame_table, t):
    # print(col, frame_table[0:2])
    s = sorted(list(range(len(frame_table))),
                  key=lambda i: move_front(frame_table[i][1][t], col))
    return s


def find_candidate_indice(db, target_hsv_array):
    if len(db['h_indice'][0]) < CANDIDATES_LEFTOVER_THRESHOLD:
        return candidates
    candidates = None
    # Binary search
    for t, name in enumerate(['h_indice']):
        for col in INDEX_COLS:
            col_i = index_cols_map[col]
            """
            col_i = 12
            col = INDEX_COLS[col_i]
            """
            indice = db[name][col_i]
            # print(col, col_i)
            target_value = target_hsv_array[t][col]
            # Find satisfy min index
            """
            if col_i == 12:
                for mi, i in enumerate(indice):
                    print(i, db['data_table'][i][1][t][col], db['data_table'][i][1][t])
            """
            def binary_search(offset):
                start = 0
                end = len(indice) - 1
                while start != end:
                    mid = (start + end) // 2
                    value = db['data_table'][indice[mid]][1][t][col]
                    """
                    if col_i == 12:
                        print(start, mid, end, value, target_value)
                        sleep(1)
                    """
                    if offset < 0:
                        if mid == start and end - start == 1:
                            start = end
                        elif value >= target_value + offset:
                            end = mid
                        else:
                            start = mid
                    else:
                        if mid == start and end - start == 1:
                            start = end
                        elif value <= target_value + offset:
                            start = mid
                        else:
                            end = mid
                """
                if col_i == 12:
                    print('return', start)
                """
                return start
            left, right = binary_search(-HUE_DIFF_ALLOWANCE), binary_search(HUE_DIFF_ALLOWANCE)
            """
            if col_i == 12:
                print("lr", left, right, indice[left:right + 1], target_value)
            """
            if candidates is None:
                candidates = set(indice[left:right + 1])
            else:
                candidates &= set(indice[left:right + 1])
            if len(candidates) < CANDIDATES_LEFTOVER_THRESHOLD:
                print(col, name)
                return candidates
    return candidates


def find_similar(data_file, target_hsv_array):
    similarities = []
    id = splitext(basename(data_file))[0]
    db = bson.loads(open(data_file, 'rb').read())
    # decompress_data_table(db['data_table'])
    indice = find_candidate_indice(db, target_hsv_array)
    for i in indice:
        frame_i, hsv_array = db['data_table'][i]
        val = hsv_array_diff(target_hsv_array, hsv_array)
        # print(i, frame_i, val)
        if val < FIND_BOUND and (len(similarities) == 0 or val < similarities[-1]['val']):
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
          'scale=8:8', '-pix_fmt', 'rgb24', tmp_bmp])
    im = Image.open(tmp_bmp)
    hsv_array = tuples_to_hsv_array(
        [rgb_to_hsv_16(rgb) for rgb in im.getdata()])
    remove(tmp_bmp)
    with Pool(processes=1) as pool:
        results = pool.starmap(find_similar, [(join(BASE_DIR, data_file), hsv_array) for data_file in listdir(
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
          'scale=8:8', '-pix_fmt', 'bgr24', bmp_dir + '/%d.bmp'])
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
            val = hsv_array_diff(data_array[left], data_array[
                right]) / INDEX_BOUND
            # print(left, right, val)
            if val >= DUPLICATE_FRAME_THRESHOLD:
                data_table.append([str(left), data_array[left]])
                left = right
                break
            right += 1
    if len(data_table) == 0:
        data_table.append(["0", data_array[0]])
    """
    for i, arr in enumerate(data_table):
        print(i, arr)
    """
    print('Indexed frame count:', len(data_table))
    with Pool(processes=cpu_count()) as pool:
        h_indice = pool.starmap(
            generate_indice, [(i, data_table, 0) for i in INDEX_COLS])
        """
        s_indice = pool.starmap(
            generate_indice, [(i, data_table, 1) for i in INDEX_COLS])
        v_indice = pool.starmap(
            generate_indice, [(i, data_table, 2) for i in INDEX_COLS])
        """
    """
    print('1st column h_indice', h_indice[0])
    print('2nd column s_indice', s_indice[1])
    print('3th column v_indice', v_indice[2])
    """
    """
    for mi, i in enumerate(h_indice[0]):
        print(i, data_table[i][1][0][0], data_table[i][1][0])
    """
    makedirs(BASE_DIR, exist_ok=True)
    # compress_data_table(data_table)
    data = {
        'fps': fps,
        'data_table': data_table,
        'h_indice': h_indice
    }
    open(join(BASE_DIR, video_id + '.dat'), 'wb').write(bson.dumps(data))
    rmtree(bmp_dir)
