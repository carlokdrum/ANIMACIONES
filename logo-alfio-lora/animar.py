"""Animación cinematográfica del logo ALFIO LORA.

Uso: python3 animar.py  ->  alfio-lora-4k.mov (3840x2160, 5 s, fondo transparente, QuickTime Animation)
"""
import math, subprocess
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

W, H, FPS, DUR = 3840, 2160, 30, 5.0
LOGO_W = 3000

# --- separar el logo del fondo negro (sin premultiplicar el negro) ----------------
src = np.array(Image.open("logo.webp").convert("RGB")).astype(np.float32) / 255
m = src.max(2)
alpha = np.clip((m - 0.03) / 0.12, 0, 1)
color = np.clip(src / np.maximum(alpha[..., None], 1e-3), 0, 1)
ys, xs = np.nonzero(alpha > 0.02)
y0, y1, x0, x1 = ys.min() - 20, ys.max() + 21, xs.min() - 20, xs.max() + 21
alpha, color = alpha[y0:y1, x0:x1], color[y0:y1, x0:x1]
S = LOGO_W / alpha.shape[1]
def up(arr):
    return np.array(Image.fromarray((arr * 255).astype(np.uint8)).resize(
        (LOGO_W, round(arr.shape[0] * S)), Image.LANCZOS)).astype(np.float32) / 255
alpha, color = up(alpha), up(color)
LH, LW = alpha.shape

# --- regiones: onda turquesa, monograma (A, trazo) y letras del nombre ---------------
solid = alpha > 0.35
teal = solid & (color[..., 2] > color[..., 0] + 0.08)
lime = solid & ~teal
split = round((690 - y0) * S)                     # separación entre monograma y nombre
lab = np.zeros(alpha.shape, np.int32)
lab[teal] = 1
top, _ = ndimage.label(lime & (np.arange(LH)[:, None] < split))
bot, _ = ndimage.label(lime & (np.arange(LH)[:, None] >= split))
regions = [("onda", 1)]
nid = 2
for name, L in (("mono", top), ("texto", bot)):
    objs = ndimage.find_objects(L)
    comps = [(i + 1, objs[i][1].start) for i in range(len(objs)) if (L == i + 1).sum() > 400 * S * S]
    for k, _x in sorted(comps, key=lambda c: c[1]):
        lab[L == k] = nid; regions.append((name, nid)); nid += 1
_, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
owner = lab[iy, ix]

def layer(rid):
    a = np.where(owner == rid, alpha, 0)
    yy, xx = np.nonzero(a > 0)
    r0, r1, c0, c1 = yy.min(), yy.max() + 1, xx.min(), xx.max() + 1
    rgba = np.dstack([color[r0:r1, c0:c1] * a[r0:r1, c0:c1, None], a[r0:r1, c0:c1]])   # premultiplicado
    return {"rgba": rgba, "x": c0, "y": r0}
L = {rid: layer(rid) for _, rid in regions}
mono = [rid for n, rid in regions if n == "mono"]
texto = [rid for n, rid in regions if n == "texto"]

def to_img(rgba):
    return Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBa")

def place(canvas, rgba, x, y, scale=1.0, blur=0.0, op=1.0):
    """Compone una capa premultiplicada (escala desde su centro, desenfoque, opacidad)."""
    if op <= 0.003: return
    img = to_img(rgba * op)
    h, w = rgba.shape[:2]
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)
    pad = int(blur * 3) + 2
    if blur > 0.3:
        big = Image.new("RGBa", (img.width + 2 * pad, img.height + 2 * pad)); big.paste(img, (pad, pad))
        img = big.filter(ImageFilter.GaussianBlur(blur))
    else:
        pad = 0
    arr = np.asarray(img).astype(np.float32) / 255
    cx, cy = x + w / 2, y + h / 2
    px, py = round(cx - img.width / 2), round(cy - img.height / 2)
    sx0, sy0 = max(0, -px), max(0, -py)
    dx0, dy0 = max(0, px), max(0, py)
    hh = min(arr.shape[0] - sy0, canvas.shape[0] - dy0); ww = min(arr.shape[1] - sx0, canvas.shape[1] - dx0)
    if hh <= 0 or ww <= 0: return
    src_ = arr[sy0:sy0 + hh, sx0:sx0 + ww]; dst = canvas[dy0:dy0 + hh, dx0:dx0 + ww]
    dst[:] = src_ + dst * (1 - src_[..., 3:4])

ease_out = lambda u: 1 - (1 - min(1, max(0, u))) ** 3
smooth = lambda u: (lambda v: v * v * (3 - 2 * v))(min(1, max(0, u)))

onda = L[regions[0][1]]
ox_w = np.arange(onda["rgba"].shape[1]) + onda["x"]
X_START, X_END = onda["x"], onda["x"] + onda["rgba"].shape[1]
xx_logo = np.arange(LW)[None, :].astype(np.float32); yy_logo = np.arange(LH)[:, None].astype(np.float32)

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", "alfio-lora-4k.mov"], stdin=subprocess.PIPE)

for f in range(int(DUR * FPS)):
    t = f / FPS
    cv = np.zeros((LH, LW, 4), np.float32)

    # 1) la onda se dibuja de izquierda a derecha con una cabeza de luz
    head = X_START + (X_END - X_START) * smooth(t / 1.3)
    if t > 0:
        rev = np.clip((head - ox_w) / 8 + 0.5, 0, 1)[None, :, None]
        place(cv, onda["rgba"] * rev, onda["x"], onda["y"])
        glow_amt = 1 - smooth((t - 1.2) / 0.4)
        if glow_amt > 0.01:
            band = np.exp(-((ox_w - head) / 70) ** 2)[None, :] * (ox_w <= head + 10)[None, :]
            a = onda["rgba"][..., 3] * band * glow_amt
            g = np.dstack([np.stack([a * 0.75, a, a], -1), a])                    # blanco azulado
            place(cv, g, onda["x"], onda["y"], blur=18 * S / 2)
            place(cv, g * 0.9, onda["x"], onda["y"])

    # 2) monograma: llega desde la cámara, desenfocado, y se asienta
    for i, rid in enumerate(mono):
        u = (t - (0.35 + i * 0.22)) / 0.75
        if u <= 0: continue
        e = ease_out(u); wob = 1 + 0.025 * math.exp(-6 * max(0, u - 1) * 0.75) * math.sin(14 * max(0, u - 1) * 0.75) if u > 1 else 1
        p = L[rid]
        place(cv, p["rgba"], p["x"], p["y"], scale=(1 + 0.7 * (1 - e)) * wob, blur=30 * (1 - e), op=min(1, u * 2.2))

    # 3) el nombre, letra a letra: sube, se enfoca y se junta
    tx = [L[r]["x"] + L[r]["rgba"].shape[1] / 2 for r in texto]; tcx = (min(tx) + max(tx)) / 2
    for i, rid in enumerate(texto):
        u = (t - (1.5 + i * 0.075)) / 0.6
        if u <= 0: continue
        e = ease_out(u); p = L[rid]
        cx = p["x"] + p["rgba"].shape[1] / 2
        place(cv, p["rgba"], p["x"] + (cx - tcx) * 0.22 * (1 - e), p["y"] + 90 * (1 - e), blur=16 * (1 - e), op=min(1, u * 1.8))

    # 4) bloom y reflejo de luz que recorre el logo
    bloom = math.exp(-((t - 2.65) / 0.22) ** 2) * 0.55
    sweep_u = (t - 2.55) / 0.85
    if 0 < sweep_u < 1 or bloom > 0.01:
        base = cv.copy()
        if 0 < sweep_u < 1:
            c = -500 + (LW + LH * 0.45 + 1000) * smooth(sweep_u)
            band = np.exp(-(((xx_logo + yy_logo * 0.45) - c) / 120) ** 2)[..., None]
            cv[..., :3] = np.minimum(cv[..., 3:4], cv[..., :3] + band * 0.85 * cv[..., 3:4])
        if bloom > 0.01:
            img = to_img(base).filter(ImageFilter.GaussianBlur(60))
            b = np.asarray(img).astype(np.float32) / 255 * bloom
            cv = b + cv * (1 - b[..., 3:4])

    # 5) cámara: acercamiento lento y continuo
    cam = 1.07 - 0.07 * ease_out(t / DUR)
    frame = np.zeros((H, W, 4), np.float32)
    place(frame, cv, (W - LW) / 2, (H - LH) / 2, scale=cam)
    out = frame.copy()
    a = out[..., 3:4]
    out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)     # a alfa recto
    proc.stdin.write((np.clip(out, 0, 1) * 255).astype(np.uint8).tobytes())
    if f % 30 == 0: print("t", t, flush=True)

proc.stdin.close(); proc.wait()
print("ok", len(mono), "piezas de monograma,", len(texto), "piezas de texto")
