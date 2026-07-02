"""Audición de voces FEMENINAS disponibles en Piper para español.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_voces_mujer.py
"""

import sys
import time

from tts import Voz

sys.stdout.reconfigure(encoding="utf-8")

FRASE = (
    "Hola, soy tu asistente personal. Si te gusta cómo sueno. "
    "elígeme como tu voz."
)

# (etiqueta, nombre del modelo, speaker_id)
CANDIDATAS = [
    ("es_AR-daniela-high (Argentina)", "es_AR-daniela-high", None),
    #("es_ES-sharvard-medium hablante F (España)", "es_ES-sharvard-medium", 1),
    #("es_MX-claude-high (México)", "es_MX-claude-high", None),
]

for etiqueta, modelo, speaker in CANDIDATAS:
    print(f"🔊 {etiqueta}")
    voz = Voz(modelo, speaker_id=speaker)
    voz.decir(FRASE)
    time.sleep(0.5)

print("\n¿Cuál te gustó más?")
