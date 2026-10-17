# creates overlay.mov of cumsum kills for both sides
# includes recent kills

import csv
import subprocess
from bisect import bisect_right
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---- settings ----
SRC = Path("/home/killfeed/feed_adjusted.csv") # replace with your path
DST = SRC.with_name("overlay.mov")
FPS = 10
TAIL = 10                 # seconds to keep showing the last row
OFFSET = 0                # shift if CSV 00:00:00 isn't the video start
FONT = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
#FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 48
GAP = 6                   # spaces between blue and red
PAD = 6                   # padded width of each number
BG = (0, 0, 0, 155)       # semi-transparent box behind text, None to disable
HOLD = 5   # seconds a recent value stays visible unless replaced
BLUE_DARK, BLUE_BRIGHT = (40, 90, 210), (110, 180, 255)
RED_DARK, RED_BRIGHT = (190, 35, 35), (255, 100, 100)
# ------------------

def to_sec(ts):
    h, m, s = map(int, ts.split(":"))
    return h * 3600 + m * 60 + s

with open(SRC, newline="") as f:
    rows = list(csv.DictReader(f, delimiter=";"))
times = [to_sec(r["ts"]) + OFFSET for r in rows]

font = ImageFont.truetype(FONT, FONT_SIZE)
cw = font.getlength("0")
margin = 14
W = int(cw * (PAD * 2 + GAP) + margin * 2)
line_h = int(FONT_SIZE * 1.25)
H = line_h * 2 + margin * 2
red_x = margin + cw * (PAD + GAP)

def recent_text(v):
    return f"+{v}".rjust(PAD) if v else " " * PAD

def events(col):
    """(times, values) of rows where this side's recent value is non-zero."""
    ev_t, ev_v = [], []
    for t, r in zip(times, rows):
        if str(r[col]) not in ("", "0"):
            ev_t.append(t)
            ev_v.append(r[col])
    return ev_t, ev_v

blue_ev = events("bluerecent")
red_ev = events("redrecent")

def active(ev, t):
    """Latest event value if it is still within HOLD seconds, else empty."""
    ev_t, ev_v = ev
    k = bisect_right(ev_t, t) - 1
    if k >= 0 and t - ev_t[k] < HOLD:
        return ev_v[k]
    return ""

cache = {}
def render(i, b, r_):
    key = (i, b, r_)
    if key in cache:
        return cache[key]
    r = rows[i]
    img = Image.new("RGBA", (W, H), BG or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((margin, margin), str(r["blue"]).rjust(PAD), font=font, fill=BLUE_DARK)
    d.text((red_x, margin), str(r["red"]).rjust(PAD), font=font, fill=RED_DARK)
    d.text((margin, margin + line_h), recent_text(b), font=font, fill=BLUE_BRIGHT)
    d.text((red_x, margin + line_h), recent_text(r_), font=font, fill=RED_BRIGHT)
    cache[key] = img.tobytes()
    return cache[key]

blank = Image.new("RGBA", (W, H), (0, 0, 0, 0)).tobytes()
total_frames = int((times[-1] + TAIL) * FPS)

ff = subprocess.Popen([
    "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", str(DST)
], stdin=subprocess.PIPE)

for n in range(total_frames):
    t = n / FPS
    i = bisect_right(times, t) - 1
    if i < 0:
        ff.stdin.write(blank)
    else:
        ff.stdin.write(render(i, active(blue_ev, t), active(red_ev, t)))
ff.stdin.close()
ff.wait()
print(f"Wrote {DST} ({W}x{H})")
