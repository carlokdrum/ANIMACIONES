# Logo Ponte en Quatro: llenado de cerveza

Un chorro de cerveza ámbar (tipo ale quadrupel) cae desde arriba a la derecha y entra por lo alto de las letras, que se llenan con burbujas y una corona fina de espuma. Luego cae una última gota: al tocar las letras el líquido se vacía y, al llegar al fondo, las letras desaparecen de golpe. Animación y sonido hechos por programa (no es video filmado ni generado con IA).

## Archivos

- `logo-cerveza-transparente-1080.mov`: 1080×1920, 5,3 s, 30 fps, fondo transparente (QuickTime Animation, el formato que lee CapCut en Mac), con el sonido incluido.
- `logo-cerveza-con-sonido-1080.mp4`: lo mismo sobre fondo negro, con sonido.
- `sonido-logo-cerveza-master.wav`: el sonido solo, masterizado (−16 LUFS, picos a −1,5 dB, 48 kHz / 24 bits).
- `llenado_cerveza.py`: genera el video.
- `sonido_cerveza.py`: genera el sonido sin masterizar.
- `masterizar.sh`: lo hace todo de una vez (sonido, masterización, los dos videos).

## Volver a generar

```bash
pip install numpy pillow scipy
./masterizar.sh
```

O por separado: `python3 llenado_cerveza.py 0.5 salida.mov logo.png` (escala `0.5` = 1080, `1` = 4K; salida `.mov` = fondo transparente, `.mp4` = fondo negro).

## Qué tocar para editar (en `llenado_cerveza.py`)

| Para cambiar | Busca |
|---|---|
| Color de la cerveza | `top_c, bot_c` (y `edge_c, mid_c` para el chorro) |
| Brillo del líquido | `sheen` y la línea de `spec` |
| Velocidad del llenado | `T_RISE` (y mover `T_STOP`, `T_DROP0` en la misma proporción) |
| Velocidad del vaciado | `T_DRAIN` |
| Cantidad de espuma | `THICK` y `FOAM_TOP` |
| Que la espuma rebose y baje por las letras | `OVERFLOW = True` |
| Separación entre letras | `GROW` |
| Grosor del chorro | la línea `hw = (78 - 30 * ...` |

Si cambias los tiempos del video, ajusta los mismos tiempos al principio de `sonido_cerveza.py`.

## Tiempos

Chorro 0,25–2,5 s · lleno 2,75 s · sale la gota 3,25 s · toca 3,8 s · vacío y fin de las letras 4,6 s · fin 5,3 s.
