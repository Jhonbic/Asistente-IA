"""Prueba aislada del VAD (Fase A).

Habla una frase y después quedate en silencio: el script debe cortar solo
~1s después de que dejes de hablar (no hace falta presionar nada). Guarda
el audio y lo transcribe con Whisper (Capa 2) para confirmar que el corte
automático no se comió palabras del final.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_vad.py
"""

import sys
import time

import audio
from stt import Transcriptor
from vad import EscuchaConVAD

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    escucha = EscuchaConVAD()
    transcriptor = Transcriptor("small")

    print("Hablá una frase y quedate en silencio (corta sola tras ~1s)...")
    inicio = time.time()
    grabacion = escucha.grabar()
    duracion = time.time() - inicio
    print(f"Cortó sola después de {duracion:.1f}s de grabación. "
          f"Muestras: {len(grabacion)}")

    audio.guardar_wav(grabacion, "prueba_vad.wav")
    print("Guardado como prueba_vad.wav")

    texto = transcriptor.transcribir(grabacion)
    print(f"Transcripción: {texto!r}")


if __name__ == "__main__":
    main()
