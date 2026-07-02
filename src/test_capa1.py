"""Prueba aislada de la Capa 1.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_capa1.py

Qué hace:
1. Lista tus dispositivos de audio.
2. Graba 5 segundos del micrófono por defecto.
3. Guarda la grabación como prueba_capa1.wav.
4. La reproduce por los altavoces para que verifiques que se oye bien.
"""

import numpy as np

import audio

print("=== Dispositivos de audio ===")
print("(el símbolo > marca tu micrófono por defecto, < tu salida por defecto)\n")
audio.listar_dispositivos()

print("\n=== Prueba de grabación ===")
input("Presiona Enter cuando estés listo para grabar 5 segundos...")
grabacion = audio.grabar_fijo(5)

# El volumen pico nos dice si el micrófono captó algo:
# ~0.0 significa silencio total (micrófono equivocado o muteado).
pico = float(np.abs(grabacion).max())
print(f"Volumen pico de la grabación: {pico:.3f} (si es < 0.01, algo anda mal)")

audio.guardar_wav(grabacion, "prueba_capa1.wav")
print("Guardado como prueba_capa1.wav")

print("\n🔊 Reproduciendo lo que grabé...")
audio.reproducir(grabacion)
print("¿Se escuchó tu voz clara? Si sí, la Capa 1 está lista. ✅")
