# Gojo vs Sukuna: first 3 seconds (180 frames at 60 fps)

Reference: the AMV ending scene, frames 1-180 extracted at 960x540.

## Shots
| frames | shot | method used | rendered PSNR |
|---|---|---|---|
| 1-6 | Gojo/Sukuna art still | trace, k=64 + 240-col grid underlay | 26.3 dB |
| 7 | white flash | flat fill | 50.7 dB |
| 8-46 | eye-diamond on purple texture | trace + underlay | 30-33 dB |
| 47-82 | streak / white bloom | grid (smooth gradients) | 33-51 dB |
| 83-139 | glow over purple mountains | grid | 45-55 dB |
| 140-171 | black, then JJK logo | flat / trace | 28-138 dB |
| 172 | white flash | flat | 55 dB |
| 173-180 | dark blue water | grid | 44-50 dB |

Average over all 180 frames: **40.6 dB**. Each frame is 0.25-3.4 MB of Desmos state
(100k-270k polygon vertices on textured frames).

## Pipeline
```
python3 scripts/video2desmos.py frames/ scenes/            # per-frame scenes + report.json
node scripts/render_seq.js scenes/ out/ --from 1 --to 180  # render in desmos.com
python3 scripts/video_link.py frames/ link.json --step 3 --k 10 --simplify 1.4 --fps 20
node scripts/share.js link.json --state                    # one playable desmos.com link
node scripts/share.js scenes/f0030.json                    # full-quality snapshot of one frame
```

## Limits learned
- desmos.com's snapshot save accepts about 3 MB of state; 6 MB and 20 MB failed. So the
  single playable link is a lighter cut (60 frames, 10 colours, half resolution).
- Textured frames (art still, purple texture) lose the most: 10-colour posterization at
  half resolution scores 16-24 dB, versus 26-33 dB at full quality.
- The grid underlay puts a grey halo around thin lines (logo frames, 28 dB). Next step:
  drop the underlay when one flat colour covers most of the frame (predicted 41 dB).
- Desmos resizes the viewport to keep a square aspect ratio, so capture with explicit
  `mathBounds`, never the graph's current viewport.
