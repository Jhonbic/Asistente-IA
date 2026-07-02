"""Prueba del Módulo 2 de la Fase B: function calling en llm.py.

Chat por texto en terminal (sin audio) para verificar que el modelo elige
la herramienta correcta, la ejecuta y redacta una respuesta hablable con el
resultado. Correr desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_capa3b.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

from llm import Cerebro

cerebro = Cerebro()

print("Chat de prueba (Fase B: herramientas). Escribí 'salir' para terminar.\n")
print("Probá cosas como:")
print("  - abrí YouTube")
print("  - ¿cuánta batería queda?")
print("  - poné un timer de medio minuto que se llame prueba")
print("  - ¿qué clima hace en Córdoba?")
print("  - apagá la PC   (debe pedir confirmación, no ejecutarlo)")
print("  - ¿cómo estás?  (no debería usar ninguna herramienta)\n")

while True:
    texto = input("Vos: ").strip()
    if texto.lower() == "salir":
        break
    if not texto:
        continue
    respuesta = cerebro.responder(texto)
    print(f"Asistente: {respuesta}\n")
