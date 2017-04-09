#!/usr/bin/env python3
from __main__ import __file__ as main_file
from multiprocessing import Pool, cpu_count
from subprocess import call, check_output
from PIL import Image
from os import listdir, remove, makedirs
from os.path import basename, splitext, join, isfile, dirname, realpath
from shutil import rmtree
import colorsys
import msgpack

BASE_DIR = join(realpath(dirname(main_file)), 'bwa')
TMP_DIR = '/tmp/bwa'
INDEX_BOUND = 3 * ((8 * 8) * 16)
FIND_BOUND = INDEX_BOUND
VAL_DIFF_ALLOWANCE = 1
CANDIDATES_LEFTOVER_THRESHOLD = 50
# backslash + forward slash
INDEX_COLS = [i * 9 for i in range(8)] + [i * 7 for i in range(1, 9)]
ACTIVE_HSV_INDICE_NAME = 'v_indice'
ACTIVE_HSV_INDICE_NUM = 2 # Index using value

index_cols_map = {}
for i, val in enumerate(INDEX_COLS):
    index_cols_map[val] = i


def hsv_array_diff(a, b):
    diff = 0
    for i in range(len(a[0])):
        hd, sd, vd = abs(a[0][i] - b[0][i]), abs(a[1][i] - b[1][i]), abs(a[2][i] - b[2][i])
        if i in INDEX_COLS and vd > VAL_DIFF_ALLOWANCE:
            return INDEX_BOUND
        diff += hd + sd + vd
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
    s = sorted(list(range(len(frame_table))),
               key=lambda i: move_front(frame_table[i][1][t], col))
    return s


def find_candidate_indice(db, target_hsv_array):
    name = ACTIVE_HSV_INDICE_NAME.encode()
    if len(db[name][0]) < CANDIDATES_LEFTOVER_THRESHOLD:
        return db[name][0]
    candidates = None
    for col in INDEX_COLS:
        col_i = index_cols_map[col]
        indice = db[name][col_i]
        target_value = target_hsv_array[ACTIVE_HSV_INDICE_NUM][col]
        def binary_search(offset):
            start = 0
            end = len(indice) - 1
            while start != end:
                mid = (start + end) // 2
                value = db[b'data_table'][indice[mid]][1][ACTIVE_HSV_INDICE_NUM][col]
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
            return start
        if target_value <= 1:
            left = 0
        else:
            left = binary_search(-VAL_DIFF_ALLOWANCE)
        if target_value >= 14:
            right = len(indice) - 1
        else:
            right = binary_search(VAL_DIFF_ALLOWANCE)
        if candidates is None:
            candidates = set(indice[left:right + 1])
        else:
            candidates &= set(indice[left:right + 1])
        if len(candidates) < CANDIDATES_LEFTOVER_THRESHOLD:
            return candidates
    return candidates


def find_similar(data_file, target_hsv_array):
    similarities = []
    id = splitext(basename(data_file))[0]
    db = msgpack.unpackb(open(data_file, 'rb').read(), use_list=False)
    indice = find_candidate_indice(db, target_hsv_array)
    for i in indice:
        frame_i, hsv_array = db[b'data_table'][i]
        val = hsv_array_diff(target_hsv_array, hsv_array)
        if val < FIND_BOUND and (len(similarities) == 0 or val < similarities[-1]['val']):
            similarities.append({
                'position_second': int(frame_i) / db[b'fps'],
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
    with Pool(processes=cpu_count()) as pool:
        results = pool.starmap(find_similar, [(join(BASE_DIR, data_file), hsv_array) for data_file in listdir(
            BASE_DIR) if isfile(join(BASE_DIR, data_file)) and splitext(data_file)[1] == '.dat'])
    results = [item for sublist in results for item in sublist]
    results.sort(key=lambda k: k['val'])
    return results


def index_anime(video_file):
    fps = get_fps(video_file)
    video_id = splitext(basename(video_file))[0]
    bmp_dir = join(TMP_DIR, video_id)
    try:
        makedirs(bmp_dir)
        call(['ffmpeg', '-y', '-i', video_file, '-vf',
              'scale=8:8', '-pix_fmt', 'bgr24', bmp_dir + '/%d.bmp'])
    except:
        print('Using existing bmp data')
    with Pool(processes=cpu_count()) as pool:
        data_array = pool.map(to_data, (join(bmp_dir, i)
                                        for i in sorted(listdir(bmp_dir), key=lambda f: int(f.split('.')[0]))))
    data_table = []
    left = 0
    right = 0
    l = len(data_array)
    from time import sleep
    data_table.append(["0", data_array[0]])
    while right != l:
        right = left + 1
        while True:
            if right == l:
                break
            val = hsv_array_diff(data_array[left], data_array[right])
            if val == INDEX_BOUND:
                data_table.append([str(left), data_array[left]])
                left = right
                break
            right += 1
    if len(data_table) == 0:
        data_table.append(["0", data_array[0]])
    print('Indexed frame count:', len(data_table))
    with Pool(processes=cpu_count()) as pool:
        indice = pool.starmap(
            generate_indice, [(i, data_table, ACTIVE_HSV_INDICE_NUM) for i in INDEX_COLS])
    makedirs(BASE_DIR, exist_ok=True)
    data = {
        'fps': fps,
        'data_table': data_table,
        ACTIVE_HSV_INDICE_NAME: indice
    }
    open(join(BASE_DIR, video_id + '.dat'), 'wb').write(msgpack.packb(data))
    # rmtree(bmp_dir)
