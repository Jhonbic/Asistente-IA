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

- [ ] Fase A (v2) — Manos libres: wake word + VAD
- [ ] Fase B (v3) — Herramientas: function calling
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
4. **`src/asistente.py`** (adaptar) — nuevo loop manos libres; flag `--teclado` para arrancar
   en modo push-to-talk clásico. La cadena STT→LLM→TTS no se toca.
   - *Prueba de integración:* conversación completa sin tocar el teclado, varios turnos;
     verificar que mientras el asistente habla no se dispara a sí mismo (pausar el
     despertador durante el TTS).

### Criterio de cierre

Detecta la palabra >90% de las veces a distancia normal, corta solo al callar, y no se
auto-despierta con su propia voz. Usuario aprueba y se actualiza este archivo.

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
