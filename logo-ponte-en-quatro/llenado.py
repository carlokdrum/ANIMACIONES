"""Logo de Ponte en Quatro que se llena de abajo arriba como un vaso.

Genera un vídeo 2160x3840 con fondo transparente (QuickTime Animation) para CapCut.
Uso: python3 llenado.py  ->  logo-llenado-4k.mov
"""
import subprocess
import numpy as np
from PIL import Image
from scipy import ndimage

W, H, FPS, DUR = 2160, 3840, 30, 3.0
LOGO_W = 1800                      # ancho del logo en el encuadre 4K
WHITE = np.array([255, 255, 255], np.float32)

# --- logo: recorte, escala y centrado -------------------------------------------
src = np.array(Image.open("logo.png").convert("RGBA"))
ys, xs = np.nonzero(src[..., 3] > 8)
crop = Image.fromarray(src[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
scale = LOGO_W / crop.width
crop = crop.resize((LOGO_W, round(crop.height * scale)), Image.LANCZOS)
alpha = np.array(crop)[..., 3].astype(np.float32) / 255.0      # el logo va en blanco puro
lh, lw = alpha.shape
ox, oy = (W - lw) // 2, (H - lh) // 2

# contorno: anillo de ~12 px por DENTRO del borde, así el logo final queda idéntico al PNG
r = 12
yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
disk = (xx * xx + yy * yy) <= r * r
outline = np.clip(alpha - ndimage.grey_erosion(alpha, footprint=disk), 0, 1)

# --- física del nivel del líquido (muelle amortiguado hacia un objetivo que sube) ---
DT = 1 / 240
T_FILL0, T_RISE = 0.35, 1.25
level, vel, levels = 0.0, 0.0, []
for i in range(int(DUR / DT) + 1):
    t = i * DT
    if t < T_FILL0:
        levels.append(0.0); continue
    u = min(1.0, (t - T_FILL0) / T_RISE)
    target = u * u * (3 - 2 * u) * 1.04          # sube hasta pasar el borde superior
    vel += (-140 * (level - target) - 13 * vel) * DT
    level += vel * DT
    levels.append(level)

cols = np.arange(lw, dtype=np.float32)
rows = np.arange(lh, dtype=np.float32)[:, None]

def ease_out(u):
    u = min(1.0, max(0.0, u)); return 1 - (1 - u) ** 3

proc = subprocess.Popen([
    "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
    "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", "logo-llenado-4k.mov"], stdin=subprocess.PIPE)

for f in range(int(DUR * FPS)):
    t = f / FPS
    lv = levels[min(len(levels) - 1, int(round(t / DT)))]
    # superficie: dos ondas que viajan + inclinación del vaivén; se calma al llenarse
    calm = max(0.0, 1.0 - max(0.0, lv - 0.85) / 0.2)
    amp = 26 * calm
    tilt = 0.035 * np.sin(2 * np.pi * 1.6 * t) * calm
    surf_y = lh * (1 - lv) + amp * np.sin(2 * np.pi * cols / 420 + 7.5 * t) \
        + 0.45 * amp * np.sin(2 * np.pi * cols / 170 - 11 * t) + tilt * (cols - lw / 2)
    fill = np.clip(rows - surf_y[None, :] + 1.0, 0, 1) * alpha    # borde suavizado de 2 px

    # contorno: aparece con un pequeño ajuste de escala (1.06 -> 1)
    oa = ease_out(t / 0.4)
    a_logo = np.maximum(fill, outline * oa)

    frame = np.zeros((H, W, 4), np.uint8)
    if oa < 1:
        s = 1.06 - 0.06 * oa
        img = Image.fromarray((a_logo * 255).astype(np.uint8)).resize((round(lw * s), round(lh * s)), Image.BILINEAR)
        a_big = np.array(img).astype(np.float32) / 255
        bh, bw = a_big.shape
        bx, by = (W - bw) // 2, (H - bh) // 2
        frame[by:by + bh, bx:bx + bw, :3] = 255
        frame[by:by + bh, bx:bx + bw, 3] = (a_big * 255).astype(np.uint8)
    else:
        frame[oy:oy + lh, ox:ox + lw, :3] = 255
        frame[oy:oy + lh, ox:ox + lw, 3] = (a_logo * 255).astype(np.uint8)
    proc.stdin.write(frame.tobytes())

proc.stdin.close(); proc.wait()
print("ok", lw, lh)
