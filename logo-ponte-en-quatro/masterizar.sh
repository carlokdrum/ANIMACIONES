#!/bin/bash
# Masteriza el sonido del logo y lo une al video.
# Uso: ./masterizar.sh   (necesita ffmpeg, python3 con numpy y scipy)
set -e
python3 sonido_cerveza.py sonido-mezcla.wav

# 1) limpieza y carácter: fuera graves sobrantes, menos medios turbios, más agudos, compresión suave
CADENA="highpass=f=55:poles=2,equalizer=f=260:t=q:w=1.0:g=-2.5,treble=g=4:f=3500:t=s:w=0.6,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1:knee=4"
ffmpeg -v error -y -i sonido-mezcla.wav -af "$CADENA" -c:a pcm_f32le sonido-pre.wav

# 2) sonoridad a -16 LUFS (redes) y picos limitados a -1,5 dB
I=$(ffmpeg -hide_banner -nostats -i sonido-pre.wav -af ebur128 -f null - 2>&1 | awk '/Integrated loudness/{f=1} f&&/I:/{print $2; exit}')
G=$(python3 -c "print(round(-16 - ($I), 2))")
ffmpeg -v error -y -i sonido-pre.wav -af "volume=${G}dB,aresample=192000,alimiter=limit=0.84:attack=2:release=40:level=false,aresample=48000" -c:a pcm_s24le sonido-logo-cerveza-master.wav
rm -f sonido-mezcla.wav sonido-pre.wav

# 3) video: fondo negro (.mp4) y fondo transparente (.mov), los dos con el sonido
python3 llenado_cerveza.py 0.5 video-negro.mp4 logo.png
python3 llenado_cerveza.py 0.5 video-alfa.mov logo.png
ffmpeg -v error -y -i video-negro.mp4 -i sonido-logo-cerveza-master.wav -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart logo-cerveza-con-sonido-1080.mp4
ffmpeg -v error -y -i video-alfa.mov -i sonido-logo-cerveza-master.wav -map 0:v -map 1:a -c:v copy -c:a pcm_s24le -shortest logo-cerveza-transparente-1080.mov
rm -f video-negro.mp4 video-alfa.mov
echo "listo"
