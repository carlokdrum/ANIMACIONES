# Logo ALFIO LORA

## Versión cinematográfica compleja (8 s) · `alfio-lora-cinematica.mp4`

1920×1080 sobre negro. El logo se construye solo: la onda entra como una serpiente siguiendo su recorrido y el monograma y las letras se trazan a lo largo de su forma. Cuatro planos de cámara: primerísimo plano persiguiendo a la serpiente, contrapicado en perspectiva sobre el monograma, travelling por el nombre y plano general de revelación con destello. Barridos con desenfoque de movimiento en los cortes. Se genera con `python3 cinematica.py` (necesita numpy, pillow, scipy y scikit-image).

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
