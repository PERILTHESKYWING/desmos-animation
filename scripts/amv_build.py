#!/usr/bin/env python3
"""Whole-video pipeline: source mp4 -> cel-style Desmos links + frames for the mp4.

    python3 scripts/amv_build.py WORK --video src.mp4 --start 2 --dur 140.38 \
        --mask assets/ninjaristic_watermark_mask_1080p.png [--from F --to F] [--jobs 4]

Stages (each resumable, results cached in WORK):
  frames/      960x540 PNGs, watermark inpainted
  dupmap.json  held drawings -> first identical frame (never across a shot cut)
  shots.json   shot cuts (pixel + histogram change)
  slots/       one pickle per unique drawing: cel layers for that shot's palette
  links/       linkNN.json states, each under --budget MB, cut at shot boundaries
               where possible; links.json lists frame ranges
Then: node scripts/render_link.js / share.js per link (see research/amv-full.md).
"""
import argparse, json, os, sys, glob, pickle, subprocess
from multiprocessing import Pool
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import cel
from video2desmos import num

W, H = 960, 540

def extract(a, work):
    out = os.path.join(work, 'frames')
    if os.path.exists(os.path.join(work, 'frames.done')): return out
    os.makedirs(out, exist_ok=True)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(a.start), '-t', str(a.dur), '-i', a.video,
                    '-vf', f'scale={W}:{H}:flags=lanczos', '-start_number', '0', os.path.join(out, 'r%05d.png')], check=True)
    m = cv2.imread(a.mask, cv2.IMREAD_GRAYSCALE)
    m = (cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA) > 20).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    for f in sorted(glob.glob(os.path.join(out, '*.png'))):
        cv2.imwrite(f, cv2.inpaint(cv2.imread(f), m, 5, cv2.INPAINT_TELEA))
    open(os.path.join(work, 'frames.done'), 'w').close()
    return out

def analyse(work, frames):
    p = os.path.join(work, 'shots.json')
    if os.path.exists(p): return json.load(open(p)), json.load(open(os.path.join(work, 'dupmap.json')))
    names = sorted(os.listdir(frames))
    small = np.stack([cv2.resize(cv2.imread(os.path.join(frames, n)), (240, 135), interpolation=cv2.INTER_AREA) for n in names]).astype(np.int16)
    d = np.abs(small[1:] - small[:-1]).mean((1, 2, 3))
    hist = np.stack([np.concatenate([np.histogram(f[..., c], 16, (0, 256))[0] for c in range(3)]) for f in small]) / (240 * 135)
    hd = np.abs(hist[1:] - hist[:-1]).sum(1)
    cuts = [0]
    for i in range(len(d)):
        if (d[i] > 28 or hd[i] > 0.9) and i + 1 - cuts[-1] >= 6: cuts.append(i + 1)
    shots = [[c, (cuts[j + 1] if j + 1 < len(cuts) else len(names)) - 1] for j, c in enumerate(cuts)]
    dup, cutset, last = {}, set(cuts), None
    for i, n in enumerate(names):
        if last is None or i in cutset or np.abs(small[i] - small[last]).mean() > 0.6: last = i
        dup[n] = names[last]
    json.dump(shots, open(p, 'w')); json.dump(dup, open(os.path.join(work, 'dupmap.json'), 'w'))
    return shots, dup

def _load(path):
    return cv2.imread(path)[:, :, ::-1].copy()

def _job(args):
    frames, work, n, cen, k = args
    out = os.path.join(work, 'slots', n.replace('.png', '.pkl'))
    if os.path.exists(out): return
    img = _load(os.path.join(frames, n))
    sl, prev = cel.cel_slots(img, cen, lambda x: str(int(round(x))), lambda y: str(int(round(y))), k=k)
    if not sl: sl = [(cel.rgb(cen[:1])[0], None)]
    cv2.imwrite(out.replace('.pkl', '_preview.png'), prev[:, :, ::-1])
    pickle.dump(sl, open(out, 'wb'))

def convert(work, frames, shots, dup, jobs, rng):
    os.makedirs(os.path.join(work, 'slots'), exist_ok=True)
    tasks = []
    for s, e in shots:
        if e < rng[0] or s > rng[1]: continue
        uniq = sorted({dup[f'r{i:05d}.png'] for i in range(s, e + 1)})
        pal_p = os.path.join(work, 'slots', f'pal_{s:05d}.npz')
        if os.path.exists(pal_p):
            z = np.load(pal_p); cen, k = z['cen'], int(z['k'])
        else:
            sample = [_load(os.path.join(frames, uniq[i])) for i in np.linspace(0, len(uniq) - 1, min(8, len(uniq))).astype(int)]
            cen, k = cel.fit_palette(sample, 8)
            np.savez(pal_p, cen=cen, k=k)
        tasks += [(frames, work, n, cen, k) for n in uniq]
    with Pool(jobs) as pool:
        for i, _ in enumerate(pool.imap_unordered(_job, tasks, chunksize=2)):
            if i % 50 == 0: print('converted', i, '/', len(tasks), flush=True)

def pack(frames_slots, order, fps, title):
    """frames_slots: list of slot lists (one per drawing); order: 1-based drawing per frame."""
    N, M = len(frames_slots), len(order); S = max(len(fr) for fr in frames_slots)
    x0, x1, y0, y1 = '0', str(W), '0', str(H)
    data, vis = [{"type": "folder", "id": "data", "title": "frame data (keep closed)", "collapsed": True}], []
    for j in range(S):
        R, G, B = [], [], []
        for i, fr in enumerate(frames_slots):
            col, poly = fr[j] if j < len(fr) else (fr[0][0], None)
            R.append(int(col[0])); G.append(int(col[1])); B.append(int(col[2]))
            if poly is None:
                xs, ys = ([x0, x1, x1, x0], [y0, y0, y1, y1]) if j == 0 else (['0/0'], ['0/0'])
            else:
                xs, ys = poly
                if j == 0:  # the largest colour also floods the frame
                    xs = [x0, x1, x1, x0, x0, "0/0"] + xs; ys = [y0, y0, y1, y1, y0, "0/0"] + ys
            data.append({"type": "expression", "id": f"f{i+1}s{j+1}", "folderId": "data", "hidden": True,
                         "latex": rf"a_{{f{i+1}s{j+1}}}=\operatorname{{polygon}}\left(\left[{','.join(xs)}\right],\left[{','.join(ys)}\right]\right)"})
        for nm, L in (("R", R), ("G", G), ("B", B)):
            data.append({"type": "expression", "id": f"{nm}{j+1}", "folderId": "data",
                         "latex": rf"{nm}_{{s{j+1}}}=\left[{','.join(map(str, L))}\right]"})
        vis.append({"type": "expression", "id": f"slot{j+1}",
                    "latex": r"\left[" + ",".join(rf"a_{{f{i+1}s{j+1}}}" for i in range(N)) + r"\right]\left[u\right]",
                    "colorLatex": rf"\operatorname{{rgb}}\left(R_{{s{j+1}}}\left[u\right],G_{{s{j+1}}}\left[u\right],B_{{s{j+1}}}\left[u\right]\right)",
                    "fillOpacity": "1", "lines": False})
    return {"version": 11, "randomSeed": "0",
            "graph": {"viewport": {"xmin": 0, "xmax": W, "ymin": 0, "ymax": H},
                      "showGrid": False, "showXAxis": False, "showYAxis": False},
            "expressions": {"list": [
                {"type": "text", "id": "note", "text": f"{title}: {M} frames ({N} drawings) at {fps:g} fps. Press play on the ticker (or drag k)."},
                {"type": "expression", "id": "k", "latex": "k=1", "slider": {"hardMin": True, "hardMax": True, "min": "1", "max": str(M), "step": "1"}},
                {"type": "expression", "id": "U", "latex": r"U=\left[" + ",".join(map(str, order)) + r"\right]", "hidden": True},
                {"type": "expression", "id": "u", "latex": r"u=U\left[k\right]", "hidden": True},
            ] + vis + data,
                "ticker": {"handlerLatex": rf"k\to\left\{{k={M}:1,k+1\right\}}", "minStepLatex": f"{1000/fps:.3f}", "open": True, "playing": True}}}

def est_bytes(sl):
    return sum(sum(len(x) + 1 for x in p[0]) + sum(len(y) + 1 for y in p[1]) for _, p in sl if p) + 40 * len(sl)

def build_links(work, shots, dup, rng, budget, fps, prefix):
    os.makedirs(os.path.join(work, 'links'), exist_ok=True)
    cache = {}
    def slots(n):
        if n not in cache: cache[n] = pickle.load(open(os.path.join(work, 'slots', n.replace('.png', '.pkl')), 'rb'))
        return cache[n]
    lim = budget * 1e6 * 0.92  # leave room for the colour lists and index list
    def cost(idx):  # bytes of the distinct drawings a run of frames needs
        return sum(est_bytes(slots(d)) for d in {dup[f'r{i:05d}.png'] for i in idx})
    groups, cur = [], []
    for s, e in shots:
        if e < rng[0] or s > rng[1]: continue
        shot = list(range(max(s, rng[0]), min(e, rng[1]) + 1))
        if cur and cost(cur + shot) <= lim:
            cur += shot; continue
        if cur: groups.append(cur); cur = []
        if cost(shot) <= lim:
            cur = shot; continue
        for i in shot:  # one shot bigger than a link: split it frame by frame
            if cur and cost(cur + [i]) > lim: groups.append(cur); cur = []
            cur.append(i)
    if cur: groups.append(cur)
    index = []
    for g, frames_idx in enumerate(groups, 1):
        uniq, order = [], []
        for i in frames_idx:
            d = dup[f'r{i:05d}.png']
            if d not in uniq: uniq.append(d)
            order.append(uniq.index(d) + 1)
        st = pack([slots(d) for d in uniq], order, fps, f'{prefix} part {g}')
        p = os.path.join(work, 'links', f'link{g:03d}.json'); json.dump(st, open(p, 'w'))
        mb = os.path.getsize(p) / 1e6
        index.append({"link": p, "from": frames_idx[0], "to": frames_idx[-1], "drawings": len(uniq), "MB": round(mb, 2)})
        print(g, frames_idx[0], frames_idx[-1], len(uniq), round(mb, 2), flush=True)
    json.dump(index, open(os.path.join(work, 'links.json'), 'w'), indent=1)
    return index

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('work')
    ap.add_argument('--video'); ap.add_argument('--start', type=float, default=0); ap.add_argument('--dur', type=float, default=1e9)
    ap.add_argument('--mask'); ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--from', dest='frm', type=int, default=0); ap.add_argument('--to', type=int, default=10**9)
    ap.add_argument('--budget', type=float, default=2.95); ap.add_argument('--fps', type=float, default=60)
    ap.add_argument('--title', default='Gojo vs Sukuna')
    ap.add_argument('--stage', default='all', choices=['all', 'extract', 'convert', 'links'])
    a = ap.parse_args(); os.makedirs(a.work, exist_ok=True)
    frames = extract(a, a.work)
    shots, dup = analyse(a.work, frames)
    rng = (a.frm, min(a.to, len(dup) - 1))
    if a.stage in ('all', 'convert'): convert(a.work, frames, shots, dup, a.jobs, rng)
    if a.stage in ('all', 'links'): build_links(a.work, shots, dup, rng, a.budget, a.fps, a.title)
