"""Fase A — Despertador: detecta la palabra de activación por el micrófono.

Usa openWakeWord, que corre 100% local (no manda audio a ningún lado) con un
modelo preentrenado ("hey_jarvis") sobre ONNX Runtime. Internamente convierte
bloques de 80ms de audio en un puntaje 0-1: cuanto más alto, más seguro está
de haber escuchado la palabra.
"""

import sounddevice as sd
from openwakeword.model import Model
from openwakeword.utils import download_models

SAMPLE_RATE = 16_000
CHANNELS = 1
TAMANO_BLOQUE = 1280  # 80ms a 16kHz: el tamaño de bloque recomendado por openWakeWord

PALABRA_ACTIVACION = "hey_jarvis"
UMBRAL_DETECCION = 0.1  # calibrado 2026-07-02: con 0.35 seguía sin detectar
# la mayoría de los intentos (0.05-0.41), solo cruzaba marcando mucho la "S"
# final ("Jarviss"). PENDIENTE DE VALIDAR: a 0.1 el riesgo es el opuesto —
# silencio/habla normal ya rondaba 0.05-0.09 en pruebas previas, muy cerca de
# este umbral. Falta el test de falsos positivos (TV/música de fondo varios
# minutos, ver test_despertador.py) antes de dar por cerrado este módulo.


class Despertador:
    """Escucha el micrófono en vivo y detecta la palabra de activación."""

    def __init__(self, palabra: str = PALABRA_ACTIVACION, umbral: float = UMBRAL_DETECCION):
        print(f"Cargando modelo de palabra de activación '{palabra}' "
              "(la primera vez se descarga, ~2MB)...")
        # download_models guarda los archivos dentro del propio paquete
        # openwakeword (no se re-descargan si ya existen); igual que
        # faster-whisper/Piper, la descarga ocurre una sola vez.
        download_models(model_names=[palabra])
        self.model = Model(wakeword_models=[palabra], inference_framework="onnx")
        # El nombre interno del modelo puede diferir del argumento (ej. incluye
        # versión); lo tomamos del diccionario de modelos cargados en vez de
        # asumirlo, para no hardcodear "hey_jarvis_v0.1".
        self.nombre_modelo = next(iter(self.model.models.keys()))
        self.umbral = umbral
        print("Despertador listo.")

    def escuchar(self, en_cada_bloque=None) -> float:
        """Bloquea hasta detectar la palabra de activación.

        Devuelve el puntaje (score) con el que se detectó.

        en_cada_bloque: función opcional que recibe el score de cada bloque de
        80ms mientras espera; útil para depurar/calibrar el umbral en vivo
        (ver test_despertador.py).
        """
        # Limpiamos los buffers internos: si venimos de una detección anterior
        # o de un turno de conversación, no queremos arrastrar contexto viejo.
        self.model.reset()
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",  # openWakeWord espera PCM de 16 bits, no float32
            blocksize=TAMANO_BLOQUE,
        ) as stream:
            while True:
                bloque, _desbordado = stream.read(TAMANO_BLOQUE)
                predicciones = self.model.predict(bloque.flatten())
                score = float(predicciones[self.nombre_modelo])
                if en_cada_bloque:
                    en_cada_bloque(score)
                if score > self.umbral:
                    return score
