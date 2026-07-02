"""Fase A — VAD: graba después del despertar y corta sola al detectar silencio.

VAD = Voice Activity Detection (detección de actividad de voz). A diferencia
del filtro de silencio por volumen que ya usa `asistente.py` (pico < 0.01),
un modelo de VAD analiza el audio y estima la probabilidad de que haya voz
humana en cada bloque, así que no se deja engañar por ruido de fondo bajo
ni corta de más con una voz suave.

Reutiliza el modelo Silero VAD (ONNX) que `despertador.py` ya descarga vía
openWakeWord — sin instalar `torch` ni bajar nada nuevo (ver PLAN.md, Fase A:
"silero-vad (ONNX, sin torch)").
"""

import numpy as np
import sounddevice as sd
from openwakeword.vad import VAD

SAMPLE_RATE = 16_000
CHANNELS = 1
TAMANO_BLOQUE = 480  # 30ms a 16kHz: tamaño de frame recomendado por Silero VAD

UMBRAL_VOZ = 0.5  # score de Silero VAD por encima del cual se considera "hay voz"
SILENCIO_PARA_CORTAR = 1.0  # segundos de silencio seguido para dar la frase por terminada
DURACION_MAXIMA = 15.0  # tope de seguridad para no grabar indefinidamente


class EscuchaConVAD:
    """Graba desde el micrófono y corta sola cuando el usuario deja de hablar."""

    def __init__(
        self,
        umbral_voz: float = UMBRAL_VOZ,
        silencio_para_cortar: float = SILENCIO_PARA_CORTAR,
        duracion_maxima: float = DURACION_MAXIMA,
    ):
        self.vad = VAD()
        self.umbral_voz = umbral_voz
        self.bloques_de_silencio_para_cortar = int(
            silencio_para_cortar * SAMPLE_RATE / TAMANO_BLOQUE
        )
        self.bloques_maximos = int(duracion_maxima * SAMPLE_RATE / TAMANO_BLOQUE)

    def grabar(self) -> np.ndarray:
        """Graba hasta detectar silencio sostenido (o llegar al tope máximo).

        Devuelve el audio como float32 mono 16kHz (-1.0 a 1.0), el mismo
        formato que espera `Transcriptor.transcribir()`.
        """
        self.vad.reset_states()
        bloques = []
        bloques_silencio_seguidos = 0
        empezo_a_hablar = False  # no contamos silencio inicial (antes de hablar) como corte

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",  # Silero VAD espera PCM de 16 bits, no float32
            blocksize=TAMANO_BLOQUE,
        ) as stream:
            for _ in range(self.bloques_maximos):
                bloque, _desbordado = stream.read(TAMANO_BLOQUE)
                bloque = bloque.flatten()
                bloques.append(bloque)

                score = self.vad.predict(bloque, frame_size=TAMANO_BLOQUE)
                hay_voz = score > self.umbral_voz

                if hay_voz:
                    empezo_a_hablar = True
                    bloques_silencio_seguidos = 0
                elif empezo_a_hablar:
                    bloques_silencio_seguidos += 1
                    if bloques_silencio_seguidos >= self.bloques_de_silencio_para_cortar:
                        break

        if not bloques:
            return np.zeros(0, dtype=np.float32)
        audio_int16 = np.concatenate(bloques)
        return audio_int16.astype(np.float32) / 32767.0
