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

### v1 — Conversación por voz (TERMINADA)

- [x] Capa 0 — Preparación del entorno (completada 2026-07-01)
- [x] Capa 1 — Captura de audio (completada 2026-07-01: `src/audio.py`, probada con voz real)
- [x] Capa 2 — STT (completada 2026-07-01: `src/stt.py`, modelo elegido: `small`)
- [x] Capa 3 — LLM (completada 2026-07-01: `src/llm.py`, modelo `qwen/qwen3-next-80b-a3b-instruct`)
- [x] Capa 4 — TTS (completada 2026-07-01: `src/tts.py`, voz elegida: `es_AR-daniela-high`)
- [x] Capa 5 — Loop conversacional (completada 2026-07-01: `src/asistente.py`)

### Siguientes versiones (plan detallado más abajo, aprobado 2026-07-02)

- [x] Fase A (v2) — Manos libres: wake word + VAD (completada 2026-07-02)
- [x] Fase B (v3) — Herramientas: function calling (completada 2026-07-02)
- [ ] Fase C (v4) — Siempre en segundo plano

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
- 2026-07-02: Plan de las fases A/B/C (v2–v4) definido y aprobado (ver sección siguiente).
  Decisiones del usuario: motor de wake word = **openWakeWord** (gratis, sin cuenta);
  Fase B incluye los 4 grupos de herramientas (apps/webs, timers, sistema, búsqueda e info).
- 2026-07-02: Riesgo de instalación (Fase A) descartado: `openwakeword` y `onnxruntime`
  instalan sin problemas en Python 3.13 (`pip install --dry-run`). Para el VAD se evitó el
  paquete `silero-vad` de PyPI porque arrastra `torch` (~600MB) como dependencia dura;
  en su lugar se usa `openwakeword.vad.VAD`, que ya trae el mismo modelo Silero VAD en
  formato ONNX puro (se descarga junto con el modelo de wake word, sin pasos extra).
- 2026-07-02: Módulo 1 (`despertador.py` + `test_despertador.py`) CERRADO. Modelo
  preentrenado usado: `hey_jarvis` (únicas palabras disponibles sin entrenar un modelo
  propio: `alexa, hey_mycroft, hey_jarvis, hey_rhasspy, timer, weather`; entrenar una
  palabra custom con TTS sintético queda anotado como posible trabajo futuro, no pedido
  aún). Calibración de `UMBRAL_DETECCION` con el micrófono real del usuario: con 0.5 casi
  ninguna detección correcta cruzaba el umbral (scores 0.15–0.47); con 0.35 tampoco
  mejoró demasiado; bajando a **0.1** detecta de forma consistente y, en una prueba de
  varios minutos con TV/música de fondo, no hubo falsos positivos. Valor final:
  `UMBRAL_DETECCION = 0.1`.
- 2026-07-02: Módulo 2 (`vad.py` + `test_vad.py`) CERRADO. Reutiliza el Silero VAD ya
  descargado por `despertador.py`. Prueba con voz real: corta sola ~1s después del
  silencio y la transcripción con Whisper no perdió palabras del final. Parámetros por
  defecto sin cambios: `UMBRAL_VOZ=0.5`, `SILENCIO_PARA_CORTAR=1.0s`,
  `DURACION_MAXIMA=15.0s`.
- 2026-07-02: Módulo 3 (sonido de confirmación / "blip" en `audio.py`) RESUELTO (mismo
  día, ver causa raíz al final de esta entrada). Historial del diagnóstico:
  `audio.generar_blip()` + `audio.reproducir_blip()` están implementados (tono seno con
  fade in/out, sin archivos externos) pero **no se escucha nada** en el equipo del
  usuario, sin ninguna excepción. Diagnóstico y descartes, en orden:
  1. Primer intento reproducía a 16kHz (la frecuencia de Whisper para GRABAR, sin motivo
     para aplicarla a REPRODUCIR un tono). Dispositivo MME por defecto ("Google TV",
     índice 3 en `sd.query_devices()`) lo aceptó sin error pero no sonó.
  2. Se forzó el dispositivo de altavoces por índice (`sd.default.device = (None, 4)`,
     MME "Altavoces (Realtek(R) Audio)") a 16kHz: tampoco sonó, sin error.
  3. Se forzó el dispositivo WASAPI de altavoces (índice 10) a 16kHz: **error explícito**
     `sounddevice.PortAudioError: Invalid sample rate [PaErrorCode -9997]` — confirma que
     16kHz no es válido para reproducción en ese dispositivo/driver.
  4. Se cambió el blip a reproducirse a 44100 Hz (estándar universal), sin forzar
     dispositivo (usa el default del sistema): sigue sin escucharse, sin error.
  - Dato importante: la voz de Piper (`tts.py`, reproduce a ~22050 Hz por el default del
    sistema) **sí se escucha** en este mismo equipo (confirmado en la v1). Es decir, la
    salida de audio en general funciona; el problema es específico del blip generado con
    numpy/sounddevice de forma standalone.
  - Hipótesis no probadas todavía: (a) el volumen del tono (`* 0.3`) o la duración
    (0.15s) son demasiado bajos/cortos para notarse aunque sí esté sonando; (b) mezclador
    de volumen de Windows por app silenciando este proceso de Python específico entre
    llamadas; (c) alguna diferencia entre cómo Piper/`sd.play` deja el stream abierto vs.
    cómo lo abre `audio.reproducir()` en una llamada aislada de una línea (`python -c`).
  - Lista completa de dispositivos de salida disponibles (`sd.query_devices()`), por si
    hace falta probar otro índice: 2 (Asignador Microsoft), 3 (Google TV, default MME),
    4 (Altavoces Realtek, MME), 7 (Asignador Microsoft, DirectSound), 8 (Google TV,
    DirectSound), 9 (Altavoces Realtek, DirectSound), 10 (Altavoces Realtek, WASAPI — no
    acepta 16kHz), 11 (Google TV, WASAPI), 13/20/21/22 (variantes WDM-KS de altavoces),
    26 (Output NVIDIA, WDM-KS).
  - **CAUSA RAÍZ (confirmada con prueba A/B escuchada por el usuario):** en Windows, el
    mezclador añade ~0.2-0.5s de latencia entre que PortAudio "entrega" las muestras al
    driver y que suenan de verdad. `sd.wait()` retorna al terminar la ENTREGA, no la
    reproducción; al retornar, el stream se cierra y descarta lo que quedaba en cola.
    Con la voz de Piper (varios segundos, mismo `sd.play` y mismo dispositivo default)
    solo se pierde una cola inaudible; con un clip de 0.15s se perdía el clip ENTERO.
    Por eso nunca hubo error: el audio sí se "reproducía", pero jamás llegaba al hardware.
  - **ARREGLO:** `reproducir_blip()` añade `RELLENO_BLIP = 0.5` s de silencio tras el
    tono — el silencio hace de cola sacrificable y el tono sí alcanza a sonar. Verificado
    en el equipo del usuario. Hipótesis descartadas: volumen/duración insuficientes,
    mezclador por app, dispositivo default (Piper suena por el mismo "Google TV").

---

# Plan v2 → v4: Fases A, B y C

> Detalle de las siguientes versiones (origen: `VERSIONES.md`). Misma metodología que la
> v1: cada módulo nuevo se prueba aislado con su `test_*.py` antes de conectarse, y no se
> pasa a la fase siguiente sin aprobación del usuario.

Reglas transversales (heredadas de la v1):
- Todo corre en el venv (`venv\Scripts\python.exe`), pesado en CPU, código y comentarios en español.
- Scripts ejecutables llevan `sys.stdout.reconfigure(encoding="utf-8")`.
- Al cerrar cada fase se actualiza este archivo con las decisiones tomadas.

## Fase A — Manos libres (v2): wake word + VAD

**Meta:** hablar sin teclado. Loop: esperar "Hey Jarvis" → sonido de confirmación → grabar
hasta que dejes de hablar → transcribir → responder → volver a esperar.

### Tecnologías

| Necesidad | Elección | Por qué |
|---|---|---|
| Palabra de activación | `openwakeword` (+ `onnxruntime`) | Gratis, sin cuenta, ~1-3% CPU, modelo preentrenado `hey_jarvis` |
| Fin de frase automático | `silero-vad` (ONNX, sin torch) | Estándar de facto, liviano en CPU, detecta silencio real (no solo volumen) |
| Captura continua | `sounddevice.InputStream` | Ya se usa en `audio.py`; se reutiliza el mismo patrón de callback |

Riesgo a verificar al iniciar la fase: que `openwakeword` + `onnxruntime` instalen bien en
Python 3.13 (verificar con `pip install --dry-run` como se hizo en Capa 0). Plan B si falla:
Porcupine (requiere cuenta Picovoice).

### Módulos y prueba aislada

1. **`src/despertador.py`** — clase `Despertador`: stream de micrófono permanente que alimenta
   openWakeWord en bloques de 80ms y dispara un evento al detectar la palabra.
   - *Prueba:* `test_despertador.py` — imprime "¡DESPERTÉ!" + score cada vez que se dice
     "Hey Jarvis"; medir falsos positivos dejándolo escuchar TV/música unos minutos y
     calibrar el umbral (constante `UMBRAL_DETECCION`).
2. **`src/vad.py`** — clase `EscuchaConVAD`: graba tras el despertar y corta sola tras
   ~1s de silencio (silero-vad frame a frame), con tope máximo de ~15s por frase.
   - *Prueba:* `test_vad.py` — hablar, callar, verificar que corta solo; guarda el `.wav`
     y lo transcribe con la Capa 2 para confirmar que no recorta palabras.
3. **`src/audio.py`** (ampliar, no romper) — sonido corto de confirmación ("blip" generado
   con numpy, sin archivos externos). `grabar_push_to_talk()` se conserva intacto como respaldo.
4. **`src/asistente.py`** (adaptado, 2026-07-02) — nuevo loop manos libres por defecto:
   `Despertador.escuchar()` → `audio.reproducir_blip()` → abre una **sesión**: repite
   `EscuchaConVAD.grabar()` → transcribir → responder → hablar mientras el usuario
   no se despida, SIN repetir "Hey Jarvis" entre turnos. Al despedirse ("adiós", etc.)
   la sesión termina y el programa vuelve a esperar la palabra de activación (no
   termina el programa); Ctrl+C es la única forma de cerrar el programa. Flag
   `--teclado` conserva intacto el modo push-to-talk clásico (ahí sí, despedirse
   termina el programa, porque no existe el concepto de "sesión": cada Enter ya es
   una activación manual explícita). La cadena STT→LLM→TTS no se tocó; se extrajo a
   `procesar_turno()` y la comparten ambos modos.
   - Auto-despertarse resuelto por diseño, no con un "pausado" explícito: el loop es
     secuencial (sin hilos), así que `despertador.escuchar()` solo vuelve a llamarse
     DESPUÉS de que `voz.decir()` ya terminó de reproducirse. Mientras el asistente
     habla, nada está leyendo el micrófono para la palabra de activación.
   - No hace falta limpiar estado extra entre sesiones: `despertador.escuchar()` ya
     llama `self.model.reset()` y `escucha.grabar()` ya llama `self.vad.reset_states()`
     al principio de cada llamada.
   - *Prueba de integración:* CONFIRMADA por el usuario (2026-07-02) hablando en vivo —
     varios turnos seguidos tras un solo "Hey Jarvis" sin repetirlo; "adiós" corta la
     sesión sin cerrar el programa; "Hey Jarvis" de nuevo abre una sesión nueva;
     Ctrl+C cierra el programa; no se auto-despierta con su propia voz.

### Criterio de cierre

Detecta la palabra >90% de las veces a distancia normal, corta solo al callar, y no se
auto-despierta con su propia voz. Usuario aprueba y se actualiza este archivo.

**FASE A COMPLETADA (2026-07-02).** Usuario probó el asistente completo en modo manos
libres y confirmó que todo funciona: wake word, VAD, blip y sesión conversacional
continua (sin repetir "Hey Jarvis" por turno, despedida cierra sesión no programa).
Próximo paso, cuando el usuario lo pida: Fase B (function calling + herramientas).

## Fase B — Que haga cosas (v3): function calling + herramientas

**Meta:** el LLM deja de solo conversar: decide cuándo invocar funciones de Python
(herramientas) y responde por voz con el resultado.

### Tecnologías

| Necesidad | Elección | Por qué |
|---|---|---|
| Function calling | API `tools` del SDK openai contra NIM (Qwen3 soporta tool use) | Mismo SDK ya usado en `llm.py`; solo se agrega el parámetro `tools` y el manejo de `tool_calls` |
| Abrir apps/webs | `os.startfile`, `webbrowser`, `subprocess` (stdlib) | Sin dependencias nuevas |
| Timers/recordatorios | `threading.Timer` (stdlib) | Suficiente para v3; enseña concurrencia. El aviso habla por el TTS existente |
| Volumen | `pycaw` | Control nativo del mezclador de Windows |
| Multimedia (play/pausa/siguiente) | `keyboard` (teclas multimedia) | Simple y funciona con cualquier reproductor |
| Batería/CPU/RAM | `psutil` | Estándar |
| Suspender/apagar | `shutdown` vía `subprocess` | Stdlib; **siempre con confirmación por voz previa** |
| Clima | API Open-Meteo (gratis, sin key) + `requests` | Sin registro |
| Búsqueda web | `ddgs` (DuckDuckGo) | Sin API key; devuelve resúmenes que el LLM redacta hablados |

Riesgo a verificar al iniciar la fase: confirmar con una petición real que
`qwen/qwen3-next-80b-a3b-instruct` en NIM devuelve `tool_calls` correctamente
(smoke test antes de construir nada encima). Plan B: `meta/llama-4-maverick-17b-128e-instruct`.

### Módulos y prueba aislada

1. **`src/herramientas.py`** — cada herramienta es una función de Python con su schema
   JSON (nombre, descripción, parámetros) en un registro central `HERRAMIENTAS`. Agregar una
   herramienta nueva = escribir una función + su schema, nada más.
   - *Prueba:* `test_herramientas.py` — ejecuta cada función directamente (sin LLM ni voz)
     y verifica el resultado: abre el navegador, sube el volumen, da el clima, etc.
2. **`src/llm.py`** (ampliar `Cerebro`) — enviar `tools=` en la petición; si la respuesta
   trae `tool_calls`, ejecutar vía despachador, devolver el resultado con `role="tool"` y
   pedir la respuesta final hablada. Bucle con máximo de ~3 llamadas encadenadas por turno
   (evitar loops infinitos). Ampliar el system prompt: anunciar la acción brevemente y
   pedir confirmación para acciones destructivas (apagar/suspender).
   - *Prueba:* `test_capa3b.py` — chat por texto en terminal (sin audio): "pon un timer de
     un minuto", "¿cuánta batería queda?", "abre YouTube" → verificar que elige la
     herramienta correcta, la ejecuta y redacta el resultado hablable.
3. **`src/asistente.py`** (mínimo cambio) — los recordatorios vencidos hablan por el TTS
   aun si saltan fuera de un turno (cola de avisos que el loop revisa).
   - *Prueba de integración:* por voz, un pedido de cada grupo de herramientas.

Orden de implementación dentro de la fase (de simple a complejo, cada una probada antes
de seguir): apps/webs → búsqueda e info → control del sistema → timers/recordatorios
(la más compleja por la concurrencia con el loop de voz).

### Criterio de cierre

Los 4 grupos funcionan por voz, las acciones peligrosas piden confirmación, y una pregunta
normal ("¿cómo estás?") sigue respondiendo sin invocar herramientas innecesarias.

- 2026-07-02: Riesgo de la fase descartado con un smoke test aislado (tool ficticia
  `obtener_clima`): `qwen/qwen3-next-80b-a3b-instruct` en NIM devuelve `tool_calls`
  correctamente.
- 2026-07-02: Módulo 1 (`src/herramientas.py` + `test_herramientas.py`) CERRADO, con luz
  verde del usuario grupo por grupo. Registro central `HERRAMIENTAS` (nombre → función +
  schema JSON) y despachador `ejecutar_herramienta()`.
  - Grupo 1 (apps/webs): `abrir_app`, `abrir_web`, `buscar_en_google` (`os.startfile`/
    `subprocess`, `webbrowser`, sin dependencias nuevas). Probado abriendo bloc de notas,
    YouTube, una búsqueda de Google y la calculadora.
  - Ampliación del grupo 1 (2026-07-02, pedida por el usuario): `reproducir_video_youtube`
    para poner directamente un video específico, no solo abrir la búsqueda. Se evaluaron
    `youtube-search-python` (sin mantenimiento desde 2020) y `ddgs.videos()` (backends
    genéricos, no garantiza resultados de YouTube); se eligió `yt-dlp` con
    `extract_flat=True` y prefijo `ytsearch1:<consulta>` — solo trae metadata del primer
    resultado (sin descargar nada) y se abre su `webpage_url` con `webbrowser.open`,
    igual que `abrir_web`; YouTube reproduce solo al cargar la página. Nueva dependencia
    instalada sin problemas: `yt-dlp`. Probado con LLM real: el modelo elige esta
    herramienta (no `abrir_web`) cuando se pide un video puntual.
  - Grupo 2 (búsqueda e info): `obtener_clima` (Open-Meteo, geocoding + forecast, sin key)
    y `buscar_info` (librería `ddgs`, no `duckduckgo-search` que está deprecada; devuelve
    resúmenes de texto para que el LLM los redacte hablados, NO abre el navegador — eso lo
    diferencia de `buscar_en_google`). Nueva dependencia instalada sin problemas: `ddgs`
    (y `requests`, ya estaba disponible).
  - Grupo 3 (sistema): `subir_bajar_volumen`, `silenciar_volumen` (`pycaw`; API actual usa
    `AudioUtilities.GetSpeakers().EndpointVolume` directo, sin el `cast`/`comtypes` viejo
    de los tutoriales), `control_multimedia` (`keyboard.send`), `estado_sistema`
    (`psutil`: batería/CPU/RAM), `apagar_o_suspender_pc` (`subprocess` + `shutdown`).
    Nuevas dependencias instaladas sin problemas: `pycaw`, `keyboard`, `psutil`.
    Confirmación de acciones destructivas resuelta a nivel de la propia función, sin
    esperar al Módulo 2: `apagar_o_suspender_pc(accion, confirmar)` con `confirmar=False`
    NO ejecuta nada y devuelve un mensaje pidiendo confirmar; el schema le exige al LLM
    llamarla primero sin confirmar y recién ejecutar con `confirmar=True` si el usuario
    dijo que sí explícitamente.
  - Grupo 4 (timers): `poner_timer`, `listar_timers`, `cancelar_timer` con
    `threading.Timer`. Decisión de diseño: el callback del timer (corre en un hilo aparte)
    NO habla directo por TTS — solo apila el mensaje en `_avisos_pendientes` (protegida
    por `threading.Lock`); función interna `obtener_avisos_pendientes()` (sin schema, no
    invocable por el LLM) vacía esa cola y la usará `asistente.py` desde el hilo principal
    para hablar los avisos entre turnos (Módulo 3). Probado con timer de 3s: dispara,
    aparece en la cola, y no se pierde ni duplica con otro timer cancelado en el medio.
  - Requirements actualizado: `requests`, `ddgs`, `pycaw`, `keyboard`, `psutil`.
  Próximo paso: Módulo 2 (function calling en `llm.py`).
- 2026-07-02: Módulo 2 (`src/llm.py` + `test_capa3b.py`) implementado y probado. `tools=`
  y `tool_choice="auto"` en la petición; bucle de hasta `MAX_LLAMADAS_HERRAMIENTAS = 3`
  llamadas encadenadas; system prompt ampliado con la lista de herramientas y la regla de
  confirmación para acciones destructivas.
  - Bug encontrado en uso real (probando "reproducí una canción de Duki"): el modelo a
    veces insiste llamando la MISMA herramienta "de apertura" (`abrir_app`, `abrir_web`,
    `buscar_en_google`, `reproducir_video_youtube`) dos veces dentro del mismo turno
    (ej: no le convence el primer resultado de búsqueda), abriendo dos pestañas/apps de
    verdad para un solo pedido. Arreglado con una guarda por turno
    (`HERRAMIENTAS_NO_REPETIBLES_POR_TURNO` + `_ejecutar_con_guarda`): la segunda llamada
    a la misma herramienta "no repetible" en el mismo turno no se ejecuta de verdad, se le
    devuelve un mensaje al modelo pidiéndole que responda con lo que ya tiene.
  - Segundo bug relacionado: a veces Qwen3 (vía NIM) no usa el campo estructurado
    `tool_calls` de la API y en cambio escribe la llamada como texto plano dentro de
    `content` (formato `<tool_call>{...}</tool_call>`, artefacto de su plantilla de
    entrenamiento). Sin manejarlo, ese texto crudo se leería literal por el TTS.
    Arreglado con `_extraer_tool_call_de_texto()` (regex + `json.loads`): si se detecta,
    se trata como una llamada real (con un `tool_call_id` fabricado) en vez de mostrarse
    al usuario. Ambos arreglos verificados con pruebas dirigidas simulando la respuesta
    del modelo (sin depender de que el bug no-determinista se repita solo).
- 2026-07-02: Módulo 3 (`src/asistente.py`) implementado. Nueva función
  `hablar_avisos_pendientes(voz)`: vacía la cola de `herramientas.obtener_avisos_pendientes()`
  y dice cada aviso por TTS, siempre desde el hilo principal (nunca desde el hilo del
  timer). Se revisa la cola en tres puntos: (1) al arrancar cada vuelta del loop manos
  libres, por si un timer venció mientras terminaba la sesión anterior; (2) pasándola
  como `en_cada_bloque` a `despertador.escuchar()` — la única ventana para avisar un
  timer mientras el asistente está "dormido" esperando "Hey Jarvis", ya que ese método
  llama el callback cada ~80ms mientras bloquea; (3) después de cada turno dentro de una
  sesión. También se agregó al loop `--teclado` (antes de cada `input()`), aunque ahí el
  caso de uso es menos relevante. Probado con timer real de 3s y una `Voz` de prueba:
  no habla nada antes de vencer, habla una sola vez al vencer, no repite en pasadas
  siguientes. **FASE B (v3) COMPLETADA** — los 4 grupos de herramientas funcionan por
  voz end-to-end, con confirmación en acciones destructivas y timers avisando incluso
  fuera de turno. Próxima fase (no empezar sin que se pida): Fase C (v4, segundo plano).
- 2026-07-02: Mejora de precisión del STT (pulido pre-Fase C, pedido por el usuario: "pon
  Duki" se transcribía "pon duque"). Cambios en `src/stt.py`:
  (1) **hotwords desde `vocabulario.txt`** (raíz del proyecto, una palabra por línea, `#`
  comenta, editable por el usuario): sesga la decodificación hacia nombres propios
  frecuentes sin inventarlos. OJO: en faster-whisper `hotwords` se ignora si se pasa
  `initial_prompt`, por eso se usa solo `hotwords`. Si el archivo no existe o está vacío,
  todo funciona como antes (`hotwords=None`).
  (2) **`condition_on_previous_text=False`**: cada segmento se decodifica sin usar el
  texto del anterior como contexto; evita que un error temprano contamine el resto
  (las frases del asistente duran <15s, ese contexto no aporta).
  (3) **Filtro de confianza por segmento**: se descartan segmentos con
  `no_speech_prob > 0.6` **y** `avg_logprob < -1.0` a la vez (umbral conservador contra
  alucinaciones típicas de Whisper tipo "Gracias por ver el video").
  Además, nuevo `src/test_stt_modelos.py`: benchmark interactivo que graba frases reales
  con el VAD (las guarda en `pruebas/` para re-comparar sin regrabar) y las transcribe
  con `small`, `medium` y `large-v3-turbo`, con y sin vocabulario, midiendo tiempos —
  el usuario decide con esa tabla si cambia el modelo por defecto (decisión del usuario:
  medir antes de pagar latencia). `medium` (~1.5GB) y `large-v3-turbo` (~1.6GB) se
  descargan a `models/` la primera vez.
- 2026-07-02: Benchmark corrido con el micrófono real (4 frases). Tiempos promedio por
  frase en esta CPU (int8): `small` 2.0s, `medium` 5.7s, `large-v3-turbo` 8.8s (turbo es
  MÁS lento que medium en CPU: su encoder grande domina el costo). Precisión: `turbo`
  perfecto en las 4; `small` solo falló "abre Spotify" → "ahora es Spotify"; `medium` no
  fue claramente mejor que small ("Bonduki", "Visa Rap"). Con el vocabulario, `small` ya
  no destroza nombres propios ("duque" desapareció; queda "ponduki" pegado, que el LLM
  interpreta bien). **Decisión del usuario: quedarse con `small`** (2s vs 9s por turno) y
  compensar su debilidad por el lado del LLM: se agregó al `PROMPT_SISTEMA` de `llm.py`
  que la entrada viene de un reconocedor de voz y puede traer errores fonéticos, con
  ejemplos ("ponduki" = "pon Duki", "ahora es Spotify" = "abre Spotify"), para que
  interprete la intención en vez de tomarlo literal. `asistente.py` no se tocó (sigue
  `Transcriptor("small")`). Los modelos medium/turbo quedan descargados en `models/` por
  si se quiere re-comparar (se pueden borrar para liberar ~3GB).
- 2026-07-02: Bug de `reproducir_video_youtube` (reportado por el usuario: "pon una
  canción de Duki" a veces abría el canal `youtube.com/channel/UCJUYcEdvnYFGajHBW0Nao3w`
  en vez de un video). Causa raíz, reproducida en consola: la búsqueda de YouTube mezcla
  videos con canales/playlists, y con consultas cortas de artistas famosos
  (`ytsearch:duki`) el canal oficial sale PRIMERO; el código abría `entradas[0]` sin
  verificar el tipo. Arreglo en `herramientas.py`: se pide `ytsearch5:` en vez de
  `ytsearch1:` y se abre el primer resultado cuya URL contenga `watch?v=` (los canales
  son `/channel/...` y las playlists `playlist?list=...`, se saltean). Verificado:
  "duki" ahora abre un video, no el canal. Costo extra de pedir 5 resultados flat:
  despreciable (misma petición de búsqueda).
- 2026-07-02: Al probar "abrí el canal de Duki", el LLM improvisó con
  `abrir_web("youtube channel duki")` y la rama "mejor esfuerzo" inventó el dominio
  `https://youtubechannelduki.com` (pegaba palabras + `.com`). Dos arreglos en
  `herramientas.py`: (1) `abrir_web` con varias palabras ya no inventa dominios,
  deriva a `buscar_en_google()`; (2) nueva herramienta `abrir_canal_youtube(nombre)` —
  misma búsqueda `ytsearch5:` que los videos pero quedándose con el resultado que ES
  canal (`/channel/` o `/@`); si no hay canal entre los resultados, abre la búsqueda de
  YouTube. Ojo: buscar el nombre A SECAS (agregar "canal" a la consulta empeora los
  resultados; YouTube ya pone el canal oficial primero). Agregada también a
  `HERRAMIENTAS_NO_REPETIBLES_POR_TURNO` en `llm.py` (abre una pestaña real).
  Verificado sin navegador: "duki" y "bizarrap" abren sus canales oficiales.

## Fase C — Siempre en segundo plano (v4)

**Meta:** el asistente arranca solo con Windows, vive en la bandeja del sistema y se
recupera de fallos sin morir.

### Tecnologías

| Necesidad | Elección | Por qué |
|---|---|---|
| Ícono de bandeja | `pystray` + `Pillow` | Estándar en Windows/Python; menú clic derecho |
| Sin ventana de consola | `pythonw.exe` del venv | Ya viene con Python, cero dependencias |
| Autoarranque | Programador de tareas de Windows ("al iniciar sesión") | Más robusto que la carpeta Inicio; permite retraso y reinicio en fallo |
| Logs (la consola ya no existe) | `logging` a `logs/asistente.log` con rotación (`RotatingFileHandler`) | Stdlib; imprescindible para diagnosticar en segundo plano |

### Módulos y prueba aislada

1. **`src/bandeja.py`** — ícono con estados por color (esperando / escuchando / pensando /
   hablando) y menú: pausar micrófono, ver estado, salir limpio.
   - *Prueba:* `test_bandeja.py` — ícono solo, cambiando de estado con un timer falso,
     sin el asistente detrás.
2. **`src/registro.py`** — configuración de `logging` compartida; los `print()` informativos
   de todos los módulos migran a `logger` (los tests siguen imprimiendo).
   - *Prueba:* correr el asistente y verificar que `logs/asistente.log` registra turnos y errores.
3. **`src/asistente.py`** (robustecer) — envolver el loop en recuperación por tipo de fallo:
   sin internet → lo dice por voz y reintenta con espera creciente; micrófono desconectado →
   reintenta y avisa en la bandeja; error inesperado → se registra y el loop continúa.
   El TTS/STT locales nunca dependen de la red, así que el asistente siempre puede *avisar* qué pasa.
   - *Prueba:* `test_resiliencia.py` + prueba manual: cortar el WiFi a mitad de conversación,
     desenchufar el micrófono USB → el proceso no muere y se recupera al volver.
4. **`scripts/instalar_autoarranque.ps1`** — crea la tarea programada apuntando a
   `venv\Scripts\pythonw.exe src\asistente.py` con directorio de trabajo en la raíz
   (crítico: rutas relativas a `models/` y `.env`). Incluir también el script inverso
   (`desinstalar_autoarranque.ps1`).
   - *Prueba:* cerrar sesión / reiniciar → el ícono aparece solo y el asistente responde.

### Criterio de cierre

Sobrevive un día completo de uso normal: arranca con Windows, sin consola, estados visibles
en la bandeja, se recupera de cortes de red/micrófono, y se cierra limpio desde el menú.

## Orden y dependencias

```
Fase A (v2: manos libres)  →  Fase B (v3: herramientas)  →  Fase C (v4: segundo plano)
```

- A va primero: es la base de la experiencia y lo que la Fase C deja corriendo todo el día.
- B no depende de A técnicamente, pero probar herramientas por voz manos libres es el flujo real.
- C va al final: solo tiene sentido dejar en segundo plano algo que ya hace cosas útiles.

## Verificación global (al final de las 3 fases)

Sin tocar el teclado, con la PC recién encendida: "Hey Jarvis, pon un temporizador de diez
minutos y dime cuánta batería queda" → confirma por voz, el timer avisa hablando a los diez
minutos, y el ícono de la bandeja reflejó cada estado. Ese es el asistente completo.
