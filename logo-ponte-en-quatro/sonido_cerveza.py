"""Sonido para la animación del logo de Ponte en Quatro llenándose de cerveza.

Todo sintetizado por programa (sin grabaciones): el líquido se hace sumando miles de
burbujas, que es lo que realmente suena cuando se sirve una bebida.

Uso: python3 sonido_cerveza.py salida.wav
"""
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 5.2667
# tiempos del video
T_STREAM, T_HITBOTTOM, T_STOP = 0.25, 0.62, 2.5
T_FULL = 2.75           # termina de llenarse
T_DROP = 3.81           # la gota toca
T_EMPTY = 4.56          # se vacía y desaparecen las letras

N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(4)
L = np.zeros(N)
R = np.zeros(N)


def smooth(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def env(t0, t1, a=0.05, r=0.1):
    """Envolvente: sube en `a` segundos desde t0 y baja en `r` segundos hasta t1."""
    return smooth((t - t0) / a) * (1 - smooth((t - (t1 - r)) / r))


def band(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def add(x, pan=0.0, gain=1.0):
    """pan: -1 izquierda, +1 derecha."""
    a = (pan + 1) * np.pi / 4
    L[:len(x)] += x * np.cos(a) * gain
    R[:len(x)] += x * np.sin(a) * gain


def bubble(t0, f0, amp, pan, rise=1.0):
    """Una burbuja: un tono que sube un poco de afinación y se apaga rápido."""
    d = 0.13 * f0 + 0.0072 * f0 ** 1.5               # amortiguación (más aguda = más corta)
    n = int(min(0.25, 7.0 / d) * SR)
    i0 = int(t0 * SR)
    if i0 < 0 or i0 + n >= N or n < 8:
        return
    tt = np.arange(n) / SR
    f = f0 * (1 + rise * 0.1 * d * tt)
    x = amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * tt)
    x[:24] *= np.linspace(0, 1, 24)
    a = (pan + 1) * np.pi / 4
    L[i0:i0 + n] += x * np.cos(a)
    R[i0:i0 + n] += x * np.sin(a)


def resonant_noise(fc, gain_t, width=0.33, seed=0):
    """Ruido que pasa por una resonancia cuya afinación `fc(t)` cambia con el tiempo."""
    noise = np.random.default_rng(seed).standard_normal(N)
    centers = np.geomspace(120, 5000, 22)
    out = np.zeros(N)
    for c in centers:
        g = np.exp(-0.5 * (np.log2(fc / c) / width) ** 2) * gain_t
        if g.max() < 1e-4:
            continue
        out += band(noise, c / 1.19, c * 1.19) * g
    return out


# ---------------------------------------------------------------- 1. el chorro y el llenado
fill = smooth((t - T_HITBOTTOM) / (T_FULL - T_HITBOTTOM))          # 0 vacío → 1 lleno
pour_env = env(T_HITBOTTOM - 0.03, T_STOP + 0.3, a=0.06, r=0.35)

# el chorro en el aire: un siseo suave que llega antes de que toque el fondo
hiss = band(rng.standard_normal(N), 2500, 9000)
flutter = 0.7 + 0.3 * np.abs(signal.sosfilt(signal.butter(2, 30, fs=SR, output="sos"), rng.standard_normal(N))) * 6
add(hiss * env(T_STREAM, T_STOP + 0.25, a=0.25, r=0.3) * flutter * 0.035, pan=0.35)

# el cuerpo del llenado: resonancia que sube de tono a medida que se llena el "vaso"
fc_fill = 260 * (1300 / 260) ** fill
turb = 0.55 + 0.45 * np.abs(signal.sosfilt(signal.butter(2, 18, fs=SR, output="sos"), rng.standard_normal(N))) * 8
add(resonant_noise(fc_fill, pour_env * turb, seed=1) * 0.30, pan=0.15)
add(resonant_noise(fc_fill * 2.3, pour_env * turb, width=0.5, seed=2) * 0.10, pan=-0.1)

# burbujas del chorro golpeando el líquido: muchas, pequeñas y grandes
n_b = int(430 * (T_STOP + 0.25 - T_HITBOTTOM))
for tb in rng.uniform(T_HITBOTTOM, T_STOP + 0.25, n_b):
    fl = float(smooth((tb - T_HITBOTTOM) / (T_FULL - T_HITBOTTOM)))
    f0 = float(np.exp(rng.normal(np.log(700 + 900 * fl), 0.75)))
    f0 = min(max(f0, 250), 9000)
    amp = 0.11 * rng.uniform(0.2, 1.0) ** 2 * (900 / f0) ** 0.35
    amp *= float(smooth((tb - T_HITBOTTOM) / 0.08)) * float(1 - smooth((tb - T_STOP) / 0.25))
    bubble(tb, f0, amp, pan=rng.normal(0.15, 0.35))

# el primer golpe del chorro contra el fondo
splash = band(rng.standard_normal(N), 600, 7000) * np.exp(-np.clip(t - T_HITBOTTOM, 0, None) / 0.07) * (t >= T_HITBOTTOM)
add(splash * 0.20, pan=0.2)
for k in range(26):
    bubble(T_HITBOTTOM + rng.uniform(0, 0.12), rng.uniform(350, 1400), rng.uniform(0.05, 0.16), pan=rng.normal(0.2, 0.3))

# ---------------------------------------------------------------- 2. la espuma: burbujeo fino
fizz_env = smooth((t - 1.0) / 1.2) * (1 - smooth((t - T_DROP) / 0.25)) * (0.55 + 0.45 * np.exp(-np.clip(t - T_FULL, 0, None) / 0.9))
fizz = band(rng.standard_normal(N), 5500, 14000)
crackle = (rng.random(N) < 0.012) * rng.uniform(0.3, 1.0, N)                # chasquidos sueltos
crackle = band(crackle, 4000, 15000) * 9
add(fizz * fizz_env * 0.018, pan=-0.2)
add(np.roll(fizz, 977) * fizz_env * 0.018, pan=0.2)
add(crackle * fizz_env * 0.022, pan=-0.3)
add(np.roll(crackle, 2311) * fizz_env * 0.022, pan=0.3)
for tb in rng.uniform(T_STOP, T_DROP, 150):                                  # burbujitas que revientan en la espuma
    bubble(tb, rng.uniform(2800, 8500), rng.uniform(0.008, 0.035) * float(np.exp(-(tb - T_STOP) / 1.2)), pan=rng.uniform(-0.7, 0.7))

# ---------------------------------------------------------------- 3. la última gota: "plic"
bubble(T_DROP, 1150, 0.55, pan=0.2, rise=2.6)
bubble(T_DROP + 0.012, 2300, 0.12, pan=0.25, rise=2.0)
bubble(T_DROP + 0.055, 1700, 0.10, pan=0.1, rise=2.0)
tick = band(rng.standard_normal(N), 1500, 9000) * np.exp(-np.clip(t - T_DROP, 0, None) / 0.012) * (t >= T_DROP)
add(tick * 0.14, pan=0.2)

# ---------------------------------------------------------------- 4. el vaciado: gorgoteo que baja de tono
u = np.clip((t - T_DROP) / (T_EMPTY - T_DROP), 0, 1)
drain_env = env(T_DROP + 0.03, T_EMPTY + 0.004, a=0.10, r=0.012)
level = 1 - u ** 1.7                                                         # igual que en el video
fc_drain = 240 * (1250 / 240) ** level
glug = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(9 + 16 * u) / SR)) ** 2   # "glu-glu-glu" que se acelera
add(resonant_noise(fc_drain, drain_env * glug, seed=5) * 0.42, pan=0.0)
add(resonant_noise(fc_drain * 0.5, drain_env * glug, width=0.4, seed=6) * 0.22, pan=0.0)
for tb in rng.uniform(T_DROP + 0.05, T_EMPTY - 0.01, 260):
    uu = (tb - T_DROP) / (T_EMPTY - T_DROP)
    f0 = float(np.exp(rng.normal(np.log(240 * (1250 / 240) ** (1 - uu ** 1.7)), 0.5)))
    bubble(tb, min(max(f0, 160), 6000), 0.12 * rng.uniform(0.3, 1.0) ** 1.5 * (0.5 + uu), pan=rng.normal(0, 0.4))
# el sorbo final: aire entrando justo antes de que se vacíe del todo
slurp_env = smooth((t - (T_EMPTY - 0.26)) / 0.2) * (t < T_EMPTY)
fc_slurp = 500 * (3600 / 500) ** np.clip((t - (T_EMPTY - 0.26)) / 0.26, 0, 1)
add(resonant_noise(fc_slurp, slurp_env * (0.6 + 0.4 * glug), width=0.28, seed=8) * 0.30, pan=0.0)

# ---------------------------------------------------------------- 5. corte seco: un golpe grave y corto
tk = np.clip(t - T_EMPTY, 0, None)
thump = np.sin(2 * np.pi * (95 * tk - 180 * tk ** 2)) * np.exp(-tk / 0.035) * (t >= T_EMPTY)
click = band(rng.standard_normal(N), 900, 6000) * np.exp(-tk / 0.004) * (t >= T_EMPTY)
add(thump * 0.55)
add(click * 0.16)

# ---------------------------------------------------------------- salida (mezcla sin masterizar)
mix = np.stack([L, R], axis=1)
mix *= np.minimum(1, t / 0.02)[:, None]                 # sin chasquido al empezar
mix[t > T_EMPTY + 0.30] = 0                             # silencio total tras el corte
peak = np.abs(mix).max()
mix = mix / peak * 0.5                                  # margen para la masterización
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else "sonido-mezcla.wav", SR, mix.astype(np.float32))
print("pico original", round(float(peak), 3), "| duración", round(N / SR, 3), "s")
