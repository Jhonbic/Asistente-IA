"""Prueba aislada de la Capa 2.

Transcribe prueba_capa1.wav (grabado en la Capa 1) con los modelos
'base' y 'small', midiendo el tiempo de cada uno, para comparar
velocidad y calidad en esta PC concreta.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_capa2.py
"""

import sys
import time
import wave

import numpy as np

# La consola de Windows usa cp1252 por defecto y no puede imprimir emojis/acentos raros.
sys.stdout.reconfigure(encoding="utf-8")

from stt import Transcriptor


def cargar_wav(ruta: str) -> np.ndarray:
    """Lee un .wav de 16 bits y lo devuelve como float32 (-1.0 a 1.0)."""
    with wave.open(ruta, "rb") as f:
        datos = f.readframes(f.getnframes())
    return np.frombuffer(datos, dtype=np.int16).astype(np.float32) / 32767.0


audio = cargar_wav("prueba_capa1.wav")
print(f"Audio cargado: {len(audio) / 16000:.1f} segundos\n")

for nombre in ["base", "small"]:
    print(f"--- Modelo '{nombre}' ---")
    t = Transcriptor(nombre)

    inicio = time.perf_counter()
    texto = t.transcribir(audio)
    duracion = time.perf_counter() - inicio

    print(f"⏱️  Tiempo de transcripción: {duracion:.2f}s")
    print(f"📝 Texto: \"{texto}\"\n")
