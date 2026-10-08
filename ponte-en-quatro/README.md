# Ponte en Quatro: textos animados

Textos animados para el anuncio vertical (27 s) de la cerveza Ponte en Quatro de Estrella Cervecería, hechos con HyperFrames.

## Archivos finales

- `renders/textos-fondo-verde.mp4`: capa de textos en 1080×1920 sobre verde puro, para montar en CapCut con croma.
- `renders/vista-previa-720.mp4`: vista previa de los textos sobre el vídeo.

- `renders/transparente/`: los mismos textos con fondo transparente real (ProRes 4444 con alfa), en 4 clips. El número del nombre es el segundo donde va cada uno. Es la opción recomendada, sin bordes verdes.

- `renders/4k/`: **versión final recomendada**. Los textos en 4K (2160×3840) con fondo transparente en formato QuickTime Animation (sin pérdida), que es el que lee CapCut en Mac. Son 3 clips; el número del nombre es el segundo donde va cada uno (0,0 · 8,4 · 18,2). Se colocan encima del vídeo sin croma.

## Montaje en CapCut

1. Vídeo original en 1080 en la línea de tiempo.
2. `textos-fondo-verde.mp4` como superposición en el segundo 0, a pantalla completa.
3. Recortar → Croma → cuentagotas sobre el verde y subir la intensidad. Si quedan bordes verdosos, subir el suavizado.

## Escenas

| Tiempo | Texto | Animación |
|---|---|---|
| 0–2,4 s | Hay cervezas… | Se llena de abajo arriba como un vaso y se vacía antes del corte |
| 2,5–4 s | …y está ESTA. | Cada letra de ESTA cae desde la cámara y sacude la frase |
| 8–13 s | MALTA · LÚPULO · DÁTILES · 100% ARTESANAL | Estallan en letras que flotan hacia cámara y se desvanecen |
| 18–22 s | La cerveza / QUADRUPEL / prémium del país. | Caen como el lúpulo y se apilan |

Tipografía: Oswald (golpes) + Playfair Display cursiva (frases suaves), combinación 2 (`data-fonts="2"` en `#root`).

## Volver a generar

```bash
npm install
npx hyperframes render --format mov -o renders/textos-transparente.mov
ffmpeg -f lavfi -i "color=c=0x00FF00:s=1080x1920:r=30:d=27" -i renders/textos-transparente.mov \
  -filter_complex "[0][1]overlay=format=auto,format=yuv420p[v]" -map "[v]" -c:v libx264 -crf 14 renders/textos-fondo-verde.mp4
```

`_opciones/` guarda las variantes descartadas: las tres entradas de "Hay cervezas…" y las tres combinaciones de tipografía.
