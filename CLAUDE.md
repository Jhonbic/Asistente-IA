# Asistente de voz personal (Windows, Python)

Asistente de voz local: micrófono → Whisper (STT local) → NVIDIA NIM (LLM en nube) →
Piper (TTS local). La v1 (conversación por voz) está TERMINADA y funciona.

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
  (chat LLM), `test_capa4.py` / `test_voces_mujer.py` (voces TTS).
- Ejecutar siempre desde la raíz del proyecto.

## Arquitectura (src/)

- `audio.py` — captura/reproducción, 16kHz mono float32, push-to-talk
- `stt.py` — Whisper `small`, CPU int8, modelos en `models/`
- `llm.py` — NIM vía SDK openai; modelo `qwen/qwen3-next-80b-a3b-instruct`; key en `.env`
  (`NVIDIA_API_KEY`); system prompt exige respuestas breves SIN markdown (se leen en voz alta)
- `tts.py` — Piper, voz `es_AR-daniela-high`, voces en `models/piper/`
- `asistente.py` — loop conversacional (une todo)

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

## Futuro acordado (no implementar sin que lo pida)

Etapa 2: function calling en `llm.py` + módulo de herramientas para ejecutar comandos y
abrir apps. El diseño modular ya lo contempla; audio/STT/TTS no se tocan.
