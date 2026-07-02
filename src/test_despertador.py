"""Prueba aislada del despertador (Fase A).

Corre indefinidamente escuchando el micrófono. Decí "Hey Jarvis" y verificá
que detecta. También sirve para calibrar UMBRAL_DETECCION: mirá los scores
en vivo (silencio y voz normal deberían quedar bien por debajo del umbral;
solo la palabra de activación debería cruzarlo).

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_despertador.py

Ctrl+C para salir.
"""

import sys

from despertador import Despertador, UMBRAL_DETECCION

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    despertador = Despertador()
    print(f"Umbral de detección actual: {UMBRAL_DETECCION}")
    print('Decí "Hey Jarvis"... (Ctrl+C para salir)\n')

    def mostrar_score(score: float) -> None:
        # No imprimimos silencio puro (score ~0) para no saturar la consola.
        if score > 0.05:
            print(f"  score: {score:.3f}")

    try:
        while True:
            score = despertador.escuchar(en_cada_bloque=mostrar_score)
            print(f"\n¡DESPERTÉ! (score={score:.3f})\n")
    except KeyboardInterrupt:
        print("\nFin de la prueba.")


if __name__ == "__main__":
    main()
