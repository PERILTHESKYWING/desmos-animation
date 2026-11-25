"""Generate the technique test scenes (run: python3 gen.py, then render each with scripts/render.js)."""
import json
def S(name, exprs, seconds=1, fps=30, size=(960,540), bounds=None, camera=None):
    s={"size":list(size),"bounds":bounds or {"left":-16,"right":16,"bottom":-9,"top":9},
       "expressions":[{"id":"T","latex":"T=0"}]+exprs,"clock":{"var":"T","fps":fps,"seconds":seconds}}
    if camera: s["camera"]=camera
    json.dump(s,open(name+'.json','w'),indent=1)
BG=lambda c:{"latex":r"\left|x\right|>0","color":c,"fillOpacity":"1","lines":False}
E_=lambda e,**k:dict(latex=e,**k)

# T2: energy orbs + glow (Hollow Purple style): stacked translucent discs, glow strokes, merge with easing
ease=r"E\left(x\right)=\left\{0<x<1:3x^{2}-2x^{3},x\le0:0,1\right\}"
S("t2_glow",[BG("#05010f"),
  E_(ease),
  E_(r"m=E\left(\frac{T-0.2}{0.6}\right)"),
  E_(r"A=\left(-7\left(1-m\right),0.6\sin\left(9T\right)\left(1-m\right)\right)"),
  E_(r"B=\left(7\left(1-m\right),-0.6\sin\left(9T\right)\left(1-m\right)\right)"),
  E_(r"r=\left[0.05,0.1...1\right]"),
  # glow halos: 20 discs each, opacity small, radius growing -> soft falloff
  E_(r"\operatorname{polygon}\left(A+\left(1+3r\left[k\right]\right)\left(\cos\left(\frac{\pi}{24}\cdot\left[0...47\right]\right),\sin\left(\frac{\pi}{24}\cdot\left[0...47\right]\right)\right)\right)\operatorname{for}k=\left[1...20\right]",color="#ff2d3c",fillOpacity="0.06",lines=False),
  E_(r"\operatorname{polygon}\left(B+\left(1+3r\left[k\right]\right)\left(\cos\left(\frac{\pi}{24}\cdot\left[0...47\right]\right),\sin\left(\frac{\pi}{24}\cdot\left[0...47\right]\right)\right)\right)\operatorname{for}k=\left[1...20\right]",color="#2d7bff",fillOpacity="0.06",lines=False),
  # cores
  E_(r"\left(x-A.x\right)^{2}+\left(y-A.y\right)^{2}<1",color="#ffd0d4",fillOpacity="1",lines=False),
  E_(r"\left(x-B.x\right)^{2}+\left(y-B.y\right)^{2}<1",color="#cfe0ff",fillOpacity="1",lines=False),
  # purple bloom when merged
  E_(r"\operatorname{polygon}\left(\left(0.3+8mr\left[k\right]\right)\left(\cos\left(\frac{\pi}{24}\cdot\left[0...47\right]\right),\sin\left(\frac{\pi}{24}\cdot\left[0...47\right]\right)\right)\right)\operatorname{for}k=\left[1...20\right]",color="#b14dff",fillOpacity="0.05m",lines=False),
  # glow strokes: one ring, many widths, low opacity
  E_(r"\left(1.5m+0\cdot\left[1...10\right]\right)\left(\cos t,\sin t\right)",color="#e7c6ff",lineWidth=r"6\cdot\left[1...10\right]",lineOpacity="0.08",parametricDomain={"min":"0","max":"2\\pi"}),
  # crackling arcs between orbs (random, re-seeded per frame)
  E_(r"\left(A.x+\left(B.x-A.x\right)t,\ A.y+\left(B.y-A.y\right)t+0.8\left(1-m\right)\sin\left(\pi t\right)\left(\operatorname{random}\left(4,\operatorname{floor}\left(30T\right)\right)-0.5\right)\sin\left(20t+40T+\left[1...4\right]\right)\right)",color="#ffffff",lineWidth="2",lineOpacity="0.6",parametricDomain={"min":"0","max":"1"}),
],seconds=1)

# T3: shape morph (tweening two equal-length point lists) = in-betweening between key poses
S("t3_morph",[BG("#101018"),E_(ease),
  E_(r"N=\left[0...119\right]"),
  E_(r"P_{1}=\left(5\cos\left(\frac{2\pi N}{120}\right),5\sin\left(\frac{2\pi N}{120}\right)\right)"),
  E_(r"P_{2}=\left(2.5+3.5\left\{\operatorname{mod}\left(N,24\right)<12:1,-0.4\right\}\right)\cdot\left(\cos\left(\frac{2\pi N}{120}\right),\sin\left(\frac{2\pi N}{120}\right)\right)"),
  E_(r"u=E\left(T\right)"),
  E_(r"\operatorname{polygon}\left(\left(1-u\right)P_{1}+uP_{2}\right)",color="#ffb000",fillOpacity="1",lines=False),
  E_(r"\operatorname{polygon}\left(\left(1-u\right)P_{1}+uP_{2}\right)",color="#000000",fillOpacity="0",lineWidth="4"),
],seconds=1,fps=10)

# T4: particle scaling: N points with per-point size and colour
for n in (2000,9000):
    S(f"t4_particles_{n}",[BG("#000000"),
      E_(rf"R=\operatorname{{random}}\left({n},1\right)"),
      E_(rf"Q=\operatorname{{random}}\left({n},2\right)"),
      E_(r"\left(16\left(2R-1\right)\left(0.3+T\right),9\left(2Q-1\right)\left(0.3+T\right)\right)",colorLatex=r"\operatorname{hsv}\left(260+60R,0.6,1\right)",pointSize=r"1+4Q",pointOpacity="0.7"),
    ],seconds=0.2,fps=10)

# T5: anime impact frame: speed lines + camera shake + white flash + zoom
S("t5_impact",[BG("#0a0a12"),E_(ease),
  E_(r"a=2\pi\operatorname{random}\left(90,\operatorname{floor}\left(15T\right)\right)"),
  E_(r"w=0.02+0.06\operatorname{random}\left(90,\operatorname{floor}\left(15T\right)+7\right)"),
  E_(r"r_{0}=3+2\operatorname{random}\left(90,5\right)"),
  E_(r"\operatorname{polygon}\left(r_{0}\left[j\right]\left(\cos\left(a\left[j\right]\right),\sin\left(a\left[j\right]\right)\right),40\left(\cos\left(a\left[j\right]-w\left[j\right]\right),\sin\left(a\left[j\right]-w\left[j\right]\right)\right),40\left(\cos\left(a\left[j\right]+w\left[j\right]\right),\sin\left(a\left[j\right]+w\left[j\right]\right)\right)\right)\operatorname{for}j=\left[1...90\right]",color="#ffffff",fillOpacity="0.85",lines=False),
  E_(r"\left|x\right|>0",color="#ffffff",fillOpacity=r"e^{-60\left(T-0.15\right)^{2}}",lines=False),
],seconds=1,camera="(()=>{const s=0.6*Math.exp(-6*T);const z=1-0.15*Math.min(1,T*3);return {left:-16*z+s*Math.sin(53*T),right:16*z+s*Math.sin(53*T),bottom:-9*z+s*Math.cos(47*T),top:9*z+s*Math.cos(47*T)}})()")
print("ok")
