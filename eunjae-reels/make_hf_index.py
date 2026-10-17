"""make_reel.py의 자막 목록(EV)과 소리 세기(env)로 하이퍼프레임 index.html 생성.
usage: python3 -I make_hf_index.py <make_reel.py> <audio.wav> <proj_dir>
"""
import ast, math, re, sys, wave
import numpy as np
from scipy import signal

REEL, WAV, PROJ = sys.argv[1:4]
DUR = 44.2667

EV = ast.literal_eval(re.search(r"^EV = (\[.*?^\])", open(REEL, encoding="utf-8").read(), re.S | re.M).group(1))

# ---- 소리 세기 env (make_reel.py와 동일 계산) ----
w = wave.open(WAV)
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
f, t, S = signal.stft(x, sr, nperseg=1024, noverlap=768)
P = np.abs(S) ** 2
nf = np.percentile(P, 30, axis=1, keepdims=True)
band = (f >= 80) & (f <= 3000)
snr = 10 * np.log10((P[band].sum(0) + 1e-20) / (nf[band].sum() + 1e-20))
snr = np.convolve(snr, np.ones(5) / 5, "same")
envv = np.clip((snr - 6) / (np.percentile(snr, 99.5) - 6), 0, 1)
env = lambda s: float(np.interp(s, t, envv))

r = lambda v: round(v, 3)
html, js = [], []

def block(idx, text, size, cx, cy, start, life, cls="cap"):
    chars = "".join(f'<span class="ch c{idx}" id="c{idx}_{i}">{c if c != " " else "&nbsp;"}</span>' for i, c in enumerate(text))
    html.append(
        f'<div class="clip {cls}" id="o{idx}" data-start="{r(start)}" data-duration="{r(life)}" data-track-index="{1 + idx % 6}" '
        f'style="left:{cx - 540}px;top:{cy - size * 0.7:.0f}px;height:{size * 1.4:.0f}px;font-size:{size}px">'
        f'<div class="in" id="i{idx}">{chars}</div></div>')

# 훅 타이틀(영상 내내 고정)
for n, (txt, sz, cy) in enumerate([("새벽에 같이 깨어본 부모라면 공감", 56, 290), ("신생아의", 205, 455), ("새벽소리", 205, 665)]):
    block(100 + n, txt, sz, 540, cy, 0, DUR, "title")

for k, (a, b, text, sz, (cx, cy), kind, drift, rot0) in enumerate(EV):
    s0 = a - 0.03
    end = max(b + 0.35, s0 + 0.9)
    fade = 0.25
    if kind == "wave":
        end, fade = b, 0.6  # 그르릉은 서서히 잦아듦
    life = end - s0
    block(k, text, sz, cx, cy, max(0, s0), life)
    o, i = f"#o{k}", f"#i{k}"
    s0 = max(0, s0)
    # 톡 튀어나옴
    js.append(f'tl.fromTo("{o}",{{scale:0.3,opacity:0,rotation:{rot0 - 8}}},{{scale:1,opacity:1,rotation:{rot0},duration:0.22,ease:"back.out(2.2)"}},{r(s0)});')
    # 소리 세기만큼 커졌다 작아짐 + 떨림
    if kind in ("shake", "wave"):
        amp_s = 0.14 if kind == "shake" else 0.08
        tt = s0 + 0.22
        while tt < end - fade - 0.1:
            e = env(tt)
            js.append(f'tl.to("{o}",{{scale:{r(1 + amp_s * e)},duration:0.1,ease:"none"}},{r(tt)});')
            if kind == "shake":
                amp = 14 * e
                jx, jy = amp * math.sin(tt * 2 * math.pi * 13), amp * math.sin(tt * 2 * math.pi * 10 + 1)
                js.append(f'tl.to("{i}",{{x:{r(jx)},y:{r(jy)},duration:0.1,ease:"none"}},{r(tt)});')
            tt += 0.1
    # 살랑 기울기
    tt, sgn = s0 + 0.22, 1
    while tt < end - fade - 0.25:
        js.append(f'tl.to("{o}",{{rotation:{rot0 + 4 * sgn},duration:0.25,ease:"sine.inOut"}},{r(tt)});')
        tt, sgn = tt + 0.25, -sgn
    # 소리 높낮이처럼 떠오르거나 가라앉음
    if drift:
        js.append(f'tl.to("{o}",{{y:{drift},duration:{r(life)},ease:"power1.out"}},{r(s0)});')
    # 글자별 물결
    if kind == "wave" or life > 1.0:
        for ci in range(len(text)):
            tt = s0 + 0.22
            while tt < end - fade - 0.1:
                amp = 24 * (0.4 + env(tt)) if kind == "wave" else 7
                y = amp * math.sin(tt * 2 * math.pi * 1.5 - ci * 0.9)
                js.append(f'tl.to("#c{k}_{ci}",{{y:{r(y)},duration:0.1,ease:"none"}},{r(tt)});')
                tt += 0.1
    js.append(f'tl.to("{o}",{{opacity:0,scale:0.9,duration:{fade},ease:"power1.in"}},{r(end - fade)});')

page = f"""<!doctype html>
<html lang="ko" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="gsap.min.js"></script>
<style>
@font-face {{ font-family: "Jua"; src: url("Jua-Regular.ttf"); font-display: block; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; font-family: "Jua", sans-serif; color: #fff; }}
#base {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }}
.cap, .title {{ position: absolute; width: 1080px; display: flex; justify-content: center; align-items: center; }}
.in {{ display: flex; white-space: pre; line-height: 1.4; text-shadow: 0 6px 14px rgba(0,0,0,.55); }}
.ch {{ display: inline-block; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
<video id="base" class="clip" src="base.mp4" data-start="0" data-duration="{DUR}" data-track-index="0" data-has-audio="true" playsinline></video>
{chr(10).join(html)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""
open(f"{PROJ}/index.html", "w", encoding="utf-8").write(page)
print("events", len(EV), "tweens", len(js), "bytes", len(page))
