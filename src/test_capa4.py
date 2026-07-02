"""Prueba aislada de la Capa 4: reproduce la misma frase con cada voz
descargada, anunciando cuál suena, para que elijas tu favorita.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_capa4.py
"""

import sys
import time

from tts import Voz, CARPETA_VOCES

sys.stdout.reconfigure(encoding="utf-8")

FRASE = (
    "Hola, soy tu asistente personal. Si te gusta cómo sueno, "
    "elígeme como tu voz."
)

voces = sorted(p.stem for p in CARPETA_VOCES.glob("*.onnx"))
print(f"Voces encontradas: {voces}\n")

for nombre in voces:
    print(f"🔊 Voz: {nombre}")
    inicio = time.perf_counter()
    voz = Voz(nombre)
    audio = voz.sintetizar(FRASE)
    print(f"   (sintetizado en {time.perf_counter() - inicio:.2f}s)")
    import sounddevice as sd
    sd.play(audio, samplerate=voz.sample_rate)
    sd.wait()
    time.sleep(0.5)  # pausa breve entre voces

print("\n¿Cuál te gustó más? Esa será la voz del asistente.")
