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

## Style change (XIAO, 2026-11-26)
The detailed scene-1 version looked too machine-made. From scene 2 on, the style is
`video_link.py --cel 8` (scripts/cel.py): one palette per shot (8 tones plus up to 2
vivid accents such as eye glow), mean-shift flattening, soft majority vote on the label
map, potrace with smooth curves (alphamax 1.0), and ink lines from an adaptive
threshold drawn on top. That keeps each shot under the 3 MB link limit, and the mp4 is
rendered from the link itself (`render_link.js`), so the link and the video match.

## Scenes delivered
| # | time | content | full-quality PSNR (non-black frames) | links |
|---|---|---|---|---|
| 1 | 0:00-0:04 (frames 0-259) | spoiler card, blue flame, red flame, clash, title strobe | 32.4 dB | play https://www.desmos.com/calculator/d46rrgwgp9, still https://www.desmos.com/calculator/qtuxudc33f |
| 2 | 0:04-0:10 (frames 260-632) | morgue, Gojo close-up, group shot (cel style) | n/a | A https://www.desmos.com/calculator/fk7bbfavlq, B https://www.desmos.com/calculator/2p56jfb0pg, C https://www.desmos.com/calculator/q9kdyg2ifu |

## Final pass (2026-11-26)
Review of every shot found: blank credits card (inpainting smeared the text; frames 8220+ now use raw frames, the watermark is absent there, and dark frames get a light-ink layer), a black disc in dark hair (near-black tones merged, letterbox bars treated as frame edge), thick ink blobs (ink drops anything that survives a 7x7 opening). All 42 links regenerated; list in research/amv-links.md. amv_assemble.py joins renders into the 1080p60 master. Its "render faults" (< 24 dB) are anti-aliasing on fine ink at 1080p, checked visually: renders match previews.
