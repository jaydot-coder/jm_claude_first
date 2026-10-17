"""제목(색 구분) + 인스타 릴스 세이프존 음성 자막.
usage: python3 -I make_reel2.py <src.mp4> <font.ttf> <out.mp4> [guide_t guide.png]
자막 목록은 CAPS만 고치면 됨. 세이프존: 위 270 / 아래 420 / 오른쪽 120 / 왼쪽 64 (1080x1920 기준).
"""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, FONT, OUT = sys.argv[1:4]
GUIDE = (float(sys.argv[4]), sys.argv[5]) if len(sys.argv) > 5 else None
W, H, FPS = 1080, 1920, 30
L, R, T, B = 64, W - 120, 270, H - 420  # 세이프존 박스
CX = (L + R) // 2                        # 세이프존 가로 중심 = 512
import numpy as np

def hlg(c):
    """sRGB(8bit) 그래픽 색 -> HLG(BT.2020) 8bit. 원본이 HLG라 글자도 같은 신호 공간에 넣어야 밝기·색이 어긋나지 않음.
    그래픽 흰색을 HLG 신호 0.75(≈203nit, BT.2408 기준)에 맞춤."""
    v = np.array(c[:3], float) / 255
    lin = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
    e = np.clip(m @ lin * 0.203, 0, 1) ** (1 / 1.2)
    a, b = 0.17883277, 0.28466892
    s = np.where(e <= 1 / 12, np.sqrt(3 * e), a * np.log(np.maximum(12 * e - b, 1e-9)) + 0.55991073)
    return tuple(int(round(x * 255)) for x in s) + (c[3],)

# 글자색은 HLG 신호값을 그대로 지정(변환 없음): 흰색=신호 최대, 노랑=쨍한 순노랑. (hlg() 변환은 흰색이 회색, 노랑이 탁하게 나와 쓰지 않음)
YEL, WHT, EDGE = (255, 245, 0, 255), (255, 255, 255, 255), (45, 30, 15, 255)
DUR = 26.2683

# (말 시작, 말 끝, 글자). 글자는 Whisper large-v3 + 한국어 zipformer 두 모델 결과를 맞춰보고
# 사용자가 알려준 "슬퍼요~/화가난당~"으로 교정한 것. 젊어졌다가/늙었다가 4곳은 두 모델 추정(확인 필요)
SEGS = [
    (0.2, 1.0, "화가 난당~"), (1.8, 2.7, "슬퍼요~"), (3.5, 4.5, "화가 난당~"), (5.3, 6.0, "슬퍼요~"),
    (6.7, 8.9, "아~ 슬퍼요~ 아~ 슬퍼요~"), (9.9, 10.5, "화가 난당~"), (11.2, 11.7, "슬퍼요~"),
    (13.0, 13.7, "젊어졌다가~"), (14.8, 15.2, "늙었다가~"), (16.7, 17.4, "젊어졌다가~"), (18.7, 19.1, "늙었다가~"),
    (20.6, 21.6, "히히히~"), (22.8, 23.5, "귀여워요~"),
]
CAPS = [(a - 0.05, max(b + 0.3, a + 0.9), t) for a, b, t in SEGS]  # 읽을 시간 확보: 최소 0.9초 유지
SUB_Y, SUB_SIZE, SUB_MAXW = 1370, 92, R - L  # 자막 중심 y(세이프존 아래쪽), 80px 이상

def render(text, size, color, maxw=None):
    """글자 한 줄을 RGBA로: 진한 외곽선 + 부드러운 그림자. maxw 넘으면 크기를 줄임."""
    while True:
        fo = ImageFont.truetype(FONT, size)
        w = int(fo.getlength(text))
        if maxw is None or w <= maxw or size <= 60:
            break
        size -= 2
    pad = size // 2
    im = Image.new("RGBA", (w + 2 * pad, int(size * 1.4) + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad + size // 16), text, font=fo, fill=(0, 0, 0, 120), stroke_width=size // 10, stroke_fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(size // 14)))
    ImageDraw.Draw(im).text((pad, pad), text, font=fo, fill=color, stroke_width=max(4, size // 14), stroke_fill=EDGE)
    return im

def paste(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, dest=(int(cx - im.width / 2), int(cy - im.height / 2)))

# 제목: "신생아"=노랑, "아빠의 특권"=흰색 (세이프존 위쪽에서 시작)
BASE = Image.new("RGBA", (W, H), (0, 0, 0, 0))
t1, t2 = render("신생아", 190, YEL), render("아빠의 특권", 136, WHT, maxw=R - L)
# 눈(약 y=680) 위쪽에 머물도록 두 줄을 붙여 세이프존 맨 위에 배치
paste(BASE, t1, CX, T + 107)
paste(BASE, t2, CX, T + 107 + 165)
CAP_IMGS = [render(t, SUB_SIZE, WHT, SUB_MAXW) for _, _, t in CAPS]

def overlay(sec):
    cv = BASE.copy()
    for (a, b, _), im in zip(CAPS, CAP_IMGS):
        if a <= sec <= b:
            u = sec - a
            sc = 0.6 + 0.4 * min(1, u / 0.15) if u < 0.15 else 1.0
            al = min(1.0, (b - sec) / 0.15)
            paste(cv, im.copy(), CX, SUB_Y, sc, al)
    return cv

if GUIDE:  # 세이프존 확인용: 프레임 + 박스 표시
    ov = overlay(GUIDE[0])
    d = ImageDraw.Draw(ov)
    d.rectangle([L, T, R, B], outline=(255, 0, 80, 255), width=4)
    ov.save(GUIDE[1])
    sys.exit()

n = int(DUR * FPS)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
       # 원본(10bit HLG, BT.2020) 그대로 유지: 비트심도·색 태그를 건드리지 않고 글자 레이어만 같은 색공간(bt2020)으로 합성
       "-filter_complex", f"[0:v]fps={FPS},scale={W}:{H}:flags=lanczos+accurate_rnd,format=yuv420p10le[v];"
                          f"[1:v]format=rgba,scale=out_color_matrix=bt2020:out_range=tv,format=yuva420p10le[ov];[v][ov]overlay=format=yuv420p10[o]",
       "-map", "[o]", "-map", "0:a", "-c:a", "copy",  # 소리도 원본 그대로
       "-c:v", "libx265", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
       "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-color_range", "tv",
       "-x265-params", "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:log-level=error",
       "-movflags", "+faststart", "-frames:v", str(n), OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for k in range(n):
    p.stdin.write(overlay(k / FPS).tobytes())
p.stdin.close()
assert p.wait() == 0, "ffmpeg failed"
