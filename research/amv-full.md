# Full AMV recreation (NinjaristicNinja "Gojo vs Sukuna" edit, credit to the editor)

Source: 1080p60, 145.4 s. Used: 2.0 s to 142.4 s (8,423 frames); intro and credits cut.
About 3,100 unique drawings: held frames are detected (mean abs diff < 0.6 at 240x135)
and converted/rendered once.

Per scene:
1. `ffmpeg -ss <start> -frames:v N` → raw PNGs
2. `scripts/dewatermark.py assets/ninjaristic_watermark_mask_1080p.png raw clean`
3. dedupe → dupmap.json; convert unique frames with `video2desmos.py` (4 parallel)
4. `render_seq.js` (resumes and relaunches the browser when a heavy frame crashes it)
5. playable link: `video_link.py clean link.json --dupmap dupmap.json --pix --width 960 --step 1 --fps 60`,
   tuned (k, --simplify) until the state is about 3 MB, then `share.js --state`
6. full-quality still: `share.js scenes/fNNNN.json`

## Scenes delivered
| # | time | content | full-quality PSNR (non-black frames) | links |
|---|---|---|---|---|
| 1 | 0:00-0:04 (frames 0-259) | spoiler card, blue flame, red flame, clash, title strobe | 32.4 dB | play https://www.desmos.com/calculator/d46rrgwgp9, still https://www.desmos.com/calculator/qtuxudc33f |
