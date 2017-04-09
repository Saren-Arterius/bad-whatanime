# bad-whatanime
Try to replicate whatanime

# Dependencies
## OS
- POSIX system
- ffmpeg

## Python
- Pillow
- msgpack-python

# Usage

## Compiling using cython
`python3 setup.py build_ext --inplace`

## Indexing video
`python3 main.py g xxx.mp4`

## Find video from photo
`python3 main.py f xxx-frame1.jpg`

### Example output

	98.89%: 'Kemono Friends - 12' | 0:22:07s (31837)
	98.05%: 'Kemono Friends - 12' | 0:22:04s (31768)

