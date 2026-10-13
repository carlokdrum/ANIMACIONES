# Logo ALFIO LORA

## Versión cinematográfica (10 s) · `alfio-lora-cinematica.mp4`

1920×1080 sobre negro. El logo se construye solo:

1. 0,2–3,6 s: la onda entra como una serpiente a velocidad constante. Tres planos: primerísimo plano, contrapicado lateral y picado más abierto. Cabeza de luz con destello anamórfico.
2. 3,6–5 s: el monograma se traza solo, con dolly lento en contrapicado.
3. 5–7,2 s: las letras se trazan mientras caen desde la cámara y se estampan con rebote y sacudida, con tres ángulos de cámara.
4. 7,25 s: corte a negro.
5. 7,45 s: impacto: el logo irrumpe con la cámara saliendo hacia atrás, destello blanco, onda expansiva de luz, destello anamórfico, sacudida y bloom. Después, reflejos que recorren el metal y pulso de brillo.

Durante toda la pieza una luz que gira saca brillos en los biseles del metal. El recorrido de construcción se calcula por dentro de cada forma para que el frente avance limpio. Se genera con `python3 cinematica.py` (numpy, pillow, scipy, scikit-image).

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
