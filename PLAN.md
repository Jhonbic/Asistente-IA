# Plan: Asistente de Voz Personal (Windows, Python)

> Documento de referencia del proyecto. Al retomar en una sesión futura, leer este archivo
> primero: contiene la arquitectura, el estado de avance y las decisiones tomadas.

## Contexto

- **SO:** Windows 11
- **Hardware:** AMD Ryzen 5 6600H, 16GB RAM, NVIDIA RTX 3050 Laptop (4GB VRAM)
- **Lenguaje:** Python (el usuario está aprendiendo → explicar decisiones técnicas con claridad)
- **Objetivo v1:** escuchar voz → responder con voz
- **Objetivo futuro (NO implementar aún):** ejecutar comandos, abrir apps, integración con el sistema
- **Regla de trabajo:** cada capa se prueba aislada antes de conectarla. Avanzar capa por capa
  solo con aprobación del usuario.

## Arquitectura

```
🎤 Micrófono
   │
[Capa 1] Captura de audio (sounddevice)
   │  audio crudo (numpy array, 16kHz mono float32)
[Capa 2] STT — faster-whisper (local)
   │  texto transcrito
[Capa 3] LLM — NVIDIA NIM (nube, gratis, ~40 req/min)
   │  respuesta en texto
[Capa 4] TTS — Piper (local)
   │  audio sintetizado
[Capa 5] Loop conversacional (une todo + historial)
   │
🔊 Altavoces
```

## Estado de avance

- [x] Capa 0 — Preparación del entorno (completada 2026-07-01)
- [x] Capa 1 — Captura de audio (completada 2026-07-01: `src/audio.py`, probada con voz real)
- [x] Capa 2 — STT (completada 2026-07-01: `src/stt.py`, modelo elegido: `small`)
- [x] Capa 3 — LLM (completada 2026-07-01: `src/llm.py`, modelo `qwen/qwen3-next-80b-a3b-instruct`)
- [x] Capa 4 — TTS (completada 2026-07-01: `src/tts.py`, voz elegida: `es_AR-daniela-high`)
- [x] Capa 5 — Loop conversacional (completada 2026-07-01: `src/asistente.py`)

---

## Capa 0 — Preparación del entorno

**Qué hace:** deja la PC lista antes de tocar audio.

- Entorno virtual (`venv`) para aislar dependencias del Python global.
- Python ideal: 3.10–3.12 (algunas librerías de audio no soportan bien 3.13+).
- Estructura: `src/`, `models/` (modelos de voz), `config/`.
- **Prueba aislada:** activar venv y correr `python --version`.

## Capa 1 — Captura de audio

**Qué hace:** graba del micrófono en el formato que Whisper espera (mono, 16kHz, float32).

- **Librerías:** `sounddevice` + `numpy`. (Descartado `pyaudio`: instalación problemática en Windows.)
- **Modo de activación v1:** push-to-talk (Enter para hablar). VAD / palabra de activación → futuro.
- **Prueba aislada:** script que graba 5s, guarda `.wav`, se escucha y verifica. Listar
  dispositivos de audio para elegir el micrófono correcto.

## Capa 2 — STT con faster-whisper

**Qué hace:** convierte el audio en texto en español.

- **Librería:** `faster-whisper` (CTranslate2, ~4x más rápido que Whisper original).
- **Decisión CPU vs GPU:** empezar en **CPU con int8** (modelo `small`). La GPU (RTX 3050 4GB)
  requiere cuBLAS + cuDNN en Windows (frágil) — queda como optimización posterior; el cambio
  es solo de parámetros (`device="cuda"`, `compute_type`).
- **Prueba aislada:** transcribir el `.wav` de la Capa 1 y comparar. Probar `base` vs `small`.
- **Decisión pendiente del usuario:** tamaño del modelo (`base` / `small` recomendado / `medium`).

## Capa 3 — LLM con NVIDIA NIM

**Qué hace:** envía el texto del usuario a la API de NVIDIA y devuelve la respuesta.

- **Librería:** SDK `openai` con `base_url = https://integrate.api.nvidia.com/v1`.
- **API key:** en [build.nvidia.com](https://build.nvidia.com) → cualquier modelo → "Get API Key".
  La key (`nvapi-...`) va en un archivo `.env`, NUNCA en el código. Agregar `.env` a `.gitignore`.
- **Modelo recomendado:** `meta/llama-3.3-70b-instruct` (buen español natural). Alternativa
  rápida: `meta/llama-3.1-8b-instruct`. Verificar catálogo vigente al llegar a esta capa.
- **Rate limit:** ~40 req/min. Manejar error 429 con gracia.
- **Prueba aislada:** chat por texto en terminal, sin audio.
- **Decisiones pendientes del usuario:** crear key; elegir modelo; personalidad del asistente
  (system prompt: nombre, tono).

## Capa 4 — TTS con Piper

**Qué hace:** convierte la respuesta en audio y la reproduce.

- **Librerías:** `piper-tts` + `sounddevice`. Corre en CPU en tiempo real (GPU libre).
- **Voces candidatas en español** (descarga única ~60MB a `models/`):
  `es_ES-davefx-medium`, `es_ES-sharvard-medium`, `es_MX-claude-high`, `es_MX-ald-medium`.
- **Riesgo:** `piper-tts` en Windows a veces falla al instalar según versión de Python.
  Plan B: binario standalone de Piper invocado desde Python.
- **Prueba aislada:** reproducir una frase fija con 2–3 voces y elegir.
- **Decisión pendiente del usuario:** la voz.

## Capa 5 — Loop conversacional

**Qué hace:** ciclo escuchar → transcribir → pensar → hablar → repetir.

- Historial de conversación con límite de turnos.
- Comando de salida por voz ("adiós", "termina").
- Manejo de errores por capa (si NIM falla, el asistente lo dice por voz; silencio → re-escuchar).
- **Diseño modular:** cada capa como clase/módulo propio. El objetivo futuro (comandos, apps)
  se implementará vía *function calling* en la Capa 3 sin tocar audio/STT/TTS.
- **Prueba:** conversación de varios turnos verificando memoria de contexto.

---

## Riesgos y decisiones

| # | Qué | Estado |
|---|---|---|
| 1 | cuDNN/GPU en Windows es frágil | Mitigado: empezar en CPU |
| 2 | Modelo Whisper (base/small/medium) | Decide usuario en Capa 2 |
| 3 | Cuenta y API key NVIDIA | Usuario, antes de Capa 3 |
| 4 | Modelo LLM del catálogo NIM | Usuario (recomendado: llama-3.3-70b-instruct) |
| 5 | Voz de Piper | Usuario, en Capa 4 |
| 6 | Push-to-talk vs VAD | Push-to-talk en v1 |
| 7 | Latencia total ~3–6s en v1 | Aceptable; streaming como optimización futura |
| 8 | Privacidad: la voz nunca sale de la PC; solo el texto viaja a NVIDIA | Informado |

## Decisiones tomadas

- 2026-07-01: Plan aprobado por el usuario ("luz verde").
- 2026-07-01: Capa 0 completada. Python 3.13.5 (única versión instalada) — verificado con
  `pip install --dry-run` que TODAS las dependencias del proyecto tienen wheels para 3.13
  en Windows, incluida `piper-tts` 1.4.2 (riesgo de instalación de Piper descartado).
  Creados: `venv/`, `src/`, `models/`, `config/`, `.gitignore`, `requirements.txt`.
  Las dependencias aún NO están instaladas; se instalan al empezar cada capa.
- 2026-07-01: Capa 1 completada (`src/audio.py` + `src/test_capa1.py`). Micrófono por defecto:
  array Realtek integrado. Ojo: la salida por defecto de Windows es el HDMI ("Google TV").
- 2026-07-01: Capa 2 implementada (`src/stt.py` + `src/test_capa2.py`). Benchmark en CPU int8
  con audio real de 5s: `base` = 0.70s, `small` = 2.15s; ambos transcribieron bien.
  Falta que el usuario elija el modelo por defecto.
- 2026-07-01: Gotcha de Windows: la consola usa cp1252 → los emojis en `print()` crashean.
  Solución: `sys.stdout.reconfigure(encoding="utf-8")` al inicio de los scripts ejecutables.
- 2026-07-01: Usuario eligió Whisper `small` como modelo STT por defecto.
- 2026-07-01: Capa 3 implementada (`src/llm.py` + `src/test_capa3.py` + `.env.example`).
  Modelo: `meta/llama-3.3-70b-instruct`. El system prompt exige respuestas breves y SIN
  markdown porque se leen en voz alta. Historial limitado a 10 intercambios.
  PENDIENTE: el usuario debe crear `.env` con su NVIDIA_API_KEY y probar el chat.
- 2026-07-01: Capa 3 CERRADA tras depuración. Hallazgos importantes:
  - `meta/llama-3.3-70b-instruct` (la recomendación original) está SATURADO en el tier
    gratuito de NIM: 148s de latencia y timeouts. No usar.
  - Se agregó `timeout=45.0` al cliente OpenAI — sin timeout, una petición colgada
    bloquea el programa para siempre.
  - Benchmark de 5 candidatos → elegido `qwen/qwen3-next-80b-a3b-instruct`: ~1s de
    latencia, español excelente. Alternativa de respaldo si falla:
    `meta/llama-4-maverick-17b-128e-instruct` (2.8s, también muy bueno).
  - Verificado con test de 2 turnos: la memoria conversacional funciona.
- 2026-07-01: Capa 4 implementada (`src/tts.py` + `src/test_capa4.py`). `piper-tts` 1.4.2
  instaló sin problemas (el plan B del binario standalone no hizo falta). 4 voces
  descargadas en `models/piper/` (davefx, sharvard, ald, claude-high); las 4 sintetizan
  bien a 22050 Hz. Voces nuevas se bajan con:
  `python -m piper.download_voices <nombre> --data-dir models\piper`.
  PENDIENTE: usuario ejecuta `src/test_capa4.py`, escucha y elige la voz por defecto
  (constante `VOZ_POR_DEFECTO` en `src/tts.py`).
- 2026-07-01: Capa 4 CERRADA. El usuario pidió voces femeninas: se descargó
  `es_AR-daniela-high` y se descubrió que `es_ES-sharvard-medium` trae 2 hablantes
  (M=0, F=1) → `Voz` ahora acepta `speaker_id`. Voz elegida: **es_AR-daniela-high**.
- 2026-07-01: Capa 5 completada (`src/asistente.py`). Push-to-talk (Enter/Enter), salida
  por voz ("adiós"/"termina" en frases de ≤4 palabras), filtro de silencio (pico < 0.01),
  errores del LLM anunciados por voz sin crashear. Smoke test de la cadena completa
  wav→STT→LLM→TTS: OK. Latencia estimada por turno (modelos ya cargados): ~4-5s.
  **v1 TERMINADA.** Siguiente etapa (futuro): function calling en la Capa 3 para
  ejecutar comandos y abrir apps, sin tocar las demás capas.
