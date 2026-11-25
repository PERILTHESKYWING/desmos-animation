#!/usr/bin/env python3
"""Fetch a saved Desmos graph's state and print a structural summary.

    python3 scripts/fetch.py <hash-or-url> [--out state.json] [--full]

No API key or browser needed: desmos.com returns the full graph (state
included) as JSON when asked with `Accept: application/json`.
The summary lists folders, sliders, the ticker, notes and a technique
fingerprint, which is what you read first when dissecting a graph.
"""
import json, re, sys, urllib.request, collections

TECHNIQUES = {  # name: (regex on latex/settings, what it means)
    "list-broadcast glow": (r"lineWidth=.*\[|\\cdot\\left\[1,\.\.\.", "one curve drawn N times with a list of widths at low opacity"),
    "stacked fills (gradient)": (r"fillOpacity=(0\.0\d|\\frac\{[^}]*\}\{\\left\[)", "many low-opacity fills stacked into a gradient or blur"),
    "polygon()": (r"\\operatorname\{polygon\}", "filled shapes from point lists (faster than parametrics)"),
    "0/0 breaks": (r"0/0|\\frac\{0\}\{0\}", "NaN separators: many disjoint shapes in one expression"),
    "list comprehension": (r"\\operatorname\{for\}", "`[... for n=[1...N]]` makes many objects in one line"),
    "with": (r"\\operatorname\{with\}", "local substitution, reuse a function with other params"),
    "random()": (r"\\operatorname\{random\}", "seeded scatter: stars, rain, jitter"),
    "hsv/okhsv colours": (r"\\operatorname\{(ok)?hsv\}", "colours as variables, animatable via colorLatex"),
    "colorLatex": (r"colorLatex=", "colour driven by an expression"),
    "3D projection": (r"\\frac\{[^}]*\}\{[^}]*\.z\}|\{z>0\}|p\.z>0", "perspective divide x/z, y/z"),
    "bezier": (r"\(1-t\)\^\{?3|\\left\(1-t\\right\)\^\{3\}", "cubic Bezier helper"),
    "tanh/logistic easing": (r"\\tanh|1\+e\^\{-", "smooth steps for transitions"),
    "median clamp": (r"\\operatorname\{median\}\\left\(0,1", "median(0,1,x) clamps a progress value"),
    "actions (->)": (r"\\to", "ticker/action state updates"),
    "pixel-relative width": (r"\\operatorname\{width\}", "l=width/k keeps line widths device independent"),
    "images": (r"^IMAGE", "embedded raster images"),
}

def fetch(h):
    h = re.sub(r".*/calculator/", "", h).split("?")[0].strip("/")
    req = urllib.request.Request("https://www.desmos.com/calculator/" + h,
                                 headers={"Accept": "application/json", "User-Agent": "desmos-dissect"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def flat(e):
    keys = ("colorLatex", "fillOpacity", "lineOpacity", "lineWidth")
    if e["type"] == "image":
        return "IMAGE"
    return e.get("latex", "") + " " + " ".join(f"{k}={e[k]}" for k in keys if k in e)

def summary(d, full=False):
    s = d["state"]; L = s["expressions"]["list"]
    print(f"# {d.get('title')}  ({d['hash']})  version {s.get('version')}")
    print("graph:", json.dumps(s.get("graph")))
    print("ticker:", json.dumps(s["expressions"].get("ticker")))
    types = collections.Counter(e["type"] for e in L)
    print("items:", len(L), dict(types), "latex chars:", sum(len(e.get("latex", "")) for e in L))
    folders = {e["id"]: e.get("title") for e in L if e["type"] == "folder"}
    cnt = collections.Counter(e.get("folderId") for e in L)
    print("\n## folders"); [print(f"  {t!r} ({cnt[i]})") for i, t in folders.items()]
    print("\n## sliders")
    for e in L:
        if e.get("slider") and ("animationPeriod" in e["slider"] or not e.get("folderId")):
            sl = e["slider"]
            print(f"  {e['latex'][:60]}  [{sl.get('min')}, {sl.get('max')}] period={sl.get('animationPeriod')} loop={sl.get('loopMode')}")
    print("\n## technique fingerprint")
    blob = [flat(e) for e in L]
    for name, (rx, why) in TECHNIQUES.items():
        n = sum(1 for b in blob if re.search(rx, b))
        if n: print(f"  {name:26s} x{n:<5d} {why}")
    notes = [e["text"] for e in L if e["type"] == "text" and e.get("text")]
    print(f"\n## author notes ({len(notes)})")
    for t in notes if full else notes[:12]:
        print("  -", t.replace("\n", " ")[: None if full else 240])

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    d = fetch(a[0])
    if "--out" in a:
        json.dump(d["state"], open(a[a.index("--out") + 1], "w"))
    summary(d, "--full" in a)
