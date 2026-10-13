"""ALFIO LORA: el logo se construye solo con planos de cámara (10 s, 1920x1080, fondo negro).

- La onda entra como una serpiente a velocidad constante siguiendo su propio recorrido.
- El recorrido de construcción se calcula por dentro de cada forma (esqueleto + propagación
  geodésica dentro de la máscara), así el frente avanza limpio sin saltar entre tramos vecinos.
- El monograma se traza solo; las letras se trazan mientras caen desde la cámara y se estampan.
- Luz que gira y saca brillos en los biseles, reflejos, destellos anamórficos.
- Final: corte a negro y el logo irrumpe con la cámara saliendo hacia atrás, destello, onda de luz y sacudida.

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
owner = np.where(alpha > 0.004, lab[iy, ix], 0)

def construction_param(rid, start_key):
    """Parámetro 0..1 de construcción: distancia geodésica por el esqueleto, propagada por dentro de la forma."""
    m = owner == rid
    sl = ndimage.find_objects(m.astype(np.int8))[0]
    sl = (slice(max(0, sl[0].start - 2), sl[0].stop + 2), slice(max(0, sl[1].start - 2), sl[1].stop + 2))
    mm = m[sl]
    sk = skeletonize(mm & (alpha[sl] > 0.5))
    skl, _ = ndimage.label(sk, structure=np.ones((3, 3)))
    sk = skl == (np.bincount(skl.ravel())[1:].argmax() + 1)          # solo el trazo principal
    pts = np.argwhere(sk)
    key = {"izq": pts[:, 1], "abajo_izq": pts[:, 1] - pts[:, 0], "abajo": -pts[:, 0], "arriba_izq": pts[:, 1] + 0.5 * pts[:, 0]}[start_key]
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
    # propagación por dentro de la máscara: cada píxel toma el valor del esqueleto de SU tramo
    P = np.where(dist >= 0, dist, -1.0)
    known = dist >= 0
    for _ in range(200):
        Pd = ndimage.grey_dilation(np.where(known, P, -1.0), size=3)
        new = mm & ~known & (Pd >= 0)
        if not new.any(): break
        P[new] = Pd[new]; known |= new
    P = np.where(known, P / max(1.0, dist.max()), 0.0)
    out = np.full(alpha.shape, 2.0, np.float32)
    out[sl] = np.where(mm, P, 2.0)
    return out

param = np.full(alpha.shape, 2.0, np.float32)
for name, start in (("onda", "izq"), ("mono", None), ("texto", "arriba_izq")):
    for j, rid in enumerate(regions[name]):
        p = construction_param(rid, start or ("abajo_izq" if j == 0 else "abajo"))
        param = np.where(owner == rid, p, param)

# piezas de texto: recortes propios para poder caer y aplastarse
letters = []
for rid in regions["texto"]:
    m = owner == rid
    yy_, xx_ = np.nonzero(m)
    r0, r1, c0, c1 = yy_.min(), yy_.max() + 1, xx_.min(), xx_.max() + 1
    letters.append({"rid": rid, "sl": (slice(r0, r1), slice(c0, c1)), "cx": (c0 + c1) / 2, "cy": (r0 + r1) / 2,
                    "rgba": np.where(m[r0:r1, c0:c1, None], premul[r0:r1, c0:c1], 0), "par": param[r0:r1, c0:c1]})
text_mask = np.isin(owner, regions["texto"])

# normales del bisel para los brillos del metal
ab = ndimage.gaussian_filter(alpha, 5)
gy, gx = np.gradient(ab)
gmag = np.hypot(gx, gy) + 1e-6
nx_, ny_ = -gx / gmag, -gy / gmag
edge = np.clip(gmag * 14, 0, 1) * alpha

# ---------------------------------------------------------------- guion temporal
smooth = lambda u: (lambda v: v * v * (3 - 2 * v))(min(1.0, max(0.0, u)))
ease_out = lambda u: 1 - (1 - min(1.0, max(0.0, u))) ** 3
lerp = lambda a, b, u: a + (b - a) * u

SNAKE0, SNAKE1 = 0.2, 3.6
def snake_head(t):
    """Velocidad constante a lo largo del recorrido."""
    return min(1.0, max(0.0, (t - SNAKE0) / (SNAKE1 - SNAKE0)))

MONO = {regions["mono"][0]: (3.6, 1.0)}
if len(regions["mono"]) > 1: MONO[regions["mono"][1]] = (4.0, 0.9)
LT0, LSTEP, FALL, TRACE_D, S0 = 5.1, 0.27, 0.32, 0.42, 3.0
for i, L_ in enumerate(letters): L_["t0"] = LT0 + i * LSTEP; L_["ti"] = L_["t0"] + FALL
IMPACTS = [L_["ti"] for L_ in letters]
DIP0, SLAM = 7.25, 7.45

def squash(d):
    """Aplastamiento elástico tras el impacto (muelle amortiguado, solución cerrada)."""
    if d < 0: return 0.0
    w = 26.0; z = 0.22
    return 0.28 * math.exp(-z * w * d) * math.cos(w * math.sqrt(1 - z * z) * d)

def paste(cv, rgba, cx, cy, sx, sy):
    h, w = rgba.shape[:2]
    img = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBa")
    nw, nh = max(1, round(w * sx)), max(1, round(h * sy))
    arr = np.asarray(img.resize((nw, nh), Image.BILINEAR)).astype(np.float32) / 255
    px, py = round(cx - nw / 2), round(cy - nh / 2)
    sx0, sy0, dx0, dy0 = max(0, -px), max(0, -py), max(0, px), max(0, py)
    hh, ww = min(nh - sy0, cv.shape[0] - dy0), min(nw - sx0, cv.shape[1] - dx0)
    if hh <= 0 or ww <= 0: return
    s_ = arr[sy0:sy0 + hh, sx0:sx0 + ww]; d_ = cv[dy0:dy0 + hh, dx0:dx0 + ww]
    d_[:] = s_ + d_ * (1 - s_[..., 3:4])

def light_dir(t):
    a = 0.9 * t + 0.6
    return math.cos(a), math.sin(a)

def build(t):
    """Logo en construcción (premultiplicado, coordenadas del logo) + datos para cámara y luces."""
    vis = np.zeros(alpha.shape, np.float32); hot = np.zeros(alpha.shape, np.float32)
    on = owner == 1
    h = snake_head(t)
    vis = np.where(on, np.clip((h - param) / 0.004 + 0.5, 0, 1), vis)
    fade_hot = 1 - smooth((t - SNAKE1 + 0.1) / 0.3)
    hot = np.where(on, np.exp(-((param - h) / 0.012) ** 2) * (param <= h + 0.004) * fade_hot, hot)
    for rid, (t0, d) in MONO.items():
        u = (t - t0) / d
        if u <= 0: continue
        hh = ease_out(u) * 1.02; m = owner == rid
        vis = np.where(m, np.clip((hh - param) / 0.015 + 0.5, 0, 1), vis)
        hot = np.where(m, np.exp(-((param - hh) / 0.035) ** 2) * (1 - smooth((u - 0.9) / 0.3)), hot)
    vis = np.where(text_mask, 0, vis)
    img = premul * vis[..., None]

    # metal: la luz gira y saca brillos en los biseles; más fuerte tras el impacto final
    lx, ly = light_dir(t)
    spec = np.clip(nx_ * lx + ny_ * ly, 0, 1) ** 6 * edge
    k = 0.55 + 0.6 * smooth((t - SLAM) / 0.3)
    add = (spec * k + hot) * alpha * vis
    img[..., :3] = np.minimum(img[..., 3:4], img[..., :3] + add[..., None] * np.array([0.95, 1.0, 1.0], np.float32))

    # letras: se trazan mientras caen desde la cámara y se estampan con rebote
    for L_ in letters:
        if t < L_["t0"]: continue
        uf = (t - L_["t0"]) / FALL
        tr = ease_out((t - L_["t0"]) / TRACE_D) * 1.02
        v = np.clip((tr - L_["par"]) / 0.03 + 0.5, 0, 1)
        rgba = L_["rgba"] * v[..., None]
        if t < L_["ti"]:
            s = 1 + (S0 - 1) * (1 - uf * uf); sx = sy = s; rgba = rgba * min(1.0, uf * 3)
        else:
            a = squash(t - L_["ti"]); sx, sy = 1 + 0.6 * a, 1 - a
        sl = L_["sl"]
        sp = spec[sl] * k * rgba[..., 3]
        rgba = rgba.copy(); rgba[..., :3] = np.minimum(rgba[..., 3:4], rgba[..., :3] + sp[..., None])
        paste(img, rgba, L_["cx"], L_["cy"], sx, sy)

    band = on & (np.abs(param - h) < 0.006)
    hy, hx = (np.argwhere(band).mean(0) if band.any() else (LH * 0.85, LW * 0.1))
    return img, (hx, hy)

# ---------------------------------------------------------------- cámara 3D
BASE = 1500 / LW

def homography(cx, cy, zoom, yaw=0.0, pitch=0.0, roll=0.0):
    D = 3000.0; f = D * BASE * zoom
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    R = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) \
        @ np.array([[cyw, 0, syw], [0, 1, 0], [-syw, 0, cyw]])
    tvec = R @ np.array([-cx, -cy, 0.0]) + np.array([0, 0, D])
    K = np.array([[f, 0, OUT_W / 2], [0, f, OUT_H / 2], [0, 0, 1]])
    Hm = K @ np.column_stack([R[:, 0], R[:, 1], tvec])
    Hi = np.linalg.inv(Hm); Hi /= Hi[2, 2]
    return tuple(Hi.flatten()[:8]), Hm

def project(Hm, x, y):
    p = Hm @ np.array([x, y, 1.0]); return p[0] / p[2], p[1] / p[2]

cam_state = {"shot": None, "hx": 0.0, "hy": 0.0}
def follow(shot, hx, hy, k):
    if cam_state["shot"] != shot: cam_state.update(shot=shot, hx=hx, hy=hy)
    cam_state["hx"] += (hx - cam_state["hx"]) * k; cam_state["hy"] += (hy - cam_state["hy"]) * k
    return cam_state["hx"], cam_state["hy"]

lc = [L_["cx"] for L_ in letters]
NAME_Y = np.mean([L_["cy"] for L_ in letters])
CUTS = [1.4, 2.5, 3.6, 5.0, 5.85, 6.65]

def impact_shake(t):
    x = y = 0.0
    for i, ti in enumerate(IMPACTS):
        d = t - ti
        if 0 <= d < 0.5:
            a = 14 * math.exp(-9 * d); x += a * math.sin(95 * d + i); y += a * math.cos(80 * d + 2 * i)
    return x, y

def camera(t, head):
    hx, hy = head
    if t < 1.4:                                   # serpiente: primerísimo plano que la acompaña
        x, y = follow(1, hx, hy, 0.15); u = t / 1.4
        return (x + 80, y, lerp(2.7, 2.5, u), lerp(6, 3, u), -6, 0)
    if t < 2.5:                                   # contrapicado lateral
        x, y = follow(2, hx, hy, 0.18); u = (t - 1.4) / 1.1
        return (x + 60, y, lerp(2.2, 2.0, u), -14, 18, lerp(-4, -2, u))
    if t < 3.6:                                   # picado más abierto
        x, y = follow(3, hx, hy, 0.18); u = (t - 2.5) / 1.1
        return (x - 40, y - 60, lerp(1.9, 1.6, u), 10, -15, lerp(3, 1, u))
    if t < 5.0:                                   # monograma: dolly lento en contrapicado
        u = smooth((t - 3.6) / 1.4)
        return (lerp(LW * 0.27, LW * 0.33, u), LH * 0.40, lerp(1.75, 1.5, u), lerp(-8, 4, u), 20, lerp(-3, 2, u))
    sx, sy = impact_shake(t)
    if t < 5.85:                                  # letras 1: contrapicado por la izquierda
        u = smooth((t - 5.0) / 0.85)
        return (lerp(lc[0], lc[2], u) + sx, NAME_Y - 60 + sy, 2.25, 12, 16, -4)
    if t < 6.65:                                  # letras 2: picado por la derecha
        u = smooth((t - 5.85) / 0.8)
        return (lerp(lc[3], lc[min(5, len(lc) - 1)], u) + sx, NAME_Y - 40 + sy, 2.05, -12, -14, 4)
    if t < SLAM:                                  # letras 3: el nombre completo
        u = smooth((t - 6.65) / 0.6)
        return (LW * 0.5 + sx, NAME_Y - 120 + sy, lerp(1.5, 1.38, u), 0, 10, 0)
    d = t - SLAM                                  # impacto: la cámara sale disparada hacia atrás
    pull = 2.6 * math.exp(-d / 0.085)
    shake = 26 * math.exp(-6 * d)
    return (LW * 0.5 + shake * math.sin(70 * d), LH * 0.5 + shake * math.cos(83 * d),
            1.0 + pull + 0.06 * smooth((d - 0.5) / 2.0), 0, 0, 0.8 * math.exp(-6 * d) * math.sin(50 * d))

def whip(t):
    return max([math.exp(-((t - c) / 0.05) ** 2) for c in CUTS] + [0.0])

# ---------------------------------------------------------------- efectos de luz en pantalla
SX = np.arange(OUT_W, dtype=np.float32)[None, :]; SY = np.arange(OUT_H, dtype=np.float32)[:, None]
def streak(frame, x, y, amt, length=520, col=(0.75, 0.95, 1.0)):
    """Destello anamórfico horizontal."""
    if amt < 0.01: return
    s = np.exp(-((SY - y) / 4.0) ** 2) * np.exp(-np.abs(SX - x) / length) * amt * 255
    core = np.exp(-(((SY - y) / 18) ** 2 + ((SX - x) / 18) ** 2)) * amt * 255
    frame += (s + core)[..., None] * np.array(col, np.float32)

xx = np.arange(LW, dtype=np.float32)[None, :]; yy = np.arange(LH, dtype=np.float32)[:, None]

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", "alfio-lora-cinematica.mp4"], stdin=subprocess.PIPE)

for f in range(int(DUR * FPS)):
    t = f / FPS
    img, head = build(t)
    d = t - SLAM

    # reflejos que recorren el metal: uno fuerte tras el impacto y otro suave al final
    for t0, dur, amt in ((7.85, 0.8, 1.0), (9.0, 0.9, 0.55)):
        u = (t - t0) / dur
        if 0 < u < 1:
            c = -400 + (LW + LH * 0.5 + 800) * smooth(u)
            band = np.exp(-(((xx + yy * 0.5) - c) / 100) ** 2)[..., None]
            img[..., :3] = np.minimum(img[..., 3:4], img[..., :3] + band * amt * img[..., 3:4])
    # destello del impacto: el logo se quema a blanco y vuelve
    if d >= 0:
        fl = 0.95 * math.exp(-d / 0.16)
        img[..., :3] += (img[..., 3:4] - img[..., :3]) * fl
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBa")
    pulse = 0.1 * (0.5 + 0.5 * math.sin((t - 8.4) * 2 * math.pi / 1.2)) if t > 8.4 else 0.0
    glow_amt = 0.3 + (1.4 * math.exp(-d / 0.3) if d >= 0 else 0) + pulse
    glow = pil.resize((LW // 4, LH // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(9)).resize((LW, LH), Image.BILINEAR)

    w = whip(t)
    fast = (0 <= d < 0.3)
    offs = (-0.02, -0.01, 0.0, 0.01, 0.02) if (w > 0.05 or fast) else (0.0,)
    acc = np.zeros((OUT_H, OUT_W, 3), np.float32)
    for ofs in offs:
        cam = camera(t + ofs, head)
        co, Hm = homography(*cam)
        a = np.asarray(pil.transform((OUT_W, OUT_H), Image.PERSPECTIVE, co, Image.BICUBIC)).astype(np.float32)[..., :3]
        g = np.asarray(glow.transform((OUT_W, OUT_H), Image.PERSPECTIVE, co, Image.BILINEAR)).astype(np.float32)[..., :3]
        acc += np.minimum(255, a + g * glow_amt)
    frame = acc / len(offs)
    if w > 0.05:
        frame = ndimage.uniform_filter1d(frame, size=int(8 + 60 * w), axis=1)

    # destellos anamórficos: cabeza de la serpiente, impactos de letras y el golpe final
    _, Hm = homography(*camera(t, head))
    if t < SNAKE1:
        px, py = project(Hm, *head); streak(frame, px, py, 0.55)
    for L_ in letters:
        dd = t - L_["ti"]
        if 0 <= dd < 0.4:
            px, py = project(Hm, L_["cx"], L_["cy"]); streak(frame, px, py, 0.6 * math.exp(-dd / 0.12), 380)
    if d >= 0:
        cx_, cy_ = project(Hm, LW * 0.5, LH * 0.5)
        streak(frame, cx_, cy_, 1.6 * math.exp(-d / 0.35), 1400, (0.85, 1.0, 0.9))
        r = 2600 * (1 - math.exp(-d / 0.35))                     # onda expansiva de luz
        ring = np.exp(-((np.hypot(SX - cx_, (SY - cy_) * 1.15) - r) / 26) ** 2) * 255 * 0.7 * math.exp(-d / 0.45)
        frame += ring[..., None] * np.array([0.8, 1.0, 0.95], np.float32)

    # exposición: baja a negro antes del golpe
    if DIP0 <= t < SLAM:
        frame *= 1 - smooth((t - DIP0) / (SLAM - DIP0 - 0.05))
    proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    if f % 30 == 0: print("t", round(t, 1), flush=True)

proc.stdin.close(); proc.wait()
print("ok")
