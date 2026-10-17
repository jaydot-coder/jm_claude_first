"""은재왔지 새벽소리 릴스: 훅 타이틀 + 소리 따라 움직이는 의성어 자막.
usage: python3 -I make_reel.py <src.mp4> <work_dir> <out.mp4> [still_t out.png]
"""
import math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal

SRC, WORK, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
STILL = (float(sys.argv[4]), sys.argv[5]) if len(sys.argv) > 5 else None
W, H, FPS = 1080, 1920, 30
FONT = f"{WORK}/Jua-Regular.ttf"
DUR = 44.2667

# ---- 소리 세기(env): 노이즈 바닥 대비 SNR을 0~1로 ----
w = wave.open(f"{WORK}/audio.wav")
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
f, t, S = signal.stft(x, sr, nperseg=1024, noverlap=768)
P = np.abs(S) ** 2
nf = np.percentile(P, 30, axis=1, keepdims=True)
band = (f >= 80) & (f <= 3000)
snr = 10 * np.log10((P[band].sum(0) + 1e-20) / (nf[band].sum() + 1e-20))
snr = np.convolve(snr, np.ones(5) / 5, "same")
envv = np.clip((snr - 6) / (np.percentile(snr, 99.5) - 6), 0, 1)
def env(sec):
    return float(np.interp(sec, t, envv))

# ---- 자막: (시작, 끝, 글자, 크기, (cx,cy), 종류, 드리프트dy, 기울기) ----
# 종류: pop=톡 튀고 사라짐 / shake=소리 세기만큼 떨림 / wave=글자가 물결
EV = [
    (0.00, 0.55, "으음", 110, (720, 930), "pop", 0, -4),
    (0.65, 10.0, "그르르릉~", 135, (540, 1390), "wave", 0, 0),
    (2.80, 2.95, "쩝", 110, (330, 880), "pop", -20, 5),
    (4.25, 4.40, "킁", 110, (770, 1010), "pop", -20, -6),
    (6.50, 6.80, "으응~", 140, (350, 1110), "pop", 40, -4),
    (13.82, 14.30, "으읏", 120, (330, 900), "pop", -10, 4),
    (14.40, 15.60, "으으응~", 190, (560, 1060), "shake", 60, -3),
    (18.40, 18.82, "응?", 120, (730, 900), "pop", -25, 6),
    (20.90, 21.07, "끅", 110, (330, 1010), "pop", -15, -5),
    (21.62, 21.74, "푸", 100, (770, 1160), "pop", -15, 5),
    (24.67, 25.39, "으음~", 170, (390, 910), "shake", 50, -4),
    (26.03, 26.61, "으앙?", 170, (720, 1060), "shake", -40, 5),
    (27.68, 28.27, "으응~", 170, (400, 1240), "shake", 40, -4),
    (30.54, 30.88, "후우~", 120, (680, 960), "pop", -20, 3),
    (31.87, 32.70, "으애앵!!", 230, (540, 1060), "shake", 0, -3),
    (33.31, 33.42, "끙", 110, (330, 960), "pop", 0, -5),
    (36.48, 36.66, "끙~", 120, (720, 1160), "pop", 50, 4),
    (38.94, 39.09, "킁", 110, (400, 910), "pop", -20, 6),
    (40.14, 40.62, "으엥!", 190, (580, 1030), "shake", 0, 4),
]

# ---- 글자 이미지(흰색 + 아주 옅은 그림자) 캐시 ----
_fc, _gc = {}, {}
def font(sz):
    if sz not in _fc:
        _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

def glyph(ch, sz):
    if (ch, sz) in _gc:
        return _gc[(ch, sz)]
    fo = font(sz)
    pad = sz // 3
    adv = int(fo.getlength(ch)) or sz // 3
    im = Image.new("RGBA", (adv + 2 * pad, int(sz * 1.3) + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad + sz // 20), ch, font=fo, fill=(0, 0, 0, 130))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(sz // 25)))
    ImageDraw.Draw(im).text((pad, pad), ch, font=fo, fill=(255, 255, 255, 255))
    _gc[(ch, sz)] = (im, adv, pad)
    return _gc[(ch, sz)]

def put(canvas, text, sz, cx, cy, scale=1.0, rot=0.0, alpha=1.0, wave_amp=0.0, wave_t=0.0):
    gl = [glyph(c, sz) for c in text]
    total = sum(g[1] for g in gl)
    px = -total / 2
    th = math.radians(rot)
    for i, (im, adv, pad) in enumerate(gl):
        lx = (px + adv / 2) * scale
        ly = wave_amp * math.sin(wave_t * 2 * math.pi * 1.5 - i * 0.9)
        px += adv
        gx = cx + lx * math.cos(th) - ly * math.sin(th)
        gy = cy + lx * math.sin(th) + ly * math.cos(th)
        g = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
        if rot:
            g = g.rotate(-rot, resample=Image.BICUBIC, expand=True)
        if alpha < 1:
            g.putalpha(g.getchannel("A").point(lambda v: int(v * alpha)))
        dx, dy = int(gx - g.width / 2), int(gy - g.height / 2)
        if dx < 0 or dy < 0 or dx + g.width > W or dy + g.height > H:
            continue
        canvas.alpha_composite(g, dest=(dx, dy))

def ease_back(u):  # 0->1, 살짝 넘쳤다 돌아옴
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2

# ---- 훅 타이틀(고정): 작은 줄 = 타깃, 큰 줄 = 약속 ----
BASE = Image.new("RGBA", (W, H), (0, 0, 0, 0))
put(BASE, "새벽에 같이 깨어본 부모라면 공감", 56, 540, 290)
put(BASE, "신생아의", 205, 540, 455)
put(BASE, "새벽소리", 205, 540, 665)

def frame_overlay(sec):
    cv = BASE.copy()
    for (a, b, text, sz, (cx, cy), kind, drift, rot0) in EV:
        start = a - 0.03
        end = max(b + 0.35, start + 0.9)
        if not (start <= sec <= end):
            continue
        u, life = sec - start, end - start
        sc = 0.3 + 0.7 * ease_back(min(1, u / 0.18))
        e = env(sec)
        sc *= 1 + (0.14 if kind == "shake" else 0.08) * e
        alpha = 1.0
        if end - sec < 0.25:
            k = (end - sec) / 0.25
            alpha, sc = k, sc * (0.9 + 0.1 * k)
        jx = jy = 0.0
        if kind == "shake":
            amp = 14 * e
            jx, jy = amp * math.sin(sec * 2 * math.pi * 13), amp * math.sin(sec * 2 * math.pi * 10 + 1)
        elif kind == "wave":
            amp_env = e
        rot = rot0 + 4 * math.sin(sec * 2 * math.pi * 2)
        wamp = (24 * (0.4 + e) if kind == "wave" else 7)
        if kind == "wave" and sec > 9.4:  # 그르릉이 잦아드는 구간
            alpha *= max(0.0, (10.0 - sec) / 0.6) if sec < 10.0 else 0.0
        put(cv, text, sz, cx + jx, cy + jy + drift * (u / life), sc, rot, alpha, wamp, sec)
    return cv

def main():
    if STILL:
        frame_overlay(STILL[0]).save(STILL[1])
        return
    n = int(DUR * FPS)
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", SRC,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
        "-filter_complex",
        f"[0:v]fps={FPS},scale={W}:{H}:flags=lanczos,format=yuv420p[v];[v][1:v]overlay=format=auto,format=yuv420p[o]",
        "-map", "[o]", "-map", "0:a",
        # 원본 소리가 -57LUFS로 아주 작아 +28dB, 피크는 리미터로 보호
        "-af", "volume=28dB,alimiter=limit=0.89",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-frames:v", str(n), OUT,
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(frame_overlay(k / FPS).tobytes())
    p.stdin.close()
    assert p.wait() == 0, "ffmpeg failed"

main()
