"""Capa 1 — Captura y reproducción de audio.

El audio digital es una secuencia de números ("muestras") por segundo.
Whisper fue entrenado con audio mono a 16.000 Hz en formato float32
(valores entre -1.0 y 1.0), así que grabamos directamente en ese formato
para no tener que convertir nada después.
"""

import queue

import numpy as np
import sounddevice as sd

# Frecuencia de muestreo que espera Whisper: 16.000 muestras por segundo.
SAMPLE_RATE = 16_000
CHANNELS = 1  # mono


def listar_dispositivos() -> None:
    """Muestra todos los dispositivos de audio (micrófonos y salidas).

    El símbolo '>' marca la entrada por defecto y '<' la salida por defecto.
    """
    print(sd.query_devices())


def grabar_fijo(segundos: float) -> np.ndarray:
    """Graba una duración fija desde el micrófono por defecto.

    Útil para pruebas. Devuelve un array float32 mono a 16kHz.
    """
    print(f"🎤 Grabando {segundos} segundos... ¡habla ahora!")
    audio = sd.rec(
        int(segundos * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()  # bloquea hasta que termine la grabación
    print("✅ Grabación terminada.")
    return audio.flatten()  # de forma (N, 1) a forma (N,)


def grabar_push_to_talk() -> np.ndarray:
    """Graba hasta que el usuario presione Enter (modo push-to-talk).

    Usa un stream con callback: sounddevice nos entrega el audio en
    bloques pequeños a medida que llega, y los vamos acumulando en una
    cola hasta que el usuario decide parar.
    """
    bloques: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(f"⚠️  Aviso de audio: {status}")
        bloques.put(indata.copy())

    print("🎤 Grabando... presiona Enter para terminar.")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
    ):
        input()  # espera el Enter mientras el stream sigue grabando

    partes = []
    while not bloques.empty():
        partes.append(bloques.get())
    if not partes:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(partes).flatten()


def reproducir(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Reproduce un array de audio por la salida por defecto."""
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


SAMPLE_RATE_BLIP = 44_100  # estándar universal de reproducción; no tiene que
# ver con SAMPLE_RATE (16kHz), que es un requisito de Whisper para GRABAR voz,
# no de los dispositivos de salida para REPRODUCIR. Un dispositivo WASAPI de
# este equipo rechazó 16kHz para reproducción ("Invalid sample rate").


def generar_blip(frecuencia: float = 880.0, duracion: float = 0.15) -> np.ndarray:
    """Genera un pitido corto (seno) para confirmar que el despertador escuchó.

    No usamos un archivo de audio externo: un seno generado con numpy pesa
    cero bytes en disco y es instantáneo. Se aplica un fundido de entrada y
    salida (fade in/out) de unos milisegundos para evitar el "click" que se
    escucha si el sonido empieza o termina de golpe en amplitud distinta de 0.
    """
    n_muestras = int(duracion * SAMPLE_RATE_BLIP)
    t = np.linspace(0, duracion, n_muestras, endpoint=False)
    onda = np.sin(2 * np.pi * frecuencia * t).astype(np.float32)

    n_fundido = max(1, int(0.01 * SAMPLE_RATE_BLIP))  # 10ms de fundido
    fundido = np.linspace(0, 1, n_fundido, dtype=np.float32)
    onda[:n_fundido] *= fundido
    onda[-n_fundido:] *= fundido[::-1]

    return onda * 0.3  # volumen moderado, no al máximo


# En Windows, el mezclador añade ~0.2-0.5s de latencia entre que PortAudio
# "entrega" el audio y que suena de verdad. sd.wait() retorna al terminar la
# entrega (no la reproducción), y al cerrarse el stream se descarta lo que
# quedaba en cola: un clip de 0.15s se perdía ENTERO. El relleno de silencio
# al final hace de cola sacrificable para que el tono sí llegue al hardware.
RELLENO_BLIP = 0.5  # segundos de silencio tras el tono


def reproducir_blip() -> None:
    """Reproduce el pitido corto de confirmación."""
    blip = generar_blip()
    silencio = np.zeros(int(RELLENO_BLIP * SAMPLE_RATE_BLIP), dtype=np.float32)
    reproducir(np.concatenate([blip, silencio]), sample_rate=SAMPLE_RATE_BLIP)


def guardar_wav(audio: np.ndarray, ruta: str, sample_rate: int = SAMPLE_RATE) -> None:
    """Guarda el audio como .wav de 16 bits (formato estándar).

    Los WAV clásicos usan enteros de 16 bits, así que convertimos
    nuestros float32 (-1.0 a 1.0) multiplicando por 32767.
    """
    import wave

    enteros = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(ruta, "wb") as f:
        f.setnchannels(CHANNELS)
        f.setsampwidth(2)  # 2 bytes = 16 bits
        f.setframerate(sample_rate)
        f.writeframes(enteros.tobytes())
