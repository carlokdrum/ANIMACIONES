"""ALFIO LORA: el logo se construye solo con planos de cámara (8 s, 1920x1080, fondo negro).

- La onda entra como una serpiente siguiendo su propio recorrido.
- El monograma y las letras se trazan a lo largo de su forma (esqueleto + distancia geodésica).
- Cámara 3D por homografía: primerísimo plano que persigue a la serpiente, contrapicado,
  travelling por el nombre y plano general de revelación, con desenfoque de movimiento en los cortes.

Uso: python3 cinematica.py  ->  alfio-lora-cinematica.mp4
"""
import math, subprocess
from collections import deque
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage.morphology import skeletonize

OUT_W, OUT_H, FPS, DUR = 1920, 1080, 30, 10.0
LOGO_W = 2400

# ---------------------------------------------------------------- logo y regiones
src = np.array(Image.open("logo.webp").convert("RGB")).astype(np.float32) / 255
alpha = np.clip((src.max(2) - 0.03) / 0.12, 0, 1)
color = np.clip(src / np.maximum(alpha[..., None], 1e-3), 0, 1)
ys, xs = np.nonzero(alpha > 0.02)
y0, x0 = ys.min() - 30, xs.min() - 30
alpha, color = alpha[y0:ys.max() + 31, x0:xs.max() + 31], color[y0:ys.max() + 31, x0:xs.max() + 31]
S = LOGO_W / alpha.shape[1]
def up(arr):
    return np.array(Image.fromarray((arr * 255).astype(np.uint8)).resize(
        (LOGO_W, round(arr.shape[0] * S)), Image.LANCZOS)).astype(np.float32) / 255
alpha, color = up(alpha), up(color)
LH, LW = alpha.shape
premul = np.dstack([color * alpha[..., None], alpha])

solid = alpha > 0.35
teal = solid & (color[..., 2] > color[..., 0] + 0.08)
lime = solid & ~teal
split = round((690 - y0) * S)
rows = np.arange(LH)[:, None]
lab = np.zeros(alpha.shape, np.int32); lab[teal] = 1
regions = {"onda": [1], "mono": [], "texto": []}
nid = 2
for name, msk in (("mono", lime & (rows < split)), ("texto", lime & (rows >= split))):
    L, _ = ndimage.label(msk); objs = ndimage.find_objects(L)
    comps = sorted([(objs[i][1].start, i + 1) for i in range(len(objs)) if (L == i + 1).sum() > 400 * S * S])
    for _, k in comps:
        lab[L == k] = nid; regions[name].append(nid); nid += 1
_, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
owner = np.where(alpha > 0, lab[iy, ix], 0)

def geodesic_param(rid, start_key):
    """Recorrido de construcción: distancia geodésica sobre el esqueleto desde un extremo."""
    m = owner == rid
    sk = skeletonize(m & (alpha > 0.5))
    skl, _ = ndimage.label(sk, structure=np.ones((3, 3)))       # solo el trazo principal del esqueleto
    sk = skl == (np.bincount(skl.ravel())[1:].argmax() + 1)
    pts = np.argwhere(sk)
    key = {"izq": pts[:, 1], "abajo_izq": pts[:, 1] - pts[:, 0], "abajo": -pts[:, 0], "arriba_izq": pts[:, 1] + pts[:, 0]}[start_key]
    st = tuple(pts[np.argmin(key)])
    dist = np.full(sk.shape, -1.0, np.float32); dist[st] = 0
    q = deque([st])
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if (dy or dx) and 0 <= ny < sk.shape[0] and 0 <= nx < sk.shape[1] and sk[ny, nx] and dist[ny, nx] < 0:
                    dist[ny, nx] = dist[y, x] + (1.4142 if dy and dx else 1.0); q.append((ny, nx))
    reach = dist >= 0
    _, (jy, jx) = ndimage.distance_transform_edt(~reach, return_indices=True)
    par = dist[jy, jx] / max(1.0, dist.max())
    return np.where(m, par, 2.0).astype(np.float32)

param = np.full(alpha.shape, 2.0, np.float32)
region_of = {}
for name, start in (("onda", "izq"), ("mono", None), ("texto", "arriba_izq")):
    for j, rid in enumerate(regions[name]):
        sk_start = start or ("abajo_izq" if j == 0 else "abajo")
        p = geodesic_param(rid, sk_start)
        param = np.where(owner == rid, p, param)
        region_of[rid] = name

# ---------------------------------------------------------------- guion temporal
smooth = lambda u: (lambda v: v * v * (3 - 2 * v))(min(1.0, max(0.0, u)))
ease_out = lambda u: 1 - (1 - min(1.0, max(0.0, u))) ** 3

def snake_head(t):
    """Ritmo de contraste: avanza despacio (0.2-2.8 s, hasta el 40 %) y acelera (3.0-4.2 s, hasta el final)."""
    if t < 0.2: return 0.0
    if t < 2.8: return 0.40 * smooth((t - 0.2) / 2.6) ** 0.9
    if t < 3.0: return 0.40
    return min(1.0, 0.40 + 0.60 * smooth((t - 3.0) / 1.2))

TRACE = {regions["mono"][0]: (4.2, 1.1)}
if len(regions["mono"]) > 1: TRACE[regions["mono"][1]] = (4.6, 0.9)
for i, rid in enumerate(regions["texto"]): TRACE[rid] = (5.65 + i * 0.13, 0.35)

def build(t):
    """Imagen premultiplicada del logo en construcción (en coordenadas del logo) y posición de la cabeza."""
    head = np.zeros(alpha.shape, np.float32)
    vis = np.zeros(alpha.shape, np.float32)
    on = owner == 1
    h = snake_head(t)
    vis = np.where(on, np.clip((h - param) / 0.006 + 0.5, 0, 1), vis)
    hot = np.where(on, np.exp(-((param - h) / 0.025) ** 2) * (param <= h + 0.01) * (1 - smooth((t - 4.1) / 0.4)), 0)
    for rid, (t0, d) in TRACE.items():
        u = (t - t0) / d
        if u <= 0: continue
        hh = ease_out(u) * 1.02
        m = owner == rid
        vis = np.where(m, np.clip((hh - param) / 0.02 + 0.5, 0, 1), vis)
        hot = np.where(m, np.exp(-((param - hh) / 0.05) ** 2) * (1 - smooth((u - 0.9) / 0.3)), hot)
    img = premul * vis[..., None]
    a = alpha * vis * hot
    img[..., :3] = np.minimum(img[..., 3:4], img[..., :3] + a[..., None] * np.array([0.9, 1.0, 1.0]))   # borde al rojo blanco
    # posición de la cabeza de la serpiente (para que la cámara la persiga)
    band = on & (np.abs(param - h) < 0.01)
    hy, hx = (np.argwhere(band).mean(0) if band.any() else (LH * 0.8, LW * 0.1))
    return img, (hx, hy), hot

# ---------------------------------------------------------------- cámara 3D
BASE = 1500 / LW            # escala del plano general: el logo ocupa 1500 px de ancho

def homography(cx, cy, zoom, yaw=0.0, pitch=0.0, roll=0.0):
    D = 3000.0; f = D * BASE * zoom
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    Ry = np.array([[cyw, 0, syw], [0, 1, 0], [-syw, 0, cyw]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    R = Rz @ Rx @ Ry
    tvec = R @ np.array([-cx, -cy, 0.0]) + np.array([0, 0, D])
    K = np.array([[f, 0, OUT_W / 2], [0, f, OUT_H / 2], [0, 0, 1]])
    Hm = K @ np.column_stack([R[:, 0], R[:, 1], tvec])
    Hi = np.linalg.inv(Hm); Hi /= Hi[2, 2]
    return tuple(Hi.flatten()[:8])

lerp = lambda a, b, u: a + (b - a) * u
cam_state = {"shot": None, "hx": 0.0, "hy": 0.0}

def follow(shot, hx, hy, k=0.3):
    """Sigue la cabeza de la serpiente con suavizado; se reinicia en cada corte."""
    if cam_state["shot"] != shot:
        cam_state.update(shot=shot, hx=hx, hy=hy)
    cam_state["hx"] += (hx - cam_state["hx"]) * k; cam_state["hy"] += (hy - cam_state["hy"]) * k
    return cam_state["hx"], cam_state["hy"]

CUTS = [2.9, 3.4, 3.8, 4.2, 5.6, 7.0]

def camera(t, head):
    """Plano de cámara en el instante t: (cx, cy, zoom, yaw, pitch, roll)."""
    hx, hy = head
    if t < 2.9:                                    # 1) lento: primerísimo plano que se desliza con la serpiente
        x, y = follow(1, hx, hy, 0.12)
        return (x + 90, y, lerp(2.7, 2.3, t / 2.9), lerp(10, 4, t / 2.9), -5, 0)
    if t < 3.4:                                    # 2a) rápido: ángulo lateral derecho
        x, y = follow(2, hx, hy, 0.4); return (x + 60, y, 2.2, 32, -8, 4)
    if t < 3.8:                                    # 2b) rápido: ángulo contrario, desde abajo
        x, y = follow(3, hx, hy, 0.4); return (x + 60, y, 2.0, -30, 16, -7)
    if t < 4.2:                                    # 2c) rápido: más abierto, contrapicado
        x, y = follow(4, hx, hy, 0.4); return (x, y - 80, 1.45, -12, 26, 3)
    if t < 5.6:                                    # 3) lento: órbita en contrapicado alrededor del monograma
        u = smooth((t - 4.2) / 1.4)
        return (LW * 0.33, LH * 0.42, lerp(1.6, 1.4, u), lerp(-40, 18, u), lerp(20, 14, u), lerp(-5, 3, u))
    if t < 7.0:                                    # 4) rápido: travelling por el nombre mientras se escribe
        u = smooth((t - 5.6) / 1.3)
        return (lerp(LW * 0.10, LW * 0.92, u), LH * 0.86, 2.1, lerp(14, -14, u), -10, 0)
    if t < 8.0:                                    # 5) calma: se aleja despacio hasta el plano general
        u = ease_out((t - 7.0) / 1.0)
        return (lerp(LW * 0.62, LW * 0.5, u), lerp(LH * 0.62, LH * 0.5, u), lerp(1.9, 1.08, u), lerp(24, 0, u), lerp(-12, 0, u), lerp(6, 0, u))
    d = t - 8.0                                    # 6) impacto: golpe de cámara hacia el logo y sacudida
    punch = 0.16 * math.exp(-5 * d) * math.cos(9 * d)
    shake = 22 * math.exp(-7 * d)
    return (LW * 0.5 + shake * math.sin(70 * d), LH * 0.5 + shake * math.cos(83 * d), 1.0 + punch + 0.04 * smooth(d / 2.0), 0, 0, 0.6 * math.exp(-6 * d) * math.sin(50 * d))

def whip(t):
    """Intensidad del barrido en los cortes (desenfoque de movimiento horizontal)."""
    return max([math.exp(-((t - c) / 0.05) ** 2) for c in CUTS] + [0.0])

def exposure(t):
    """Baja la luz antes del golpe (7.3-8.0 s) y destello blanco en el impacto."""
    dip = 1 - 0.55 * smooth((t - 7.3) / 0.6) if t < 8.0 else 1.0
    flash = 0.95 * math.exp(-max(0, t - 8.0) / 0.18) if t >= 8.0 else 0.0
    return dip, flash

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", "alfio-lora-cinematica.mp4"], stdin=subprocess.PIPE)

xx = np.arange(LW, dtype=np.float32)[None, :]; yy = np.arange(LH, dtype=np.float32)[:, None]
for f in range(int(DUR * FPS)):
    t = f / FPS
    img, head, hot = build(t)

    # destello final: bloom y reflejo de luz que recorre el logo terminado
    sweep_u = (t - 8.25) / 0.9
    if 0 < sweep_u < 1:
        c = -400 + (LW + LH * 0.5 + 800) * smooth(sweep_u)
        band = np.exp(-(((xx + yy * 0.5) - c) / 110) ** 2)[..., None]
        img[..., :3] = np.minimum(img[..., 3:4], img[..., :3] + band * 0.9 * img[..., 3:4])
    dip, flash = exposure(t)
    if flash > 0.01:                                # destello: el logo se quema a blanco y vuelve
        img[..., :3] = img[..., :3] + (img[..., 3:4] - img[..., :3]) * flash
    img[..., :3] *= dip; img[..., 3] = np.maximum(img[..., 3] * 1.0, 0)
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBa")
    pulse = 0.12 * (0.5 + 0.5 * math.sin((t - 8.6) * 2 * math.pi / 1.1)) if t > 8.6 else 0.0
    glow_amt = (0.35 + 1.3 * math.exp(-max(0, t - 8.0) / 0.35) * (t >= 8.0) + pulse) * dip
    glow = pil.resize((LW // 4, LH // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize((LW, LH), Image.BILINEAR)

    # cámara (con submuestras de movimiento en los barridos)
    w = whip(t)
    subs = [t + d for d in ((-0.02, -0.01, 0.0, 0.01, 0.02) if w > 0.05 else (0.0,))]
    acc = np.zeros((OUT_H, OUT_W, 3), np.float32)
    for ts in subs:
        cam = camera(ts, head)
        co = homography(*cam)
        a = np.asarray(pil.transform((OUT_W, OUT_H), Image.PERSPECTIVE, co, Image.BICUBIC)).astype(np.float32)[..., :3]
        g = np.asarray(glow.transform((OUT_W, OUT_H), Image.PERSPECTIVE, co, Image.BILINEAR)).astype(np.float32)[..., :3]
        acc += np.minimum(255, a + g * glow_amt)
    frame = acc / len(subs)
    if w > 0.05:                                    # estela horizontal del barrido
        k = int(8 + 60 * w)
        frame = ndimage.uniform_filter1d(frame, size=k, axis=1)
    proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    if f % 30 == 0: print("t", round(t, 1), flush=True)

proc.stdin.close(); proc.wait()
print("ok")
