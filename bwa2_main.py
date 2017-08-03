#!/usr/bin/env python3
from multiprocessing import Pool
from subprocess import check_output, call
from binascii import unhexlify
from datetime import timedelta
from os.path import basename, splitext, join, isfile, dirname, realpath
from shutil import rmtree
from time import time, strftime
from math import floor
from sys import argv
from PIL import Image
from os import listdir, makedirs, remove
import imagehash
import redis

TMP_DIR = '/tmp/bwa2'
# DEGRADE_TO = None
DEGRADE_TO = '16:16'
hash_db = redis.StrictRedis(
    host='localhost', port=6379, db=10, decode_responses=True)
meta_db = redis.StrictRedis(
    host='localhost', port=6379, db=11, decode_responses=True)


def log(msg, label='INFO'):
    print('[{}] [{}] {}'.format(strftime('%Y-%m-%d %H:%M:%S'), label, msg))


def get_fps(video_file):
    return float(check_output(['mediainfo', '--inform=Video;%FrameRate%',
                               video_file], universal_newlines=True).strip())


def get_hash(filename):
    # return unhexlify(str(imagehash.phash(Image.open(filename)))) + unhexlify(str(imagehash.dhash(Image.open(filename))))
    return unhexlify(str(imagehash.phash(Image.open(filename))))


def index_anime(video_file):
    video_name = splitext(basename(video_file))[0]
    bmp_dir = join(TMP_DIR, video_name)

    log('Splitting video file to .bmp frames...')
    try:
        makedirs(bmp_dir)
        if DEGRADE_TO:
            call(['ffmpeg', '-loglevel', 'panic', '-y', '-i', video_file, '-vf',
                  'scale={}'.format(DEGRADE_TO), bmp_dir + '/%d.bmp'])
        else:
            call(['ffmpeg', '-loglevel', 'panic', '-y',
                  '-i', video_file, bmp_dir + '/%d.bmp'])
    except Exception as e:
        log('Using existing bmp data', 'WARN')
    files = list(map(lambda f: bmp_dir + '/' + f, listdir(bmp_dir)))

    log('Generating hashes for {} images...'.format(len(files)))
    with Pool() as p:
        results = p.map(get_hash, files)

    log('Generating metadata...')
    frames = {}
    video_id = meta_db.get('name:' + video_name)
    if video_id is None:
        video_id = meta_db.incr('id_incr')
        meta_db.set('name:' + video_name, video_id)
    else:
        log('Using existing ID {} for {}'.format(video_id, video_name))
    fps = get_fps(video_file)
    meta_db.hset(video_id, 'name', video_name)
    meta_db.hset(video_id, 'fps', fps)

    log("ID: {}, Video name: {}, fps: {}".format(video_id, video_name, fps))
    for i in range(len(files)):
        frames[results[i]] = str(video_id) + ',' + \
            splitext(basename(files[i]))[0]

    log('Saving {} frames to redis...'.format(len(frames)))
    for k, v in frames.items():
        hash_db.set(k, v)
    rmtree(bmp_dir)
    log('Done!')


def find_anime(image_file):
    tmp_file = None
    if DEGRADE_TO:
        tmp_file = join(TMP_DIR, str(time()) + '.bmp')
        call(['ffmpeg', '-loglevel', 'panic', '-y', '-i', image_file,
              '-vf', 'scale={}'.format(DEGRADE_TO), tmp_file])
        image_file = tmp_file
    hash = get_hash(image_file)
    info = hash_db.get(hash)
    if info is None:
        log('No result found for {}, hash={}'.format(image_file, hash))
        return
    video_id, frame = info.split(',')
    name, fps = meta_db.hget(video_id, 'name'), meta_db.hget(video_id, 'fps')
    log("'{}' | {}s ({})".format(name, timedelta(
        seconds=floor(int(frame) / float(fps))), frame), 'RESULT')
    if tmp_file is not None:
        remove(tmp_file)


if __name__ == "__main__":
    ext = splitext(argv[1])[1]
    if ext.lower() in ['.png', '.bmp', '.jpg', '.jpeg', '.tiff', '.gif']:
        find_anime(argv[1])
    else:
        index_anime(argv[1])
