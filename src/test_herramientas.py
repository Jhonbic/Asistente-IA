"""Prueba aislada del Módulo 1 de la Fase B: herramientas de apps/webs.

Ejecuta cada función directamente (sin pasar por el LLM ni por voz) para
verificar que abren lo que deben abrir. Correr desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_herramientas.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

import time

from herramientas import (
    abrir_app,
    abrir_web,
    apagar_o_suspender_pc,
    buscar_en_google,
    buscar_info,
    cancelar_timer,
    control_multimedia,
    ejecutar_herramienta,
    estado_sistema,
    listar_timers,
    obtener_avisos_pendientes,
    obtener_clima,
    poner_timer,
    reproducir_video_youtube,
    silenciar_volumen,
    subir_bajar_volumen,
)

print("=== Prueba: abrir_app (bloc de notas) ===")
print(abrir_app("bloc de notas"))

input("Presiona Enter para continuar...")

print("\n=== Prueba: abrir_app (app inexistente) ===")
print(abrir_app("photoshop"))

input("Presiona Enter para continuar...")

print("\n=== Prueba: abrir_web (youtube) ===")
print(abrir_web("youtube"))

input("Presiona Enter para continuar...")

print("\n=== Prueba: buscar_en_google ===")
print(buscar_en_google("clima en Buenos Aires"))

input("Presiona Enter para continuar...")

print("\n=== Prueba: reproducir_video_youtube ===")
print(reproducir_video_youtube("trailer oficial Inception"))

input("Presiona Enter para continuar...")

print("\n=== Prueba: ejecutar_herramienta (despacho por nombre, como lo hará llm.py) ===")
print(ejecutar_herramienta("abrir_app", {"nombre": "calculadora"}))

print("\nListo. Verificá que se hayan abierto: bloc de notas, YouTube, una búsqueda de Google y la calculadora.")

print("\n=== Prueba: obtener_clima (Buenos Aires) ===")
print(obtener_clima("Buenos Aires"))

print("\n=== Prueba: obtener_clima (ciudad inventada) ===")
print(obtener_clima("Ciudadquenoexisteasdf"))

print("\n=== Prueba: buscar_info ===")
print(buscar_info("quien fue Alan Turing"))

print("\n=== Prueba: estado_sistema ===")
print(estado_sistema())

print("\n=== Prueba: subir_bajar_volumen ===")
print(subir_bajar_volumen("subir"))
print(subir_bajar_volumen("bajar"))

print("\n=== Prueba: silenciar_volumen (silenciar y reactivar) ===")
print(silenciar_volumen(True))
print(silenciar_volumen(False))

print("\n=== Prueba: control_multimedia (play/pausa) ===")
print(control_multimedia("reproducir"))

print("\n=== Prueba: apagar_o_suspender_pc SIN confirmar (no debe apagar nada) ===")
print(apagar_o_suspender_pc("apagar", confirmar=False))

print("\n=== Prueba: timers ===")
print(poner_timer(0.05, "probar el timer"))  # 3 segundos
print(poner_timer(10, "un timer largo que vamos a cancelar"))
print(listar_timers())
print(cancelar_timer("largo"))
print(listar_timers())

print("Esperando a que venza el timer corto (3s)...")
avisos = []
for _ in range(10):
    avisos = obtener_avisos_pendientes()
    if avisos:
        break
    time.sleep(0.5)
print("Avisos pendientes recibidos:", avisos)
print(listar_timers())
