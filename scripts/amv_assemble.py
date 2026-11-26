#!/usr/bin/env python3
"""Join rendered links back into one frame sequence and encode the master mp4.

    python3 scripts/amv_assemble.py WORK out.mp4 [--fps 60]

Reads WORK/links.json and WORK/render/linkNNN/kNNNN.png, links them as
WORK/final/rNNNNN.png (global frame numbers), checks each rendered drawing against
its cel preview (flags < 24 dB = a Desmos rendering fault) and encodes H.264.
"""
import json, os, sys, subprocess, argparse
import numpy as np, cv2

ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('out'); ap.add_argument('--fps', type=float, default=60)
a = ap.parse_args()
links = json.load(open(os.path.join(a.work, 'links.json')))
dup = json.load(open(os.path.join(a.work, 'dupmap.json')))
final = os.path.join(a.work, 'final'); os.makedirs(final, exist_ok=True)
missing, bad = [], []
for L in links:
    rd = L['link'].replace('/links/link', '/render/link').replace('.json', '')
    for k, i in enumerate(range(L['from'], L['to'] + 1), 1):
        src = os.path.join(rd, f'k{k:04d}.png'); dst = os.path.join(final, f'r{i:05d}.png')
        if not os.path.exists(src): missing.append(i); continue
        if os.path.lexists(dst): os.remove(dst)
        os.symlink(src, dst)
        n = f'r{i:05d}.png'
        if dup[n] == n:  # check each drawing once
            pv = os.path.join(a.work, 'slots', n.replace('.png', '_preview.png'))
            r = cv2.resize(cv2.imread(src), (960, 540), interpolation=cv2.INTER_AREA).astype(np.float32)
            m = ((r - cv2.imread(pv).astype(np.float32)) ** 2).mean()
            ps = 99 if m == 0 else 10 * np.log10(255 ** 2 / m)
            if ps < 24: bad.append((i, round(float(ps), 1)))
print('missing', len(missing), missing[:20]); print('render faults', len(bad), bad[:40])
json.dump({'missing': missing, 'bad': bad}, open(os.path.join(a.work, 'assemble.json'), 'w'))
if not missing:
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(a.fps), '-start_number', '0',
                    '-i', os.path.join(final, 'r%05d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '16', '-preset', 'slow', a.out], check=True)
    print('wrote', a.out)
