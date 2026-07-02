# Asistente de voz personal (Windows, Python)

Asistente de voz local: micrófono → Whisper (STT local) → NVIDIA NIM (LLM en nube) →
Piper (TTS local). La v1 (conversación por voz) está TERMINADA y funciona.

Fase A / v2 (manos libres — wake word + VAD) TERMINADA y funciona (confirmado por el
usuario 2026-07-02). Tras un solo "Hey Jarvis" se abre una sesión con turnos seguidos
sin repetir la palabra; "adiós" cierra la sesión (no el programa) y vuelve a esperar
"Hey Jarvis". Siguiente fase (no empezar sin que se pida): Fase B (function calling +
herramientas), ver `PLAN.md`.

**Lee `PLAN.md` antes de trabajar**: contiene la arquitectura, el estado por capas y todas
las decisiones tomadas con su porqué. Actualízalo cuando se tomen decisiones nuevas.

## Contexto del usuario

- Está aprendiendo Python: explicar decisiones técnicas con claridad, priorizar
  aprendizaje sobre atajos. Código y comentarios en español.
- Avanzar por fases y esperar su aprobación antes de cada fase nueva.
- Hardware: Ryzen 5 6600H, 16GB RAM, RTX 3050 4GB. Todo lo pesado corre en CPU a propósito
  (evitar la fricción de cuDNN en Windows).

## Cómo ejecutar

- Python del proyecto: `venv\Scripts\python.exe` (venv sobre Python 3.13). No instalar
  fuera del venv.
- Asistente completo: `venv\Scripts\python.exe src\asistente.py`
- Pruebas por capa: `src\test_capa1.py` (audio), `test_capa2.py` (STT), `test_capa3.py`
  (chat LLM), `test_capa4.py` / `test_voces_mujer.py` (voces TTS), `test_despertador.py`
  (wake word), `test_vad.py` (corte automático de fin de frase).
- Ejecutar siempre desde la raíz del proyecto.

## Arquitectura (src/)

- `audio.py` — captura/reproducción, 16kHz mono float32, push-to-talk
- `stt.py` — Whisper `small`, CPU int8, modelos en `models/`
- `llm.py` — NIM vía SDK openai; modelo `qwen/qwen3-next-80b-a3b-instruct`; key en `.env`
  (`NVIDIA_API_KEY`); system prompt exige respuestas breves SIN markdown (se leen en voz alta)
- `tts.py` — Piper, voz `es_AR-daniela-high`, voces en `models/piper/`
- `despertador.py` — Fase A: wake word "hey_jarvis" con openWakeWord (ONNX), clase
  `Despertador`, `UMBRAL_DETECCION = 0.1` (calibrado con el micrófono real del usuario)
- `vad.py` — Fase A: corte automático de fin de frase con Silero VAD (ONNX, reutiliza el
  modelo que ya descarga openWakeWord — sin `torch`), clase `EscuchaConVAD`
- `asistente.py` — loop conversacional (une todo); aún en modo push-to-talk, pendiente
  adaptar a manos libres

## Gotchas conocidos

- Consola Windows = cp1252: todo script ejecutable necesita
  `sys.stdout.reconfigure(encoding="utf-8")` antes de imprimir emojis/acentos.
- Cliente OpenAI SIEMPRE con `timeout` (sin él, una petición colgada congela todo).
- `meta/llama-3.3-70b-instruct` está saturado en el tier gratuito de NIM: no usarlo.
  Respaldo si Qwen falla: `meta/llama-4-maverick-17b-128e-instruct`.
- La salida de audio por defecto de Windows puede ser el HDMI ("Google TV"), no los
  altavoces de la laptop.
- Voces Piper nuevas: `python -m piper.download_voices <nombre> --data-dir models\piper`.
  Algunos modelos traen varios hablantes (`Voz(..., speaker_id=N)`).
- Clips cortos con `sd.play()` + `sd.wait()` en Windows: `wait()` retorna cuando PortAudio
  ENTREGA las muestras, no cuando suenan; al cerrarse el stream se descartan los últimos
  ~0.2-0.5s que el mezclador aún tenía en cola. Un clip de 0.15s se pierde ENTERO (sin
  error). Solución: rellenar con silencio al final (ver `RELLENO_BLIP` en `audio.py`).
  Con audios largos (voz de Piper) el efecto es inaudible.

## Futuro acordado (no implementar sin que lo pida)

Etapa 2: function calling en `llm.py` + módulo de herramientas para ejecutar comandos y
abrir apps. El diseño modular ya lo contempla; audio/STT/TTS no se tocan.
