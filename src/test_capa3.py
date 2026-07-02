"""Prueba aislada de la Capa 3: chat por TEXTO en la terminal (sin audio).

Requiere el archivo .env con tu NVIDIA_API_KEY (ver .env.example).

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_capa3.py

Escribe mensajes y verás las respuestas del modelo. Prueba también la
memoria: pregunta algo, y luego haz una pregunta de seguimiento que solo
tenga sentido con el contexto anterior. Escribe "salir" para terminar.
"""

import sys
import time

from llm import Cerebro

sys.stdout.reconfigure(encoding="utf-8")

cerebro = Cerebro()
print(f"Chat de prueba con {cerebro.modelo} (escribe 'salir' para terminar)\n")

while True:
    try:
        entrada = input("Tú: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not entrada:
        continue
    if entrada.lower() in ("salir", "exit", "quit"):
        break

    inicio = time.perf_counter()
    respuesta = cerebro.responder(entrada)
    duracion = time.perf_counter() - inicio

    print(f"Asistente ({duracion:.1f}s): {respuesta}\n")

print("Hasta luego.")
