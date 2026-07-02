"""Capa 4 — TTS (Text-To-Speech) con Piper.

Piper es un sintetizador de voz neuronal que corre local en CPU en tiempo
real, así que la GPU queda libre. Cada voz es un archivo .onnx (~60MB) más
su .onnx.json de configuración, descargados en models/piper/.

Piper genera el audio en "chunks" (trozos) a medida que sintetiza; los
juntamos y los reproducimos con sounddevice (el mismo de la Capa 1).
"""

from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_VOCES = RAIZ / "models" / "piper"

# Elegida por el usuario tras la audición (2026-07-01).
VOZ_POR_DEFECTO = "es_AR-daniela-high"


class Voz:
    def __init__(self, nombre: str = VOZ_POR_DEFECTO, speaker_id: int | None = None):
        """Carga una voz de Piper desde models/piper/.

        speaker_id: algunos modelos traen varios hablantes (p. ej.
        es_ES-sharvard-medium tiene M=0 y F=1). Para modelos de un solo
        hablante se deja en None.
        """
        ruta = CARPETA_VOCES / f"{nombre}.onnx"
        if not ruta.exists():
            disponibles = [p.stem for p in CARPETA_VOCES.glob("*.onnx")]
            raise FileNotFoundError(
                f"No existe la voz '{nombre}'. Disponibles: {disponibles}. "
                f"Descarga más con: python -m piper.download_voices <nombre> "
                f"--data-dir models\\piper"
            )
        self.voice = PiperVoice.load(str(ruta))
        # Cada voz trae su propia frecuencia de muestreo (suele ser 22050 Hz).
        self.sample_rate = self.voice.config.sample_rate
        self.config = (
            SynthesisConfig(speaker_id=speaker_id) if speaker_id is not None else None
        )

    def sintetizar(self, texto: str) -> np.ndarray:
        """Convierte texto en audio (float32) sin reproducirlo."""
        partes = [
            chunk.audio_float_array
            for chunk in self.voice.synthesize(texto, syn_config=self.config)
        ]
        if not partes:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(partes)

    def decir(self, texto: str) -> None:
        """Sintetiza y reproduce el texto por los altavoces."""
        audio = self.sintetizar(texto)
        sd.play(audio, samplerate=self.sample_rate)
        sd.wait()
