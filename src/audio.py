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
