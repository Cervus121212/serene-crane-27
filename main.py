#!/usr/bin/env python3
"""VELMARA — Where the Water Climbs to the Sky.

A travel poster for a place that does not exist: a giant waterfall that
flows UP from the sea into the sky at golden hour.

Python 3.13, standard library only (os/struct/zlib/math). No PIL, no
network. Draws the whole 1024x1024 poster procedurally and writes
entry.png to $MAKEFUN_OUTPUT_DIR (falling back to this file's directory).
"""
import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024
INSET = 14            # thin cream frame at the edges
HORIZON = 660         # sea line

# ---------------------------------------------------------------- palette
CREAM = (255, 244, 214)
INK = (28, 20, 48)            # dark outline / cliffs
SKY_TOP = (38, 32, 86)        # indigo
SKY_MID = (94, 60, 140)       # violet
SKY_LOW = (244, 164, 96)      # amber at the horizon
SUN_HALO = (255, 170, 80)
SUN_OUT = (255, 222, 130)
SUN_IN = (255, 238, 175)
CLOUD = (255, 250, 240)
CLOUD_PEACH = (255, 205, 165)
FALL_TOP = (226, 238, 248)
FALL_MID = (196, 222, 240)
FALL_SHADE = (150, 190, 220)
FOAM = (255, 255, 255)
SEA_TOP = (64, 160, 165)
SEA_BOT = (16, 90, 110)
CLIFF = (32, 26, 54)
PINE = (22, 44, 50)
SAIL_WHITE = (255, 252, 244)
SAIL_AMBER = (255, 190, 110)
HULL = (30, 22, 46)
REFL = (255, 190, 110)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def blend(base, over, alpha):
    """Alpha-blend `over` onto `base` (alpha 0..1)."""
    return tuple(int(round(base[i] * (1.0 - alpha) + over[i] * alpha))
                 for i in range(3))


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def _rowbase(self, y):
        return y * self.w * 3

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x0 >= x1 or y0 >= y1:
            return
        span = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            b = self._rowbase(y) + x0 * 3
            self.px[b:b + len(span)] = span

    def hline(self, x0, x1, y, color):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x0 >= x1:
            return
        b = self._rowbase(y) + x0 * 3
        span = bytes(color) * (x1 - x0)
        self.px[b:b + len(span)] = span

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            b = (y * self.w + x) * 3
            self.px[b:b + 3] = bytes(color)

    def get_px(self, x, y):
        b = (y * self.w + x) * 3
        return tuple(self.px[b:b + 3])

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - dx, cx + dx + 1, cy + dy, color)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            self.hline(cx - dx, cx + dx + 1, cy + dy, color)

    def fill_polygon(self, pts, color):
        """Scanline polygon fill. pts = [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, ya = pts[i]
                x1, yb = pts[(i + 1) % n]
                if ya == yb:
                    continue
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(math.ceil(xs[i])), int(xs[i + 1]) + 1,
                           y, color)

    def vgrad_rect(self, x0, y0, x1, y1, stops):
        """Vertical gradient. stops = [(pos 0..1, color), ...] sorted."""
        for y in range(max(0, y0), min(self.h, y1)):
            t = (y - y0) / float(max(1, y1 - y0))
            c = grad_at(stops, t)
            self.hline(x0, x1, y, c)


def grad_at(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            return lerp(c0, c1, (t - p0) / max(1e-9, p1 - p0))
    return stops[-1][1]


# --------------------------------------------------------------------- font
# Classic 5x7 block font. Each glyph: 7 rows of 5 bits, MSB = left column.
FONT = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    ' ': (0, 0, 0, 0, 0, 0, 0),
}


def text_mask(text, scale):
    """Return (rows, width, height): rows are ints, bit x = pixel x set."""
    n = len(text)
    width = (n * 6 - 1) * scale
    height = 7 * scale
    rows = [0] * height
    for ci, ch in enumerate(text):
        glyph = FONT.get(ch.upper(), FONT[' '])
        xbase = ci * 6 * scale
        for r in range(7):
            bits = glyph[r]
            for c in range(5):
                if bits & (1 << (4 - c)):
                    for dx in range(scale):
                        for dy in range(scale):
                            rows[r * scale + dy] |= (
                                1 << (xbase + c * scale + dx))
    return rows, width, height


def draw_text(cv, text, cx, y, scale, color, outline_color, outline):
    """Centered text with a dark outline. Returns (x0, y0, x1, y1)."""
    rows, width, height = text_mask(text, scale)
    x0 = cx - width // 2
    # Dilate the mask by `outline` px (Chebyshev) for the outline layer.
    dil = []
    for r in range(height):
        v = rows[r]
        for s in range(1, outline + 1):
            v |= (rows[r] << s) | (rows[r] >> s)
        dil.append(v)
    out_rows = []
    for r in range(height):
        v = dil[r]
        for s in range(1, outline + 1):
            if 0 <= r - s < height:
                v |= dil[r - s]
            if 0 <= r + s < height:
                v |= dil[r + s]
        out_rows.append(v)
    for r in range(height):
        yy = y + r
        if yy < 0 or yy >= cv.h:
            continue
        m = rows[r]
        o = out_rows[r]
        # outline pixels: set in o but not in m
        bits = o & ~m
        while bits:
            lsb = bits & -bits
            x = lsb.bit_length() - 1
            cv.set_px(x0 + x, yy, outline_color)
            bits ^= lsb
        while m:
            lsb = m & -m
            x = lsb.bit_length() - 1
            cv.set_px(x0 + x, yy, color)
            m ^= lsb
    return (x0, y, x0 + width, y + height)


# ------------------------------------------------------------------- scene
def sky_color(y):
    stops = [(0.0, SKY_TOP), (0.45, SKY_MID), (0.82, SKY_LOW),
             (1.0, (250, 200, 120))]
    return grad_at(stops, (y - INSET) / float(HORIZON - INSET))


def draw_sky(cv):
    for y in range(INSET, HORIZON):
        cv.hline(INSET, W - INSET, y, sky_color(y))


def draw_sun_halo(cv, cx, cy, r):
    """Soft orange halo: concentric rings blended into the local sky."""
    steps = 30
    for i in range(steps, 0, -1):
        t = i / float(steps)          # 1 at the outer edge, ~0 at the disc
        rr = r + int(t * 190)
        alpha = 0.55 * (1.0 - t) ** 1.6 + 0.04
        for dy in range(-rr, rr + 1):
            yy = cy + dy
            if yy < INSET or yy >= HORIZON:
                continue
            dx = int(math.sqrt(max(0, rr * rr - dy * dy)))
            inner = int(math.sqrt(max(0, (rr - 7) * (rr - 7) - dy * dy))) \
                if rr > 7 else 0
            base = sky_color(yy)
            col = blend(base, SUN_HALO, alpha)
            if inner == 0:
                # band caps the ring: paint the whole width, centre included
                cv.hline(cx - dx, cx + dx + 1, yy, col)
            else:
                cv.hline(cx - dx, cx - inner, yy, col)
                cv.hline(cx + inner + 1, cx + dx + 1, yy, col)


def draw_cloud(cv, cx, cy, scale, color, peach=False):
    puffs = [(-1.6, 0.25, 1.15, 0.62), (-0.7, -0.25, 1.35, 0.75),
             (0.35, -0.35, 1.5, 0.85), (1.35, 0.0, 1.2, 0.65),
             (2.1, 0.3, 0.8, 0.5)]
    for dx, dy, rx, ry in puffs:
        c = CLOUD_PEACH if (peach and dx > 0.5) else color
        cv.fill_ellipse(int(cx + dx * scale), int(cy + dy * scale),
                        int(rx * scale), int(ry * scale), c)


def draw_bird(cv, x, y, s, color):
    cv.fill_polygon([(x - s, y), (x, y + int(s * 0.55)), (x + s, y)],
                    color)
    # thin wings: two short diagonals
    for i in range(s):
        cv.set_px(x - s + i, y - i // 2, color)
        cv.set_px(x + i, y - i // 2, color)


def draw_pine(cv, x, y, h, color):
    w = int(h * 0.42)
    cv.fill_polygon([(x, y - h), (x - w, y), (x + w, y)], color)
    cv.fill_polygon([(x, y - int(h * 0.72)), (x - int(w * 0.72), y - int(h * 0.28)),
                     (x + int(w * 0.72), y - int(h * 0.28))], color)
    cv.fill_rect(x - 3, y, x + 4, y + 10, color)


def draw_waterfall(cv):
    cx = 512
    top, base = 300, HORIZON
    # column: wide at the sea, narrower where it meets the clouds
    for y in range(top, base):
        t = (y - top) / float(base - top)      # 0 top -> 1 base
        half = int(48 + 34 * t + 7 * math.sin(y * 0.045))
        col = lerp(FALL_TOP, FALL_MID, t)
        cv.hline(cx - half, cx + half + 1, y, col)
    # pale inner core, brightest near the top
    for y in range(top, base):
        t = (y - top) / float(base - top)
        half = int((30 + 20 * t) * (1.0 + 0.08 * math.sin(y * 0.06)))
        col = lerp((255, 255, 255), FALL_TOP, t * 0.7)
        cv.hline(cx - half, cx + half + 1, y, col)
    # wavy vertical streaks inside the column
    streaks = [(-38, 0.052, 0.0), (-14, 0.061, 1.3), (10, 0.047, 2.6),
               (34, 0.058, 4.1)]
    for off, freq, phase in streaks:
        for y in range(top + 6, base - 4, 2):
            x = cx + off + int(9 * math.sin(y * freq + phase))
            cv.fill_rect(x - 1, y, x + 2, y + 2, FOAM)
    # foam where the fall meets the sea
    for fx, fy, frx, fry in [(470, 656, 62, 14), (545, 660, 70, 15),
                             (512, 648, 46, 12), (430, 662, 34, 9),
                             (596, 662, 30, 8)]:
        cv.fill_ellipse(fx, fy, frx, fry, FOAM)
    # spray dots above the foam
    for i in range(26):
        ang = math.pi * (0.15 + 0.7 * ((i * 37) % 100) / 100.0)
        dist = 55 + ((i * 53) % 40)
        x = int(cx + math.cos(ang) * dist * 1.5)
        yy = int(640 - math.sin(ang) * dist * 0.55)
        cv.fill_circle(x, yy, 2 + (i % 3), FOAM)


def draw_sea(cv):
    cv.vgrad_rect(INSET, HORIZON, W - INSET, H - INSET,
                  [(0.0, SEA_TOP), (1.0, SEA_BOT)])
    # faint horizontal wave lines, sparse and irregular
    for i in range(12):
        y = HORIZON + 30 + i * 27 + ((i * 41) % 11)
        x0 = INSET + 40 + ((i * 211) % 420)
        x1 = x0 + 90 + ((i * 131) % 200)
        col = blend(SEA_TOP, (255, 255, 255), 0.09 + 0.04 * (i % 2))
        cv.hline(x0, min(W - INSET - 20, x1), y, col)
    # sun reflection: warm horizontal streaks under the sun (right side)
    for i in range(16):
        y = HORIZON + 18 + i * 17
        wdt = 300 - i * 9
        x0 = 830 - wdt // 2 + ((i * 31) % 40) - 20
        x1 = x0 + wdt - ((i * 47) % 90)
        col = blend(sea_at(y), REFL, 0.55 - i * 0.022)
        cv.hline(max(INSET, x0), min(W - INSET, x1), y, col)
        cv.hline(max(INSET, x0 + 14), min(W - INSET, x1 - 10), y + 1, col)


def sea_at(y):
    t = (y - HORIZON) / float(H - INSET - HORIZON)
    return lerp(SEA_TOP, SEA_BOT, max(0.0, min(1.0, t)))


def draw_sailboat(cv, x, y, s):
    # hull
    cv.fill_polygon([(x - int(34 * s), y), (x + int(34 * s), y),
                     (x + int(22 * s), y + int(12 * s)),
                     (x - int(22 * s), y + int(12 * s))], HULL)
    # mast
    cv.fill_rect(x - 1, y - int(62 * s), x + 2, y, HULL)
    # main sail (white) and jib (amber)
    cv.fill_polygon([(x + 3, y - int(58 * s)), (x + 3, y - 4),
                     (x + int(34 * s), y - 4)], SAIL_WHITE)
    cv.fill_polygon([(x - 3, y - int(52 * s)), (x - 3, y - 4),
                     (x - int(30 * s), y - 4)], SAIL_AMBER)
    # reflection + wake
    cv.hline(x - int(40 * s), x + int(44 * s), y + int(16 * s),
             blend(sea_at(y + int(16 * s)), (255, 255, 255), 0.25))
    cv.hline(x - int(26 * s), x + int(30 * s), y + int(22 * s),
             blend(sea_at(y + int(22 * s)), (255, 255, 255), 0.16))


def draw_cliffs(cv):
    # left cliff + pines
    cv.fill_polygon([(INSET, HORIZON), (INSET, 470), (120, 400),
                     (190, 430), (235, 520), (250, HORIZON)], CLIFF)
    draw_pine(cv, 150, 415, 62, PINE)
    draw_pine(cv, 185, 428, 48, PINE)
    draw_pine(cv, 118, 425, 40, PINE)
    # right headland the sun half-hides behind
    cv.fill_polygon([(880, HORIZON), (895, 430), (930, 330),
                     (985, 300), (W - INSET, 320), (W - INSET, HORIZON)],
                    CLIFF)
    draw_pine(cv, 950, 330, 44, PINE)
    draw_pine(cv, 985, 325, 34, PINE)


def draw_poster():
    cv = Canvas(W, H)
    cv.fill_rect(0, 0, W, H, CREAM)          # frame
    draw_sky(cv)
    # flat peach clouds drifting in the sky
    draw_cloud(cv, 255, 300, 26, CLOUD, peach=True)
    draw_cloud(cv, 775, 320, 19, CLOUD, peach=True)
    # sun: halo, then disc, then the headland covers its right side
    draw_sun_halo(cv, 830, 470, 95)
    cv.fill_circle(830, 470, 95, SUN_OUT)
    cv.fill_circle(830, 470, 68, SUN_IN)
    draw_cliffs(cv)
    # the waterfall climbs from the sea into the clouds
    draw_waterfall(cv)
    draw_cloud(cv, 512, 285, 42, CLOUD)
    draw_cloud(cv, 512, 262, 30, CLOUD)
    # birds
    for bx, by, bs in [(300, 250, 9), (345, 285, 7), (700, 330, 8),
                       (660, 290, 6), (250, 350, 6)]:
        draw_bird(cv, bx, by, bs, INK)
    draw_sea(cv)
    # waterfall foam sits on the sea line: redraw the base foam over sea
    for fx, fy, frx, fry in [(470, 656, 62, 14), (545, 660, 70, 15),
                             (512, 648, 46, 12)]:
        cv.fill_ellipse(fx, fy, frx, fry, FOAM)
    draw_sailboat(cv, 295, 800, 1.15)
    # title + tagline on the sky
    draw_text(cv, "VELMARA", W // 2, 52, 18, CREAM, INK, 5)
    draw_text(cv, "WHERE THE WATER CLIMBS TO THE SKY", W // 2, 196, 4,
              CREAM, INK, 2)
    return cv


# ---------------------------------------------------------------------- png
def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.path.dirname(
        os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    cv = draw_poster()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, cv)
    print("wrote %s (%d bytes)" % (path, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
