"""Capa 5 — El asistente de voz completo.

Conecta las cuatro capas en el ciclo:
    escuchar (Capa 1) → transcribir (Capa 2) → pensar (Capa 3) → hablar (Capa 4)

Modo de uso (push-to-talk):
    1. Presiona Enter para empezar a hablar.
    2. Habla.
    3. Presiona Enter de nuevo para terminar.
    4. El asistente responde con voz. Repite.

Para despedirte, di "adiós" o "termina".

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\asistente.py
"""

import sys

import numpy as np

import audio
from llm import Cerebro
from stt import Transcriptor
from tts import Voz

sys.stdout.reconfigure(encoding="utf-8")

# Si el usuario dice alguna de estas palabras (sola o dentro de una frase
# corta), el asistente se despide y termina.
PALABRAS_SALIDA = ("adiós", "adios", "termina", "hasta luego", "chau", "chao")


def es_despedida(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in PALABRAS_SALIDA) and len(t.split()) <= 4


def main() -> None:
    # Cargamos todo UNA vez al inicio (los modelos tardan unos segundos en
    # cargar; hacerlo en cada turno sería un desperdicio).
    print("Iniciando asistente...")
    transcriptor = Transcriptor("small")
    cerebro = Cerebro()
    voz = Voz()  # es_AR-daniela-high

    voz.decir("Hola, te escucho.")
    print("\n💡 Presiona Enter para hablar; Enter de nuevo para terminar de hablar.")
    print("   Di 'adiós' para salir, o presiona Ctrl+C.\n")

    while True:
        try:
            input("⏎  Enter para hablar...")
            grabacion = audio.grabar_push_to_talk()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        # Silencio o grabación vacía → volvemos a escuchar sin gastar
        # una petición al LLM.
        if len(grabacion) < 1600 or float(np.abs(grabacion).max()) < 0.01:
            print("(no escuché nada, intenta de nuevo)\n")
            continue

        texto = transcriptor.transcribir(grabacion)
        if not texto:
            print("(no entendí nada, intenta de nuevo)\n")
            continue
        print(f"Tú: {texto}")

        if es_despedida(texto):
            voz.decir("Hasta luego, que estés bien.")
            break

        try:
            respuesta = cerebro.responder(texto)
        except Exception as e:
            # Si NIM falla (sin internet, saturado, key inválida), el
            # asistente lo dice por voz en vez de crashear.
            print(f"⚠️  Error del LLM: {type(e).__name__}: {e}")
            voz.decir("Perdón, tuve un problema al conectar con mi cerebro. "
                      "Intenta de nuevo.")
            continue

        print(f"Asistente: {respuesta}\n")
        voz.decir(respuesta)


if __name__ == "__main__":
    main()
p