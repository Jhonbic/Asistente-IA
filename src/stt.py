"""Capa 2 — STT (Speech-To-Text) con faster-whisper.

Whisper es el modelo de reconocimiento de voz de OpenAI; faster-whisper es
una reimplementación ~4x más rápida. Corre 100% local: tu voz nunca sale
de esta PC.

Decisiones (ver PLAN.md):
- device="cpu" + compute_type="int8": los pesos del modelo se comprimen a
  enteros de 8 bits → menos RAM y más velocidad, con pérdida de calidad
  mínima. Evitamos la fricción de instalar cuBLAS/cuDNN para la GPU;
  si algún día queremos GPU, basta cambiar device="cuda".
- El modelo se descarga una sola vez a models/ (~145MB base, ~480MB small).
"""

from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

# Carpeta del proyecto (un nivel arriba de src/)
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_MODELOS = RAIZ / "models"


class Transcriptor:
    def __init__(self, modelo: str = "small"):
        """Carga el modelo Whisper. Tamaños: tiny, base, small, medium."""
        print(f"Cargando modelo Whisper '{modelo}' (la primera vez se descarga)...")
        self.model = WhisperModel(
            modelo,
            device="cpu",
            compute_type="int8",
            download_root=str(CARPETA_MODELOS),
        )
        print("Modelo listo.")

    def transcribir(self, audio: np.ndarray) -> str:
        """Convierte audio (float32 mono 16kHz) en texto en español.

        Whisper devuelve el texto en "segmentos" (trozos de ~30s) de forma
        perezosa: la transcripción real ocurre al recorrerlos.
        """
        segmentos, _info = self.model.transcribe(
            audio,
            language="es",       # fijamos español: más rápido y sin errores de detección
            beam_size=5,         # explora 5 hipótesis en paralelo (calidad vs velocidad)
            vad_filter=True,     # recorta silencios antes de transcribir
        )
        return " ".join(s.text.strip() for s in segmentos).strip()
