#!/usr/bin/env python3
"""Remove a fixed-position watermark from frames by masking it and inpainting.

    python3 scripts/dewatermark.py mask.png in_dir out_dir

mask.png: white where the mark (text, outline and drop shadow) sits, same size as
the frames. Build it once from the clip: the temporal median of high-passed frames
shows the text; frames that are black under it give the white part, frames that
are white give the shadow; threshold, close and dilate by ~5 px.
Alpha-unblending was tried first and left ghost text: the mark's strength varies
between frames (encoder, fades), so plain inpainting is cleaner.
"""
import sys, glob, os
import cv2

def clean(img, mask, radius=8):
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)

if __name__ == '__main__':
    mask = (cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE) > 127).astype('uint8')
    src, dst = sys.argv[2], sys.argv[3]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.png'))):
        cv2.imwrite(os.path.join(dst, os.path.basename(f)), clean(cv2.imread(f), mask))
