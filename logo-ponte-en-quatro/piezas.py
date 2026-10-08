"""Animaciones del logo de Ponte en Quatro por piezas (letras separables del PNG).

Uso: python3 piezas.py golpe      -> logo-golpe-4k.mov
     python3 piezas.py explosion  -> logo-explosion-4k.mov
Vídeo 2160x3840, 3 s, fondo transparente (QuickTime Animation) para CapCut.
"""
import math, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage

MODE = sys.argv[1]
W, H, FPS, DUR = 2160, 3840, 30, 3.0
LOGO_W = 1800

# --- logo escalado y centrado -------------------------------------------------
src = np.array(Image.open("logo.png").convert("RGBA"))
ys, xs = np.nonzero(src[..., 3] > 8)
crop = Image.fromarray(src[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
crop = crop.resize((LOGO_W, round(crop.height * LOGO_W / crop.width)), Image.LANCZOS)
alpha = np.array(crop)[..., 3]
lh, lw = alpha.shape
ox, oy = (W - lw) // 2, (H - lh) // 2

# --- piezas: componentes conexas; los bordes suaves van a la pieza más cercana ---
lab, n = ndimage.label(alpha > 100)
sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
keep = [i + 1 for i, s in enumerate(sizes) if s > 500]
lab = np.where(np.isin(lab, keep), lab, 0)
_, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
owner = lab[iy, ix]
pieces = []
for k in keep:
    m = (owner == k) & (alpha > 0)
    yy, xx = np.nonzero(m)
    y0, y1, x0, x1 = yy.min(), yy.max() + 1, xx.min(), xx.max() + 1
    a = np.where(m[y0:y1, x0:x1], alpha[y0:y1, x0:x1], 0).astype(np.uint8)
    img = np.zeros(a.shape + (4,), np.uint8); img[..., :3] = 255; img[..., 3] = a
    pieces.append({"img": Image.fromarray(img), "cx": ox + (x0 + x1) / 2, "cy": oy + (y0 + y1) / 2})
pieces.sort(key=lambda p: (p["cx"], p["cy"]))      # orden de lectura aproximado, de izquierda a derecha

def spring(x0, v0, k, c, secs, target=0.0, dt=1 / 240):
    """Muelle amortiguado muestreado a FPS: devuelve x(t) por fotograma."""
    x, v, out = x0, v0, []
    for i in range(1, int(secs / dt) + 1):
        v += (-k * (x - target) - c * v) * dt; x += v * dt
        if i % int(1 / FPS / dt) == 0: out.append(x)
    return out

NF = int(DUR * FPS)
rnd = np.random.default_rng(4)
state = [[None] * len(pieces) for _ in range(NF)]   # por fotograma y pieza: (dx, dy, sx, sy, rot, opacity)
shake = [(0.0, 0.0)] * NF

if MODE == "golpe":
    S0, FALL, STAG, T0 = 3.2, 0.15, 0.085, 0.2
    impacts = []
    for i, p in enumerate(pieces):
        t0 = T0 + i * STAG; ti = t0 + FALL; impacts.append(ti)
        sq = spring(0.3, 0, 900, 15, DUR)
        for f in range(NF):
            t = f / FPS
            if t < t0: state[f][i] = None; continue
            if t < ti:
                u = (t - t0) / FALL; s = 1 + (S0 - 1) * (1 - u * u)
                state[f][i] = (0, 0, s, s, 0, min(1, u * 2.5))
            else:
                j = min(len(sq) - 1, int((t - ti) * FPS)); a = sq[j]
                state[f][i] = (0, 0, 1 + 0.6 * a, 1 - a, 0, 1)
    for f in range(NF):
        t = f / FPS; x = y = 0.0
        for k, ti in enumerate(impacts):
            d = t - ti
            if d < 0: continue
            amp = 22 * math.exp(-8 * d); ph = 2 * math.pi * 16 * d
            x += amp * math.sin(ph + k * 1.7); y += amp * 0.8 * math.cos(ph * 1.13 + k)
        shake[f] = (x, y)

elif MODE == "explosion":
    for i, p in enumerate(pieces):
        ang = math.atan2(p["cy"] - H / 2, p["cx"] - W / 2) + rnd.uniform(-0.5, 0.5)
        dist = rnd.uniform(1700, 2300)
        dx0, dy0 = math.cos(ang) * dist, math.sin(ang) * dist
        r0 = rnd.uniform(-260, 260); s0 = rnd.choice([rnd.uniform(0.35, 0.6), rnd.uniform(1.6, 2.2)])
        t0 = 0.1 + rnd.uniform(0, 0.35); K = rnd.uniform(4.2, 5.2)
        for f in range(NF):
            t = f / FPS - t0
            if t < 0: state[f][i] = None; continue
            e = math.exp(-K * t)                       # llegan frenando como si flotaran
            wob = 1 + 0.06 * math.exp(-3.5 * t) * math.sin(2 * math.pi * 2.2 * t)  # pequeño rebote al encajar
            s = (1 + (s0 - 1) * e) * wob
            # trayectoria curva: el desplazamiento gira un poco mientras se frena
            a2 = 0.9 * e
            dx = (dx0 * math.cos(a2) - dy0 * math.sin(a2)) * e
            dy = (dx0 * math.sin(a2) + dy0 * math.cos(a2)) * e
            state[f][i] = (dx, dy, s, s, r0 * e, min(1, t / 0.15))

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", f"logo-{MODE}-4k.mov"], stdin=subprocess.PIPE)
for f in range(NF):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sx_, sy_ = shake[f]
    for i, p in enumerate(pieces):
        st = state[f][i]
        if st is None: continue
        dx, dy, sx, sy, rot, op = st
        img = p["img"]
        w, h = max(1, round(img.width * sx)), max(1, round(img.height * sy))
        im = img.resize((w, h), Image.BILINEAR) if (w, h) != img.size else img
        if abs(rot) > 0.05: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        if op < 1:
            a = np.array(im); a[..., 3] = (a[..., 3] * op).astype(np.uint8); im = Image.fromarray(a)
        x = round(p["cx"] + dx + sx_ - im.width / 2); y = round(p["cy"] + dy + sy_ - im.height / 2)
        if x > W or y > H or x + im.width < 0 or y + im.height < 0: continue
        frame.alpha_composite(im, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    proc.stdin.write(frame.tobytes())
proc.stdin.close(); proc.wait()
print("ok", MODE, len(pieces), "piezas")
