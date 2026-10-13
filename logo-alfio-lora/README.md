# Logo ALFIO LORA

## Versión cinematográfica (10 s) · `alfio-lora-cinematica.mp4`

1920×1080 sobre negro. El logo se construye solo y el ritmo alterna calma y ráfagas:

1. 0–2,8 s (lento): primerísimo plano que se desliza con la serpiente mientras entra despacio.
2. 2,9–4,2 s (rápido): tres cortes desde ángulos distintos mientras la serpiente acelera y termina.
3. 4,2–5,6 s (lento): órbita en contrapicado alrededor del monograma, que se traza solo.
4. 5,6–7 s (rápido): travelling por el nombre mientras se escribe.
5. 7–8 s: la cámara se aleja y baja la luz.
6. 8 s: impacto: golpe de cámara, destello blanco, sacudida y bloom; reflejo de luz y pulso de brillo hasta el final.

Se genera con `python3 cinematica.py` (necesita numpy, pillow, scipy y scikit-image).

## Primera versión (5 s)

1. 0–1,3 s: la onda turquesa se dibuja de izquierda a derecha con una cabeza de luz.
2. 0,35–1,3 s: el monograma llega desde la cámara, desenfocado, y se asienta.
3. 1,5–2,3 s: ALFIO LORA aparece letra a letra (sube, se enfoca y se junta).
4. 2,6 s: pulso de brillo y un reflejo de luz que recorre todo el logo.
5. Todo el rato: acercamiento lento de cámara.

## Archivos

- `alfio-lora-negro-4k.mp4`: 4K (3840×2160) sobre fondo negro. Para usarlo sobre otro vídeo en CapCut, modo de mezcla **Pantalla** (o **Aclarar**): el negro desaparece.
- `transparente-1080/`: 1920×1080 con fondo transparente (QuickTime Animation), en 4 partes por el límite de 100 MB de GitHub. El número del nombre es el segundo donde va cada parte: 0,0 · 1,2 · 2,5 · 3,8.
- `animar.py`: genera la versión 4K transparente (`python3 animar.py`). Ocupa unos 570 MB, por eso no está en el repo.
