"""Capa 5 — El asistente de voz completo.

Conecta todas las capas en el ciclo:
    despertar (Fase A) → escuchar (Capa 1 + VAD) → transcribir (Capa 2)
    → pensar (Capa 3) → hablar (Capa 4)

Modo de uso por defecto (manos libres):
    1. Di "Hey Jarvis". Sonará un bip corto de confirmación.
    2. Habla. El asistente corta solo cuando dejas de hablar (VAD).
    3. El asistente responde con voz y vuelve a esperar la palabra de activación.

Modo push-to-talk clásico (con --teclado):
    1. Presiona Enter para empezar a hablar.
    2. Habla.
    3. Presiona Enter de nuevo para terminar.
    4. El asistente responde con voz. Repite.

Para despedirte, di "adiós" o "termina" (en cualquiera de los dos modos).

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\asistente.py            (manos libres)
    venv\\Scripts\\python.exe src\\asistente.py --teclado  (push-to-talk)
"""

import argparse
import sys

import numpy as np

import audio
from despertador import Despertador
from herramientas import obtener_avisos_pendientes, precargar_catalogo_apps
from llm import Cerebro
from stt import Transcriptor
from tts import Voz
from vad import EscuchaConVAD

sys.stdout.reconfigure(encoding="utf-8")

# Si el usuario dice alguna de estas palabras (sola o dentro de una frase
# corta), el asistente se despide y termina.
PALABRAS_SALIDA = ("adiós", "adios", "termina", "hasta luego", "chau", "chao", "desactivate")


def es_despedida(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in PALABRAS_SALIDA) and len(t.split()) <= 4


def hablar_avisos_pendientes(voz: Voz) -> None:
    """Habla por TTS los timers que vencieron desde la última vez que se revisó.

    Los timers de herramientas.py corren en hilos aparte (threading.Timer) y
    solo apilan su mensaje en una cola (obtener_avisos_pendientes); es acá,
    desde el hilo principal, donde recién se convierten en voz — nunca desde
    el hilo del timer, para no pisar un turno de conversación en curso.
    """
    for aviso in obtener_avisos_pendientes():
        print(f"⏰ Aviso de timer: {aviso}\n")
        voz.decir(aviso)


def procesar_turno(grabacion: np.ndarray, transcriptor: Transcriptor, cerebro: Cerebro, voz: Voz) -> bool:
    """Transcribe, piensa y responde un turno de conversación.

    Devuelve False si el usuario se despidió (señal para terminar el loop).
    """
    # Silencio o grabación vacía → volvemos a escuchar sin gastar una
    # petición al LLM.
    if len(grabacion) < 1600 or float(np.abs(grabacion).max()) < 0.01:
        print("(no escuché nada, intenta de nuevo)\n")
        return True

    texto = transcriptor.transcribir(grabacion)
    if not texto:
        print("(no entendí nada, intenta de nuevo)\n")
        return True
    print(f"Tú: {texto}")

    if es_despedida(texto):
        voz.decir("Hasta luego, que estés bien.")
        return False

    try:
        respuesta = cerebro.responder(texto)
    except Exception as e:
        # Si NIM falla (sin internet, saturado, key inválida), el
        # asistente lo dice por voz en vez de crashear.
        print(f"⚠️  Error del LLM: {type(e).__name__}: {e}")
        voz.decir("Perdón, tuve un problema al conectar con mi cerebro. "
                  "Intenta de nuevo.")
        return True

    print(f"Asistente: {respuesta}\n")
    voz.decir(respuesta)
    return True


def loop_manos_libres(transcriptor: Transcriptor, cerebro: Cerebro, voz: Voz) -> None:
    """Loop principal: espera 'Hey Jarvis' y abre una sesión de conversación.

    Una vez activada la sesión, se siguen escuchando turnos sin repetir la
    palabra de activación (no hace falta decir "Hey Jarvis" antes de cada
    frase). La sesión termina cuando el usuario se despide (procesar_turno
    devuelve False) y el programa vuelve a esperar "Hey Jarvis" para abrir
    una sesión nueva; el programa en sí solo termina con Ctrl+C.

    Nota sobre auto-despertarse: el despertador solo escucha cuando lo
    llamamos explícitamente (despertador.escuchar()), y eso ocurre DESPUÉS
    de que voz.decir() ya terminó de reproducirse (todo el loop es
    secuencial, no hay hilos). Por eso el asistente nunca puede activarse
    con su propia voz: mientras habla, nadie está escuchando el micrófono
    para la palabra de activación.
    """
    despertador = Despertador()
    escucha = EscuchaConVAD()

    voz.decir("Hola, di Hey Jarvis cuando quieras hablarme.")
    print("\n💡 Di 'Hey Jarvis' para activar el micrófono. Di 'adiós' para terminar "
          "la sesión, o Ctrl+C para salir del programa.\n")

    try:
        while True:
            hablar_avisos_pendientes(voz)  # por si venció mientras terminaba la sesión anterior
            print("😴 Esperando 'Hey Jarvis'...")
            # en_cada_bloque corre cada ~80ms mientras se espera la palabra de
            # activación: es la única ventana para avisar un timer que venza
            # con el asistente "dormido" (sin sesión de conversación abierta).
            despertador.escuchar(en_cada_bloque=lambda score: hablar_avisos_pendientes(voz))
            print("👂 ¡Te escucho!")
            audio.reproducir_blip()

            en_sesion = True
            while en_sesion:
                grabacion = escucha.grabar()
                en_sesion = procesar_turno(grabacion, transcriptor, cerebro, voz)
                hablar_avisos_pendientes(voz)
            print("💤 Sesión terminada. Esperando 'Hey Jarvis' de nuevo...\n")
    except KeyboardInterrupt:
        print("\nHasta luego.")


def loop_push_to_talk(transcriptor: Transcriptor, cerebro: Cerebro, voz: Voz) -> None:
    """Loop clásico: Enter para hablar, Enter para terminar."""
    voz.decir("Hola, te escucho.")
    print("\n💡 Presiona Enter para hablar; Enter de nuevo para terminar de hablar.")
    print("   Di 'adiós' para salir, o presiona Ctrl+C.\n")

    while True:
        hablar_avisos_pendientes(voz)
        try:
            input("⏎  Enter para hablar...")
            grabacion = audio.grabar_push_to_talk()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        if not procesar_turno(grabacion, transcriptor, cerebro, voz):
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Asistente de voz personal")
    parser.add_argument(
        "--teclado",
        action="store_true",
        help="Usar modo push-to-talk clásico (Enter para hablar) en vez de manos libres.",
    )
    args = parser.parse_args()

    # Cargamos todo UNA vez al inicio (los modelos tardan unos segundos en
    # cargar; hacerlo en cada turno sería un desperdicio).
    print("Iniciando asistente...")
    # El catálogo de apps instaladas (Get-StartApps) tarda ~1-2 segundos:
    # se lee en un hilo aparte mientras cargan Whisper y Piper, así el
    # primer "abrí X" ya lo encuentra listo.
    precargar_catalogo_apps()
    transcriptor = Transcriptor("small")
    cerebro = Cerebro()
    voz = Voz()  # es_AR-daniela-high

    if args.teclado:
        loop_push_to_talk(transcriptor, cerebro, voz)
    else:
        loop_manos_libres(transcriptor, cerebro, voz)


if __name__ == "__main__":
    main()
