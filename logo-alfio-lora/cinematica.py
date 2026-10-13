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

OUT_W, OUT_H, FPS, DUR = 1920, 1080, 30, 8.0
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
    """Avance de la serpiente con ritmo irregular (acelera y frena) entre 0.15 s y 3.4 s."""
    u = min(1.0, max(0.0, (t - 0.15) / 3.25))
    return min(1.0, u + 0.035 * math.sin(u * math.pi * 7) * math.sin(u * math.pi)) if u < 1 else 1.0

TRACE = {regions["mono"][0]: (2.0, 1.2)}
if len(regions["mono"]) > 1: TRACE[regions["mono"][1]] = (2.6, 0.9)
for i, rid in enumerate(regions["texto"]): TRACE[rid] = (3.7 + i * 0.2, 0.55)

def build(t):
    """Imagen premultiplicada del logo en construcción (en coordenadas del logo) y posición de la cabeza."""
    head = np.zeros(alpha.shape, np.float32)
    vis = np.zeros(alpha.shape, np.float32)
    on = owner == 1
    h = snake_head(t)
    vis = np.where(on, np.clip((h - param) / 0.006 + 0.5, 0, 1), vis)
    hot = np.where(on, np.exp(-((param - h) / 0.025) ** 2) * (param <= h + 0.01) * (1 - smooth((t - 3.3) / 0.4)), 0)
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
cam_state = {"hx": None, "hy": None}

def camera(t, head):
    """Plano de cámara en el instante t: (cx, cy, zoom, yaw, pitch, roll)."""
    hx, hy = head
    if t < 2.2:                                    # 1) primerísimo plano persiguiendo a la serpiente
        if cam_state["hx"] is None: cam_state["hx"], cam_state["hy"] = hx, hy
        cam_state["hx"] += (hx - cam_state["hx"]) * 0.35; cam_state["hy"] += (hy - cam_state["hy"]) * 0.25
        return (cam_state["hx"] + 120, cam_state["hy"], 2.5 - 0.3 * t / 2.2, 8 * math.sin(t * 2.1), -6, 5 * math.sin(t * 1.6))
    if t < 3.6:                                    # 2) contrapicado en perspectiva sobre el monograma
        u = (t - 2.2) / 1.4
        return (lerp(LW * 0.30, LW * 0.36, u), LH * 0.42, lerp(1.55, 1.35, u), lerp(-38, -30, u), lerp(22, 16, u), -6)
    if t < 5.4:                                    # 3) travelling lateral por el nombre
        u = smooth((t - 3.6) / 1.8)
        return (lerp(LW * 0.12, LW * 0.88, u), LH * 0.86, 2.0, lerp(12, -12, u), -10, 0)
    u = ease_out((t - 5.4) / 1.9)                  # 4) revelación: se aleja girando hasta el plano general
    return (lerp(LW * 0.70, LW * 0.5, u), lerp(LH * 0.70, LH * 0.5, u), lerp(2.3, 1.0, u) + 0.05 * smooth((t - 7.0) / 1.0),
            lerp(40, 0, u), lerp(-18, 0, u), lerp(10, 0, u))

CUTS = [2.2, 3.6, 5.4]
def whip(t):
    """Intensidad del barrido en los cortes (desenfoque de movimiento horizontal)."""
    return max([math.exp(-((t - c) / 0.07) ** 2) for c in CUTS] + [0.0])

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", "alfio-lora-cinematica.mp4"], stdin=subprocess.PIPE)

xx = np.arange(LW, dtype=np.float32)[None, :]; yy = np.arange(LH, dtype=np.float32)[:, None]
for f in range(int(DUR * FPS)):
    t = f / FPS
    img, head, hot = build(t)

    # destello final: bloom y reflejo de luz que recorre el logo terminado
    sweep_u = (t - 6.1) / 0.9
    if 0 < sweep_u < 1:
        c = -400 + (LW + LH * 0.5 + 800) * smooth(sweep_u)
        band = np.exp(-(((xx + yy * 0.5) - c) / 110) ** 2)[..., None]
        img[..., :3] = np.minimum(img[..., 3:4], img[..., :3] + band * 0.9 * img[..., 3:4])
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBa")
    glow_amt = 0.35 + 0.5 * math.exp(-((t - 6.0) / 0.25) ** 2)
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
