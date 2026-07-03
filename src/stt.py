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
- hotwords desde vocabulario.txt: Whisper "españoliza" nombres propios que
  no conoce ("Duki" → "duque"). Las hotwords sesgan la decodificación hacia
  esas palabras cuando el sonido se les parece, sin inventarlas si no se
  dijeron. OJO: en faster-whisper, hotwords se IGNORA si también se pasa
  initial_prompt — por eso usamos solo hotwords.
"""

from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

# Carpeta del proyecto (un nivel arriba de src/)
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_MODELOS = RAIZ / "models"
ARCHIVO_VOCABULARIO = RAIZ / "vocabulario.txt"

# Filtro de confianza: Whisper a veces "alucina" texto en audio dudoso
# (típico: "Gracias por ver el video"). Cada segmento trae dos métricas:
# - no_speech_prob: probabilidad (0-1) de que en realidad NO haya voz.
# - avg_logprob: confianza media de las palabras elegidas (0 = seguro,
#   más negativo = menos seguro; -1.0 ya es bastante dudoso).
# Descartamos solo si AMBAS son malas a la vez (umbral conservador: es
# preferible dejar pasar un segmento dudoso que borrar palabras reales).
UMBRAL_NO_VOZ = 0.6
UMBRAL_LOGPROB = -1.0


def cargar_vocabulario() -> str | None:
    """Lee vocabulario.txt (una palabra por línea, # comenta) y arma las hotwords.

    Devuelve None si el archivo no existe o está vacío: así transcribir()
    simplemente no pasa hotwords y todo sigue funcionando como antes.
    """
    if not ARCHIVO_VOCABULARIO.exists():
        return None
    palabras = []
    for linea in ARCHIVO_VOCABULARIO.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            palabras.append(linea)
    return " ".join(palabras) if palabras else None


class Transcriptor:
    def __init__(self, modelo: str = "small"):
        """Carga el modelo Whisper. Tamaños: tiny, base, small, medium, large-v3-turbo."""
        print(f"Cargando modelo Whisper '{modelo}' (la primera vez se descarga)...")
        self.model = WhisperModel(
            modelo,
            device="cpu",
            compute_type="int8",
            download_root=str(CARPETA_MODELOS),
        )
        self.hotwords = cargar_vocabulario()
        if self.hotwords:
            print(f"Vocabulario personalizado cargado: {self.hotwords}")
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
            hotwords=self.hotwords,  # nombres propios frecuentes (vocabulario.txt)
            # Sin esto, cada segmento se decodifica usando el texto del anterior
            # como contexto: un error temprano contamina el resto. Nuestras
            # frases duran <15s (un solo segmento casi siempre), no lo necesitamos.
            condition_on_previous_text=False,
        )
        partes = []
        for s in segmentos:
            # Descarta alucinaciones: "no parece voz" Y "poca confianza" a la vez.
            if s.no_speech_prob > UMBRAL_NO_VOZ and s.avg_logprob < UMBRAL_LOGPROB:
                continue
            partes.append(s.text.strip())
        return " ".join(partes).strip()
