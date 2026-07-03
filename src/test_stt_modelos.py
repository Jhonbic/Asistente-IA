"""Benchmark de modelos Whisper con tu voz real.

Compara 'small' (el actual), 'medium' y 'large-v3-turbo' transcribiendo
frases grabadas con tu micrófono, con y sin el vocabulario personalizado
(vocabulario.txt), midiendo el tiempo de cada transcripción. Con la tabla
final decides si vale la pena pagar más latencia por más precisión.

Las grabaciones se guardan en pruebas/ (raíz del proyecto): si vuelves a
correr el script puedes reutilizarlas y comparar sin regrabar.

OJO: 'medium' (~1.5GB) y 'large-v3-turbo' (~1.6GB) se descargan a models/
la primera vez. El script avisa y pide confirmación antes.

Ejecutar desde la raíz del proyecto:
    venv\\Scripts\\python.exe src\\test_stt_modelos.py
"""

import sys
import time
import wave
from pathlib import Path

import numpy as np

# La consola de Windows usa cp1252 por defecto y no puede imprimir emojis/acentos raros.
sys.stdout.reconfigure(encoding="utf-8")

from audio import guardar_wav
from stt import Transcriptor
from vad import EscuchaConVAD


def cargar_wav(ruta: str) -> np.ndarray:
    """Lee un .wav de 16 bits y lo devuelve como float32 (-1.0 a 1.0).

    (No se importa de test_capa2.py porque ese script corre su benchmark
    al importarlo: todo su código está a nivel de módulo.)
    """
    with wave.open(ruta, "rb") as f:
        datos = f.readframes(f.getnframes())
    return np.frombuffer(datos, dtype=np.int16).astype(np.float32) / 32767.0

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PRUEBAS = RAIZ / "pruebas"

# Frases sugeridas: casos problema reales (nombres propios) + una frase normal.
FRASES = [
    "pon Duki en YouTube",
    "pon una canción de Bizarrap",
    "abre Spotify",
    "qué hora es y cómo va a estar el clima mañana",
]

MODELOS = ["small", "medium", "large-v3-turbo"]


def grabar_frases() -> list[Path]:
    """Graba cada frase con el VAD (corta solo al callarte) y la guarda como .wav."""
    CARPETA_PRUEBAS.mkdir(exist_ok=True)
    escucha = EscuchaConVAD()
    rutas = []
    for i, frase in enumerate(FRASES, start=1):
        ruta = CARPETA_PRUEBAS / f"frase_{i}.wav"
        input(f'\n[{i}/{len(FRASES)}] Pulsa Enter y di: "{frase}"')
        print("🎤 Grabando... (corta sola cuando te calles)")
        audio = escucha.grabar()
        guardar_wav(audio, str(ruta))
        print(f"Guardado: {ruta.name} ({len(audio) / 16000:.1f}s)")
        rutas.append(ruta)
    return rutas


# --- 1. Conseguir las grabaciones (reutilizar o grabar de nuevo) ---

existentes = sorted(CARPETA_PRUEBAS.glob("frase_*.wav"))
if existentes:
    respuesta = input(
        f"Hay {len(existentes)} grabaciones en pruebas\\. ¿Reutilizarlas? [S/n] "
    )
    rutas = existentes if respuesta.strip().lower() != "n" else grabar_frases()
else:
    rutas = grabar_frases()

audios = [(ruta.name, cargar_wav(str(ruta))) for ruta in rutas]

# --- 2. Avisar de las descargas antes de empezar ---

print(
    "\nSe van a probar los modelos: " + ", ".join(MODELOS) + "."
    "\n'medium' (~1.5GB) y 'large-v3-turbo' (~1.6GB) se descargan la primera vez."
)
if input("¿Continuar? [S/n] ").strip().lower() == "n":
    sys.exit(0)

# --- 3. Transcribir cada frase con cada modelo, con y sin vocabulario ---

# resultados[modelo] = lista de (nombre_wav, texto_sin, texto_con, segundos_con)
resultados: dict[str, list[tuple[str, str, str, float]]] = {}

for modelo in MODELOS:
    print(f"\n=== Modelo '{modelo}' ===")
    t = Transcriptor(modelo)
    hotwords = t.hotwords
    filas = []
    for nombre, audio in audios:
        # Sin vocabulario: apagamos las hotwords a mano para comparar su efecto.
        t.hotwords = None
        texto_sin = t.transcribir(audio)

        t.hotwords = hotwords
        inicio = time.perf_counter()
        texto_con = t.transcribir(audio)
        segundos = time.perf_counter() - inicio

        print(f'  {nombre}: "{texto_con}" ({segundos:.1f}s)')
        filas.append((nombre, texto_sin, texto_con, segundos))
    resultados[modelo] = filas
    # Liberamos el modelo antes de cargar el siguiente (medium/turbo usan ~2GB de RAM).
    del t

# --- 4. Tabla final ---

print("\n" + "=" * 70)
print("RESUMEN (compará precisión de los textos vs tiempo por frase)")
print("=" * 70)
for i, (nombre, _audio) in enumerate(audios):
    print(f'\n📌 {nombre} — frase esperada: "{FRASES[i] if i < len(FRASES) else "?"}"')
    for modelo in MODELOS:
        _, texto_sin, texto_con, segundos = resultados[modelo][i]
        print(f"  {modelo:>15} ({segundos:4.1f}s)")
        print(f'{"":>18} sin vocabulario: "{texto_sin}"')
        print(f'{"":>18} con vocabulario: "{texto_con}"')

tiempos = {
    modelo: sum(f[3] for f in filas) / len(filas) for modelo, filas in resultados.items()
}
print("\n⏱️  Tiempo promedio por frase:")
for modelo, prom in tiempos.items():
    print(f"  {modelo:>15}: {prom:.1f}s")
