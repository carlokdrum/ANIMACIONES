"""Logo de Ponte en Quatro llenándose de cerveza.

Un chorro cae desde la esquina superior derecha, las letras se llenan de cerveza
ámbar con burbujas, y al final la espuma rebosa y baja por las letras.
Fondo transparente (QuickTime Animation), el formato que lee CapCut en Mac.

Uso:  python3 llenado_cerveza.py [escala] [salida.mov] [logo.png]
      escala 1 = 4K (2160x3840) · 0.5 = 1080x1920 · 0.25 = prueba rápida
Requiere: pip install numpy pillow scipy  y  ffmpeg
"""
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

S = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
OUT = sys.argv[2] if len(sys.argv) > 2 else "logo-cerveza-4k.mov"
LOGO = sys.argv[3] if len(sys.argv) > 3 else "logo.png"

W, H = round(2160 * S), round(3840 * S)
FPS, DUR = 30, 7.0          # DUR es solo un tope; la duración real es T_END
f32 = np.float32


def smooth(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = np.clip(u, 0, 1)
    return 1 - (1 - u) ** 3


def snoise(shape, sigma, seed):
    """Ruido suave normalizado a 0..1."""
    r = np.random.default_rng(seed).standard_normal(shape).astype(f32)
    g = ndi.gaussian_filter(r, sigma, mode="wrap")
    g -= g.min()
    return g / g.max()


# ---------------------------------------------------------------- logo y lienzo
src = np.array(Image.open(LOGO).convert("RGBA"))
ys, xs = np.nonzero(src[..., 3] > 8)
crop = Image.fromarray(src[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
LW = round(1800 * S)
crop = crop.resize((LW, round(crop.height * LW / crop.width)), Image.LANCZOS)
a_logo = np.array(crop)[..., 3].astype(f32) / 255
lh, lw = a_logo.shape
PX, PY = round(150 * S), round(230 * S)          # margen del lienzo alrededor del logo
CH, CW = lh + 2 * PY, lw + 2 * PX
A = np.zeros((CH, CW), f32)
A[PY:PY + lh, PX:PX + lw] = a_logo
GROW = 3 * S                                     # engorda un poco las letras para cerrar los espacios entre ellas
if GROW > 0:
    rg = max(1, int(np.ceil(GROW)))
    gyy, gxx = np.mgrid[-rg:rg + 1, -rg:rg + 1]
    A = ndi.gaussian_filter(ndi.grey_dilation(A, footprint=(gxx * gxx + gyy * gyy) <= GROW * GROW), 0.6)
M = A > 0.5
cx0, cy0 = (W - CW) // 2, (H - CH) // 2            # origen del lienzo en el cuadro
Yc = np.arange(CH, dtype=f32)[:, None]
Xc = np.arange(CW, dtype=f32)

# --- relieve de vidrio: luz y brillo fijos (el logo no se mueve) ----------------
dist = ndi.distance_transform_edt(M).astype(f32)
hgt = ndi.gaussian_filter(smooth(dist / (24 * S)), 2.5 * S)
gy, gx = np.gradient(hgt)
k = 24 * S * 1.1
nx, ny = -gx * k, -gy * k
ln = np.sqrt(nx * nx + ny * ny + 1)
L = np.array([-0.45, -0.60, 0.66]); L /= np.linalg.norm(L)
Hv = L + np.array([0, 0, 1.0]); Hv /= np.linalg.norm(Hv)
diff = (nx * L[0] + ny * L[1] + L[2]) / ln
spec = np.clip((nx * Hv[0] + ny * Hv[1] + Hv[2]) / ln, 0, 1) ** 38

# cerveza: degradado ámbar, más oscura en los bordes, con vetas de luz y brillo
ty = np.clip((Yc - PY) / lh, 0, 1)
top_c, bot_c = np.array([222, 124, 30], f32), np.array([132, 48, 6], f32)   # ámbar cobrizo, tipo ale quadrupel
beer = top_c[None, None, :] * (1 - ty)[..., None] + bot_c[None, None, :] * ty[..., None]
beer = np.repeat(beer, CW, axis=1)
streak = 1 + 0.16 * (snoise((1, CW), 55 * S, 3) - 0.5)
beer = beer * (0.80 + 0.20 * hgt)[..., None] * (0.84 + 0.30 * diff)[..., None] * streak[..., None]
# brillo del líquido: reflejos diagonales anchos y un resplandor cálido en el centro de cada trazo
sheen = np.exp(-(((Xc[None, :] * 0.8 + Yc * 0.6) % (430 * S) - 150 * S) / (38 * S)) ** 2) * hgt
beer = beer + np.array([255, 214, 150], f32)[None, None, :] * (0.20 * sheen + 0.10 * hgt ** 2)[..., None]
beer = np.clip(beer + 255 * 0.95 * spec[..., None], 0, 255).astype(f32)

# espuma: crema con textura de burbujitas
def cells(spacing, seed):
    """Textura de burbujas: 0 en el borde de cada burbuja, 1 en su centro."""
    r = np.random.default_rng(seed)
    n = int(CH * CW / (spacing * spacing))
    seeds = np.ones((CH, CW), bool)
    seeds[r.integers(0, CH, n), r.integers(0, CW, n)] = False
    d = ndi.distance_transform_edt(seeds).astype(f32)
    return 1 - smooth(d / (0.62 * spacing))


ftex = (0.935 + 0.065 * cells(max(3.0, 8 * S), 11)) * (0.95 + 0.05 * cells(max(6.0, 24 * S), 12)) \
    * (0.98 + 0.02 * snoise((CH, CW), 30 * S, 13))
CREAM = np.array([252, 240, 214], f32)
CREAM_LOW = np.array([236, 200, 146], f32)
CREAM_SH = np.array([226, 204, 166], f32)          # sombra cálida de la espuma
plume_tex = snoise((CH, CW), 5 * S, 21)

# contorno de vidrio (anillo fino por dentro del borde)
r_o = max(1, round(4 * S))
yy, xx = np.mgrid[-r_o:r_o + 1, -r_o:r_o + 1]
outline = np.clip(A - ndi.grey_erosion(A, footprint=(xx * xx + yy * yy) <= r_o * r_o), 0, 1)

# --- geometría de los bordes superiores (para la espuma que rebosa) -------------
rows = np.arange(CH)[:, None] * np.ones((1, CW), int)
cs = np.cumsum(M, axis=0)
BIG = 10 ** 6
nxt = np.minimum.accumulate(np.where(M, rows, BIG)[::-1], axis=0)[::-1]     # primera fila de logo hacia abajo
d_below = (nxt - rows).astype(f32)                                           # fuera del logo: distancia hasta él
sky = cs == 0                                                                # nada de logo por encima
last_out = np.maximum.accumulate(np.where(~M, rows, -1), axis=0)
depth_in = (rows - last_out).astype(f32)                                     # dentro: profundidad desde su borde superior
cs_top = np.take_along_axis(cs, np.clip(last_out, 0, CH - 1), axis=0)
sky_in = M & (cs_top == 0)
cap_noise = 0.45 + 1.0 * snoise((1, CW), 22 * S, 5)                          # altura irregular de la espuma
CAP_H = 30 * S
OVERFLOW = False                                 # True: la espuma rebosa y baja por las letras
FOAM_TOP = 78 * S * (0.75 + 0.5 * snoise((1, CW), 40 * S, 6))   # corona de espuma en lo alto de cada letra
foam_top = np.where(sky_in, np.clip((FOAM_TOP - depth_in) / (3 * S) + 0.5, 0, 1), 0).astype(f32)

# --- tiempos y nivel del líquido -------------------------------------------------
T_STREAM = 0.25          # empieza a caer el chorro
T_FILL0, T_RISE = 0.62, 2.0
T_STOP = 2.5            # se corta el chorro
THICK = 115 * S          # espesor final de la capa de espuma
DT = 1 / 240
LV0 = -0.02                      # el nivel arranca por debajo del fondo: nada de líquido hasta que llega el chorro
level, vel, levels = LV0, 0.0, []
for i in range(int(DUR / DT) + 2):
    t = i * DT
    u = min(1.0, max(0.0, (t - T_FILL0) / T_RISE))
    target = LV0 + u * u * (3 - 2 * u) * ((1.05 if OVERFLOW else 1.012) - LV0)
    vel += (-120 * (level - target) - 15 * vel) * DT
    level += vel * DT
    levels.append(level)
levels = np.array(levels)
T_OV = float(np.argmax(levels >= 0.995) * DT)        # la espuma llega arriba y empieza a rebosar


T_HIT, T_DRAIN = 1e9, 0.75         # T_HIT se calcula más abajo; T_DRAIN = lo que tarda en vaciarse


def drain_u(t):
    """0 antes de que caiga la gota, 1 cuando el logo ya está vacío."""
    return min(1.0, max(0.0, (t - T_HIT) / T_DRAIN))


def lv_at(t):
    lv = levels[min(len(levels) - 1, int(round(min(t, T_HIT) / DT)))]
    u = drain_u(t)
    return lv * (1 - u ** 1.7) - 0.03 * u            # se vacía acelerando, hasta pasar el fondo


def thick_at(t):
    return THICK * smooth((t - T_FILL0) / 1.3) * (1 - 0.75 * drain_u(t))


# --- punto donde cae el chorro: columna con más logo en la mitad derecha --------
cov = ndi.uniform_filter1d(M.mean(axis=0).astype(f32), max(3, round(50 * S)))
lo, hi = round(CW * 0.66), round(CW * 0.84)
XL = lo + int(np.argmax(cov[lo:hi]))
# dentro del logo el chorro va DETRÁS del vidrio: solo se ve en el interior de las letras,
# con el contorno de cada letra por delante y un poco atenuado por el cristal
r_g = max(1, round(9 * S))
gy2, gx2 = np.mgrid[-r_g:r_g + 1, -r_g:r_g + 1]
A_GLASS = ndi.gaussian_filter(ndi.grey_erosion(A, footprint=(gx2 * gx2 + gy2 * gy2) <= r_g * r_g), 1.2 * S) * 0.9
SKYA = np.where(cs == 0, 1.0, A_GLASS).astype(f32)
_w = int(80 * S)
_cols = [x for x in range(XL - _w, XL + _w) if M[:, x].any()]
Y_IN = cy0 + max(int(np.argmax(M[:, x])) for x in _cols) + 10 * S   # el chorro siempre llega hasta tocar la letra
XE = cx0 + XL                                           # x del chorro al entrar al logo
B_STR, LAM = 330 * S, 420 * S                     # arco del chorro


# --- final: una última gota cae y, al tocar las letras, el logo desaparece --------
T_DROP0 = 3.25                                            # sale la gota
G_DROP = 9500 * S
T_HIT = T_DROP0 + float(np.sqrt(2 * (Y_IN - 10 * S + 60 * S) / G_DROP))   # toca la letra
T_EMPTY = T_HIT + T_DRAIN                                # el líquido llega al fondo
T_END = T_EMPTY + 0.7
HIT_X, HIT_Y = float(XL), float(Y_IN - 10 * S - cy0)
DHIT = np.hypot(Xc[None, :] - HIT_X, Yc - HIT_Y).astype(f32)
R_MAX = float(DHIT[M].max()) + 90 * S


print("gota toca en t =", round(T_HIT, 2), "| termina en t =", round(T_END, 2), flush=True)


def inside(r0, r1, c0, c1, y_free=None):
    """Recorte del chorro: se ve completo en el aire, por encima del logo, y una vez
    entra solo se ve dentro de las letras."""
    m = np.ones((r1 - r0, c1 - c0), f32)
    a0, a1 = max(r0, cy0), min(r1, cy0 + CH)
    b0, b1 = max(c0, cx0), min(c1, cx0 + CW)
    if a1 > a0 and b1 > b0:
        m[a0 - r0:a1 - r0, b0 - c0:b1 - c0] = SKYA[a0 - cy0:a1 - cy0, b0 - cx0:b1 - cx0]
    return m


def stream_x(y):
    return XE + B_STR * np.exp(-np.maximum(y, -300 * S) / LAM)


edge_c0, mid_c0 = np.array([108, 38, 4], f32), np.array([214, 116, 26], f32)   # ámbar de la gota
stex = snoise((1024, 64), (14, 4), 31)                    # vetas de espuma del chorro
srng = np.random.default_rng(99)
N_SPL = 34                                               # salpicaduras
spl_ang = srng.uniform(-1.15, 1.15, N_SPL)
spl_v = srng.uniform(520, 1250, N_SPL) * S
spl_r = srng.uniform(5, 15, N_SPL) * S
spl_ph = srng.uniform(0, 1, N_SPL)
spl_per = srng.uniform(0.38, 0.62, N_SPL)

# --- burbujas ---------------------------------------------------------------------
rng = np.random.default_rng(7)
cand = np.argwhere(dist > 7 * S)
n_small, n_big = 260, 40
pick = cand[rng.choice(len(cand), n_small + n_big, replace=False)]
site_y, site_x = pick[:, 0].astype(f32), pick[:, 1].astype(f32)
site_r = np.r_[rng.uniform(2.2, 5.5, n_small), rng.uniform(8, 15, n_big)] * S
site_v = np.r_[rng.uniform(300, 540, n_small), rng.uniform(190, 320, n_big)] * S
site_p = np.r_[rng.uniform(0.10, 0.30, n_small), rng.uniform(0.7, 1.9, n_big)]
site_ph = rng.uniform(0, 2, n_small + n_big)
site_wob = rng.uniform(2, 9, n_small + n_big) * S
# momento en que la cerveza cubre cada punto
tt = np.arange(0, DUR, 1 / 60)
beer_top_t = np.array([PY + lh * (1 - lv_at(t)) + thick_at(t) for t in tt])
site_act = np.array([tt[np.argmax(beer_top_t < y - 12 * S)] if (beer_top_t < y - 12 * S).any() else 99 for y in site_y])


def stamp(layer, x, y, r):
    rr = int(r + 2)
    x0, y0 = int(round(x)) - rr, int(round(y)) - rr
    if x0 < 0 or y0 < 0 or x0 + 2 * rr + 1 > CW or y0 + 2 * rr + 1 > CH:
        return
    gy_, gx_ = np.mgrid[0:2 * rr + 1, 0:2 * rr + 1]
    dx, dy = gx_ + x0 - x, gy_ + y0 - y
    d = np.hypot(dx, dy)
    disc = np.clip(r - d + 0.5, 0, 1)
    if r < 6 * S:
        val = disc * 0.8
    else:  # burbuja grande: aro con un puntito de brillo
        val = disc * (0.22 + 0.7 * smooth((d - 0.5 * r) / (0.5 * r)))
        val = np.maximum(val, np.clip(0.28 * r - np.hypot(dx + 0.36 * r, dy + 0.36 * r) + 0.5, 0, 1))
    sl = layer[y0:y0 + 2 * rr + 1, x0:x0 + 2 * rr + 1]
    np.maximum(sl, val, out=sl)


# --- gotas de espuma que bajan por las letras ------------------------------------
col_has = M.any(axis=0)
ytop = np.argmax(M, axis=0)
drips = []
order = rng.permutation(np.nonzero(col_has)[0])
min_gap = 150 * S
for x in order:
    if len(drips) >= 10:
        break
    if x < PX + 20 * S or x > CW - PX - 20 * S:
        continue
    if any(abs(x - d["x"]) < min_gap for d in drips):
        continue
    y0 = int(ytop[x])
    hw_chk = int(30 * S)
    if not M[min(CH - 1, y0 + int(30 * S)), max(0, x - hw_chk):x + hw_chk].all():
        continue                                    # que nazca sobre un trazo ancho, no en una punta
    Lmax = rng.uniform(220, 820) * S
    Lr = 0
    for Ltry in np.arange(Lmax, 120 * S, -20 * S):  # que termine sobre una letra y casi todo el camino también
        y1 = int(y0 + Ltry)
        if y1 < CH and M[y1, x] and M[y0:y1, x].mean() > 0.9:
            Lr = Ltry
            break
    if Lr == 0:
        continue
    drips.append(dict(x=float(x), y0=float(y0), L=float(Lr), w=rng.uniform(52, 98) * S,
                      t0=T_OV + rng.uniform(0.05, 1.1), d=rng.uniform(1.3, 2.3), ph=rng.uniform(0, 6.28)))
# copos de espuma sobre los bordes superiores: le dan a la espuma su forma abultada
blobs = []
xs_ = np.nonzero(col_has)[0]
i = int(xs_.min())
while i < xs_.max():
    if col_has[i]:
        r_ = rng.uniform(30, 66) * S
        blobs.append((float(i), float(ytop[i]) - 0.22 * r_, r_, rng.uniform(0, 0.55)))
    i += max(1, int(rng.uniform(20, 46) * S))




def over(C, Al, col, la):
    """Compone una capa (color, alfa) encima de C/Al premultiplicado."""
    C *= (1 - la)[..., None]
    C += col * la[..., None]
    Al *= (1 - la)
    Al += la


def render(t):
    lv = lv_at(t)
    thick = thick_at(t)
    pour = T_FILL0 - 0.05 < t < T_STOP + 0.25
    calm = (1 - 0.85 * smooth((lv - 0.88) / 0.15)) * (1 - 0.5 * drain_u(t))
    amp = 24 * S * calm * float(smooth((lv + 0.005) / 0.05))        # sin olas mientras no hay líquido
    yf = (PY + lh * (1 - lv) + amp * np.sin(2 * np.pi * Xc / (420 * S) + 7.5 * t)
          + 0.45 * amp * np.sin(2 * np.pi * Xc / (170 * S) - 11 * t)
          + 0.03 * np.sin(2 * np.pi * 1.5 * t) * calm * (Xc - CW / 2))
    if pour:
        yf = yf + 26 * S * calm * np.exp(-((Xc - XL) / (130 * S)) ** 2) * np.sin(19 * t)
    yb = yf + thick * (1 + 0.16 * np.sin(Xc / (120 * S) + 2.1 * t) + 0.09 * np.sin(Xc / (43 * S) - 3.0 * t))
    fill_all = np.clip(Yc - yf[None, :] + 1, 0, 1) * A
    fill_beer = np.clip(Yc - yb[None, :] + 1, 0, 1) * A
    foam_in = np.maximum(fill_all - fill_beer, foam_top * fill_all * (1 - drain_u(t)))
    fill_beer = fill_all - foam_in

    oa = float(ease_out(t / 0.4)) * (1.0 if t < T_EMPTY - 1e-6 else 0.0)      # al vaciarse, las letras desaparecen de golpe
    Al = 0.10 * A * oa
    C = 255.0 * Al[..., None] * np.ones(3, f32)

    over(C, Al, beer, fill_beer * 0.97)

    # burbujas subiendo
    bub = np.zeros((CH, CW), f32)
    for i in range(len(site_x)):
        if t < site_act[i]:
            continue
        p, v = site_p[i], site_v[i]
        j1 = int(np.floor((t - site_ph[i]) / p))
        j0 = max(int(np.ceil((site_act[i] - site_ph[i]) / p)), j1 - 40)
        for j in range(j0, j1 + 1):
            age = t - (site_ph[i] + j * p)
            y = site_y[i] - v * age * (1 + 0.25 * age)
            x = site_x[i] + site_wob[i] * np.sin(5.5 * age + j * 1.7)
            xi = int(round(x))
            if y < PY or xi < 1 or xi >= CW - 1 or y < yb[xi] + 2 * S:
                continue
            stamp(bub, x, y, site_r[i] * (0.8 + 0.35 * min(1.0, age)))
    over(C, Al, np.array([255, 222, 156], f32), bub * fill_beer * 0.85)

    # nube de espuma bajo el chorro
    if pour:
        dyp = Yc - yb[XL]
        sh = int(520 * S * t) % CH
        pl = (0.8 * np.exp(-((Xc[None, :] - XL) / (105 * S)) ** 2) * np.exp(-np.maximum(dyp, 0) / (230 * S))
              * (0.45 + 0.55 * np.roll(plume_tex, sh, axis=0)) * fill_beer)
        pl *= smooth((t - T_FILL0 + 0.05) / 0.2) * (1 - smooth((t - T_STOP) / 0.25))
        over(C, Al, np.array([250, 228, 176], f32), pl)

    # espuma dentro de las letras
    if thick > 0.5:
        dn = np.clip((Yc - yf[None, :]) / np.maximum(yb - yf, 1)[None, :], 0, 1) ** 2 * 0.75
        dn = np.where(foam_top > 0, np.minimum(dn, np.clip(depth_in / FOAM_TOP, 0, 1) ** 2 * 0.75), dn)
        fcol = (CREAM[None, None, :] * (1 - dn)[..., None] + CREAM_LOW[None, None, :] * dn[..., None]) * ftex[..., None]
        over(C, Al, fcol, foam_in)

    over(C, Al, np.array([255, 255, 255], f32), outline * 0.8 * oa * (1 - 0.85 * np.clip(fill_beer / np.maximum(A, 1e-3), 0, 1)))

    # espuma que rebosa y baja por las letras
    if OVERFLOW and t > T_OV:
        g = float(ease_out((t - T_OV) / 1.0))
        capn = CAP_H * g * cap_noise
        fo = np.where(sky & (nxt < BIG), np.clip((capn - d_below) / (3 * S) + 0.5, 0, 1), 0).astype(f32)
        fo = np.maximum(fo, np.where(sky_in, np.clip((22 * S * g - depth_in) / (3 * S) + 0.5, 0, 1), 0))
        for bx, by, br, bd in blobs:
            rr = br * float(ease_out((t - T_OV - bd) / 0.9))
            if rr < 1:
                continue
            q = int(rr + 3)
            r0, r1, c0, c1 = max(0, int(by) - q), min(CH, int(by) + q + 1), max(0, int(bx) - q), min(CW, int(bx) + q + 1)
            yy_ = np.arange(r0, r1, dtype=f32)[:, None]
            xx_ = np.arange(c0, c1, dtype=f32)[None, :]
            sl = fo[r0:r1, c0:c1]
            np.maximum(sl, np.clip((rr - np.hypot(xx_ - bx, yy_ - by)) / (3 * S) + 0.5, 0, 1), out=sl)
        for d in drips:
            a = t - d["t0"]
            if a <= 0:
                continue
            grow = float(smooth(a / 0.3))
            head = d["y0"] - 8 * S + d["L"] * float(ease_out(a / d["d"])) + 9 * S * a
            rh = d["w"] * 0.56 * grow
            r0, r1 = int(d["y0"] - 12 * S), int(min(CH - 1, head + rh + 2))
            c0, c1 = int(max(0, d["x"] - d["w"] * 1.5)), int(min(CW, d["x"] + d["w"] * 1.5))
            if r1 <= r0:
                continue
            yy_ = np.arange(r0, r1, dtype=f32)[:, None]
            xx_ = np.arange(c0, c1, dtype=f32)[None, :]
            xc = d["x"] + 5 * S * np.sin(yy_ / (95 * S) + d["ph"])
            along = np.clip((yy_ - d["y0"]) / max(head - d["y0"], 1), 0, 1)      # 0 arriba, 1 en la punta
            rad = d["w"] / 2 * grow * (1.2 - 0.5 * along) * (1 + 0.20 * np.sin(yy_ / (85 * S) + d["ph"] * 2) + 0.11 * np.sin(yy_ / (37 * S) + d["ph"] * 5))
            body = np.clip(rad - np.abs(xx_ - xc) + 0.5, 0, 1) * (yy_ <= head)
            hx = d["x"] + 5 * S * np.sin(head / (95 * S) + d["ph"])
            bulb = np.clip(rh - np.hypot(xx_ - hx, yy_ - (head - rh * 0.15)) + 0.5, 0, 1)
            sl = fo[r0:r1, c0:c1]
            np.maximum(sl, np.maximum(body, bulb), out=sl)
        rmax = int(min(CH, np.nonzero(fo.any(axis=1))[0].max() + 60 * S)) if fo.any() else 0
        if rmax:
            fo = fo[:rmax]
            ao = smooth((ndi.gaussian_filter(fo, 4.5 * S) - 0.30) / 0.36)
            hh = ndi.gaussian_filter(ao, 13 * S)
            hy, hx_ = np.gradient(hh)
            kk = 44 * S
            lit = np.clip((-hx_ * kk * L[0] - hy * kk * L[1] + L[2]) / np.sqrt((hx_ * kk) ** 2 + (hy * kk) ** 2 + 1), 0, 1.2)
            shade = smooth((lit - 0.18) / 0.42)
            ocol = (CREAM_SH[None, None, :] + (CREAM - CREAM_SH)[None, None, :] * shade[..., None]) * (0.045 + ftex[:rmax])[..., None]
            ocol = np.minimum(ocol, 255)
            # sombra suave sobre la cerveza
            shd = ndi.gaussian_filter(np.roll(np.roll(ao, int(9 * S), axis=0), int(4 * S), axis=1), 7 * S) * 0.42
            C[:rmax] *= (1 - shd * (1 - ao))[..., None]
            over(C[:rmax], Al[:rmax], ocol, ao)

    # ---- cuadro completo: lienzo + chorro ----
    frame = np.zeros((H, W, 4), f32)
    frame[cy0:cy0 + CH, cx0:cx0 + CW, :3] = C
    frame[cy0:cy0 + CH, cx0:cx0 + CW, 3] = Al

    if t > T_STREAM:
        gfall = 30000 * S
        head_y = -60 * S + 0.5 * gfall * (t - T_STREAM) ** 2
        y_end = min(head_y, max(cy0 + yf[XL] + 4 * S, Y_IN))
        tail_y = -200 * S if t < T_STOP else -200 * S + 0.5 * 26000 * S * (t - T_STOP) ** 2
        r0, r1 = int(max(0, tail_y)), int(min(H, y_end))
        if r1 > r0:
            yy_ = np.arange(r0, r1, dtype=f32)[:, None]
            xc = stream_x(yy_) + 5 * S * np.sin(yy_ / (210 * S) - 7 * t)
            hw = (78 - 30 * np.clip(yy_ / (1700 * S), 0, 1)) * S
            hw = hw * (1 + 0.22 * np.sin(yy_ / (190 * S) - 8 * t) + 0.11 * np.sin(yy_ / (71 * S) - 13 * t + 1))
            if t >= T_STOP:
                hw = hw * (0.2 + 0.8 * smooth((yy_ - tail_y) / (520 * S)))
            if head_y < cy0 + yf[XL]:
                hw = hw * (0.6 + 0.6 * np.sqrt(smooth((head_y - yy_) / (90 * S)))) * smooth((head_y - yy_) / (14 * S) + 0.3)
            c0, c1 = int(max(0, XE - 160 * S)), W
            xx_ = np.arange(c0, c1, dtype=f32)[None, :]
            u = (xx_ - xc) / np.maximum(hw, 0.5)
            sa = np.clip(hw - np.abs(xx_ - xc) + 0.5, 0, 1) * 0.96 * inside(r0, r1, c0, c1, Y_IN)
            prof = np.sqrt(np.clip(1 - u * u, 0, 1)) ** 1.2
            flow = 1 + 0.07 * np.sin(yy_ / (60 * S) - 20 * t)
            edge_c, mid_c = np.array([108, 38, 4], f32), np.array([214, 116, 26], f32)
            scol = (edge_c[None, None, :] + (mid_c - edge_c)[None, None, :] * prof[..., None]) * flow[..., None]
            u0 = -0.36 + 0.13 * np.sin(yy_ / (170 * S) - 10 * t)
            hl = 0.88 * np.exp(-((u - u0) / 0.11) ** 2) + 0.36 * np.exp(-((u - 0.52) / 0.09) ** 2)
            scol = np.clip(scol + 255 * hl[..., None], 0, 255)
            # vetas de espuma que bajan con el chorro, más densas cerca del impacto
            ri = ((yy_ / S * 0.30 - 1100 * t) % 1024).astype(int)
            ci = np.clip((u * 0.5 + 0.5) * 63, 0, 63).astype(int)
            near = np.clip(1 - (y_end - yy_) / (330 * S), 0, 1)
            fm = smooth((stex[ri, ci] - (0.60 - 0.22 * near)) / 0.14) * (0.62 + 0.3 * near)
            scol = scol * (1 - fm)[..., None] + np.array([255, 245, 216], f32)[None, None, :] * fm[..., None]
            reg = frame[r0:r1, c0:c1]
            reg[..., :3] = reg[..., :3] * (1 - sa)[..., None] + scol * sa[..., None]
            reg[..., 3] = reg[..., 3] * (1 - sa) + sa

        # espuma y salpicaduras donde el chorro golpea
        if pour and head_y >= cy0 + yf[XL]:
            k_on = float(smooth((t - T_FILL0 + 0.05) / 0.15) * (1 - smooth((t - T_STOP - 0.05) / 0.25)))
            ix, iy = float(stream_x(y_end)), float(y_end)
            rx, ry = 120 * S, 52 * S
            r0, r1 = int(max(0, iy - 2 * ry)), int(min(H, iy + 2 * ry))
            c0, c1 = int(max(0, ix - 2 * rx)), int(min(W, ix + 2 * rx))
            yy_ = np.arange(r0, r1, dtype=f32)[:, None]
            xx_ = np.arange(c0, c1, dtype=f32)[None, :]
            ang = np.arctan2(yy_ - iy, xx_ - ix)
            wob = 1 + 0.22 * np.sin(5 * ang + 23 * t) + 0.14 * np.sin(9 * ang - 31 * t)
            dd = np.hypot((xx_ - ix) / rx, (yy_ - iy) / ry) / wob
            fa = smooth((1 - dd) / 0.35) * 0.95 * k_on * inside(r0, r1, c0, c1, Y_IN)
            reg = frame[r0:r1, c0:c1]
            fc = np.array([255, 247, 226], f32) * (0.9 + 0.1 * np.clip(1 - dd, 0, 1))[..., None]
            reg[..., :3] = reg[..., :3] * (1 - fa)[..., None] + fc * fa[..., None]
            reg[..., 3] = reg[..., 3] * (1 - fa) + fa
            for i in range(N_SPL):
                age = ((t / spl_per[i]) + spl_ph[i]) % 1.0 * spl_per[i]
                px = ix + np.sin(spl_ang[i]) * spl_v[i] * age
                py = iy - np.cos(spl_ang[i]) * spl_v[i] * age + 0.5 * 3600 * S * age * age
                rr = spl_r[i] * (1 - 0.5 * age / spl_per[i])
                aa = k_on * (1 - age / spl_per[i]) ** 0.6
                q = int(rr + 2)
                x0_, y0_ = int(px) - q, int(py) - q
                if x0_ < 0 or y0_ < 0 or x0_ + 2 * q + 1 > W or y0_ + 2 * q + 1 > H:
                    continue
                gy_, gx_ = np.mgrid[0:2 * q + 1, 0:2 * q + 1]
                da = np.clip(rr - np.hypot(gx_ + x0_ - px, gy_ + y0_ - py) + 0.5, 0, 1) * aa * inside(y0_, y0_ + 2 * q + 1, x0_, x0_ + 2 * q + 1, Y_IN)
                reg = frame[y0_:y0_ + 2 * q + 1, x0_:x0_ + 2 * q + 1]
                dc = np.array([252, 232, 190], f32) if i % 3 else np.array([206, 110, 24], f32)
                reg[..., :3] = reg[..., :3] * (1 - da)[..., None] + dc * da[..., None]
                reg[..., 3] = reg[..., 3] * (1 - da) + da

    # la última gota
    if T_DROP0 < t < T_HIT:
        dyc = -60 * S + 0.5 * G_DROP * (t - T_DROP0) ** 2
        dxc = float(stream_x(dyc))
        rd = 44 * S
        r0, r1 = int(max(0, dyc - 3.4 * rd)), int(min(H, dyc + rd + 2))
        c0, c1 = int(max(0, dxc - rd - 2)), int(min(W, dxc + rd + 2))
        if r1 > r0 and c1 > c0:
            yy_ = np.arange(r0, r1, dtype=f32)[:, None]
            xx_ = np.arange(c0, c1, dtype=f32)[None, :]
            up = np.clip((dyc - yy_) / (3.2 * rd), 0, 1)                      # cola de la gota hacia arriba
            half = np.where(yy_ >= dyc, np.sqrt(np.clip(rd * rd - (yy_ - dyc) ** 2, 0, None)), rd * (1 - up) ** 1.6)
            da = np.clip(half - np.abs(xx_ - dxc) + 0.5, 0, 1) * 0.97
            un = (xx_ - dxc) / np.maximum(half, 0.5)
            dcol = edge_c0[None, None, :] + (mid_c0 - edge_c0)[None, None, :] * (np.sqrt(np.clip(1 - un * un, 0, 1)) ** 1.2)[..., None]
            hl = 0.75 * np.exp(-(((xx_ - dxc + 0.38 * rd) / (0.2 * rd)) ** 2 + ((yy_ - dyc + 0.25 * rd) / (0.38 * rd)) ** 2))
            dcol = np.clip(dcol + 255 * hl[..., None], 0, 255)
            reg = frame[r0:r1, c0:c1]
            reg[..., :3] = reg[..., :3] * (1 - da)[..., None] + dcol * da[..., None]
            reg[..., 3] = reg[..., 3] * (1 - da) + da
    # salpicadura del toque
    if T_HIT <= t < T_HIT + 0.4:
        age = t - T_HIT
        for i in range(14):
            px = cx0 + HIT_X + np.sin(spl_ang[i]) * spl_v[i] * 0.8 * age
            py = cy0 + HIT_Y - np.cos(spl_ang[i]) * spl_v[i] * 0.8 * age + 0.5 * 3600 * S * age * age
            rr = spl_r[i] * (1 - age / 0.4)
            q = int(rr + 2)
            x0_, y0_ = int(px) - q, int(py) - q
            if rr < 0.5 or x0_ < 0 or y0_ < 0 or x0_ + 2 * q + 1 > W or y0_ + 2 * q + 1 > H:
                continue
            gy_, gx_ = np.mgrid[0:2 * q + 1, 0:2 * q + 1]
            da = np.clip(rr - np.hypot(gx_ + x0_ - px, gy_ + y0_ - py) + 0.5, 0, 1) * (1 - age / 0.4)
            reg = frame[y0_:y0_ + 2 * q + 1, x0_:x0_ + 2 * q + 1]
            reg[..., :3] = reg[..., :3] * (1 - da)[..., None] + mid_c0 * da[..., None]
            reg[..., 3] = reg[..., 3] * (1 - da) + da

    al = frame[..., 3:4]
    rgb = np.where(al > 1e-4, frame[..., :3] / np.maximum(al, 1e-4), 0)
    out = np.empty((H, W, 4), np.uint8)
    out[..., :3] = np.clip(rgb + 0.5, 0, 255)
    out[..., 3] = np.clip(al[..., 0] * 255 + 0.5, 0, 255)
    return out


if __name__ == "__main__":
    if OUT.endswith(".png"):                      # hoja de cuadros de prueba: python3 ... 0.25 hoja.png logo.png t1,t2,...
        times = [float(x) for x in sys.argv[4].split(",")]
        tiles = []
        for t in times:
            fr = Image.fromarray(render(t))
            bg = Image.new("RGBA", fr.size, (0, 0, 0, 255))
            bg.alpha_composite(fr)
            tiles.append(bg.convert("RGB"))
        sheet = Image.new("RGB", (W * len(tiles), H))
        for i, im in enumerate(tiles):
            sheet.paste(im, (i * W, 0))
        sheet.save(OUT)
    else:
        black = OUT.endswith(".mp4")              # .mp4 = fondo negro · .mov = fondo transparente
        if black:
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                   "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", OUT]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                   "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", OUT]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = int(round(T_END * FPS))
        for f in range(n):
            fr = render(f / FPS)
            if black:
                fr = (fr[..., :3].astype(np.uint16) * fr[..., 3:4] // 255).astype(np.uint8)
            proc.stdin.write(fr.tobytes())
            if f % 15 == 0:
                print(f"cuadro {f}/{n}", flush=True)
        proc.stdin.close()
        proc.wait()
        print("ok", OUT)
