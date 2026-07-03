# Asistente de voz personal (Windows, Python)

Asistente de voz local: micrófono → Whisper (STT local) → NVIDIA NIM (LLM en nube) →
Piper (TTS local). La v1 (conversación por voz) está TERMINADA y funciona.

Fase A / v2 (manos libres — wake word + VAD) TERMINADA y funciona (confirmado por el
usuario 2026-07-02). Tras un solo "Hey Jarvis" se abre una sesión con turnos seguidos
sin repetir la palabra; "adiós" cierra la sesión (no el programa) y vuelve a esperar
"Hey Jarvis".

Fase B / v3 (herramientas — function calling) TERMINADA y funciona (confirmado por el
usuario 2026-07-02). El LLM puede abrir apps/webs/videos de YouTube, buscar información,
dar el clima, controlar volumen/multimedia, ver batería/CPU/RAM, poner timers y
apagar/suspender la PC (con confirmación previa). Los timers avisan por voz aunque
venzan fuera de un turno. Siguiente fase (no empezar sin que se pida): Fase C (siempre
en segundo plano — bandeja del sistema, autoarranque, logging, resiliencia), ver
`PLAN.md`.

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
  (wake word), `test_vad.py` (corte automático de fin de frase), `test_herramientas.py`
  (herramientas sin LLM ni voz), `test_capa3b.py` (chat con function calling, sin audio),
  `test_stt_modelos.py` (benchmark de modelos Whisper con voz real, con/sin vocabulario).
- Ejecutar siempre desde la raíz del proyecto.

## Arquitectura (src/)

- `audio.py` — captura/reproducción, 16kHz mono float32, push-to-talk
- `stt.py` — Whisper `small`, CPU int8, modelos en `models/`; hotwords desde
  `vocabulario.txt` (raíz del proyecto, editable por el usuario) para nombres propios,
  `condition_on_previous_text=False` y filtro de confianza contra alucinaciones
- `llm.py` — NIM vía SDK openai; modelo `qwen/qwen3-next-80b-a3b-instruct`; key en `.env`
  (`NVIDIA_API_KEY`); system prompt exige respuestas breves SIN markdown (se leen en voz
  alta) y avisa que la entrada viene del STT y puede traer errores fonéticos (interpretar
  intención, no literal).
  Fase B: manda `tools=TOOLS` (schemas de `herramientas.py`) y maneja `tool_calls` en un
  bucle de hasta `MAX_LLAMADAS_HERRAMIENTAS = 3`; guarda por turno para no repetir
  herramientas "de apertura" y parser de respaldo para `tool_calls` que el modelo a veces
  escribe como texto plano en vez de usar el campo estructurado (ver Gotchas).
- `herramientas.py` — Fase B: registro central `HERRAMIENTAS` (nombre → función + schema
  JSON) y despachador `ejecutar_herramienta()`. 4 grupos: apps/webs (`abrir_app` — abre
  CUALQUIER app/juego instalado vía catálogo dinámico de `Get-StartApps` con match difuso,
  más atajos manuales en `APPS_CONOCIDAS`; `precargar_catalogo_apps()` lo carga en un hilo
  al arrancar, `cerrar_app` — cierre amable por PID con `CloseMainWindow()` matcheando
  proceso/título de ventana, `forzar=true` solo a pedido explícito del usuario,
  `abrir_web` — con varias palabras deriva a Google en vez de inventar un dominio `.com`,
  `buscar_en_google`, `reproducir_video_youtube` y `abrir_canal_youtube` vía `yt-dlp`), búsqueda e
  info (`obtener_clima` con Open-Meteo, `buscar_info` con `ddgs`), sistema
  (`subir_bajar_volumen`/`silenciar_volumen` con `pycaw`, `control_multimedia` con
  `keyboard`, `estado_sistema` con `psutil`, `apagar_o_suspender_pc` con confirmación
  obligatoria) y timers (`poner_timer`/`listar_timers`/`cancelar_timer` con
  `threading.Timer`; `obtener_avisos_pendientes()` es interna, no invocable por el LLM).
- `tts.py` — Piper, voz `es_AR-daniela-high`, voces en `models/piper/`
- `despertador.py` — Fase A: wake word "hey_jarvis" con openWakeWord (ONNX), clase
  `Despertador`, `UMBRAL_DETECCION = 0.1` (calibrado con el micrófono real del usuario)
- `vad.py` — Fase A: corte automático de fin de frase con Silero VAD (ONNX, reutiliza el
  modelo que ya descarga openWakeWord — sin `torch`), clase `EscuchaConVAD`
- `asistente.py` — loop conversacional (une todo); modo manos libres por defecto
  (wake word + VAD + sesión continua), flag `--teclado` para el modo push-to-talk clásico.
  `hablar_avisos_pendientes()` (Fase B) revisa la cola de timers vencidos y los habla,
  llamada entre turnos y como callback de `despertador.escuchar()` mientras "duerme".

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
- `pycaw` (versión actual, 2026): la API vieja de los tutoriales
  (`AudioUtilities.GetSpeakers().Activate(IAudioEndpointVolume._iid_, ...)` + `comtypes`)
  ya no existe. Ahora es directo: `AudioUtilities.GetSpeakers().EndpointVolume`.
- Abrir apps instaladas (Store/UWP, juegos, launchers): `Get-StartApps` (PowerShell) da
  nombre → AppID de todo el menú Inicio, y cualquier AppID se lanza con
  `os.startfile("shell:AppsFolder\\<AppID>")`. OJO: (1) los AppID de juegos son
  auto-generados (`Microsoft.AutoGenerated.{...}`) y cambian al reinstalar — no
  hardcodearlos, leer el catálogo en cada arranque; (2) `ConvertTo-Json` devuelve un
  objeto suelto (no lista) si hay UN solo resultado; (3) forzar
  `[Console]::OutputEncoding` a UTF-8 en el comando de PowerShell o los nombres con
  acentos llegan rotos (consola cp1252).
- Cerrar apps: NUNCA matar por nombre de proceso — todas las apps de la Store viven
  dentro de UN solo `ApplicationFrameHost` y WhatsApp usa un `msedgewebview2` compartido;
  cerrar por PID con `CloseMainWindow()`. El nombre de proceso puede no parecerse al de
  la app (Red Dead Redemption = proceso `RDR`): matchear también títulos de ventana.
  Algunas apps (WhatsApp) cierran la ventana pero quedan vivas en la bandeja del
  sistema: el "éxito" del cierre se mide por la ventana desaparecida, no por el proceso
  muerto.
- `ddgs` es el nombre actual del paquete (antes `duckduckgo-search`, deprecado). Para
  video específico de YouTube no sirve `ddgs.videos()` (backends genéricos, no garantiza
  YouTube) ni `youtube-search-python` (sin mantenimiento desde 2020): se usa `yt-dlp` con
  `extract_flat=True` y prefijo `ytsearch5:<consulta>` (solo trae metadata, no descarga).
  OJO: la búsqueda de YouTube mezcla videos con canales/playlists y al buscar un artista
  famoso su canal oficial suele salir PRIMERO (ej: "duki" → `youtube.com/channel/...`);
  por eso se piden 5 resultados y se abre el primero cuya URL contenga `watch?v=`.
- Qwen3 (vía NIM) en el flujo de function calling: (1) a veces llama la misma herramienta
  "de apertura" dos veces en el mismo turno si no le convence el primer resultado (abre
  dos pestañas/apps reales) — mitigado con una guarda por turno en `llm.py`
  (`HERRAMIENTAS_NO_REPETIBLES_POR_TURNO`); (2) a veces escribe el `tool_call` como texto
  plano (`<tool_call>{...}</tool_call>`) en vez de usar el campo estructurado de la API —
  mitigado con un parser de respaldo (`_extraer_tool_call_de_texto`) para que no se hable
  literal por TTS; (3) a veces ANUNCIA la acción como texto final ("Abro WhatsApp.") sin
  emitir ningún tool_call — y como esa respuesta queda en el historial, los turnos
  siguientes la imitan y la sesión entera deja de usar herramientas — mitigado con
  `_parece_anuncio_sin_accion` (regex de anuncios, excluye preguntas) + un reintento por
  turno con `tool_choice="required"` (NIM lo soporta). Los tres son comportamientos no
  determinísticos del modelo, no bugs de la API; si se cambia de modelo, volver a probar
  si siguen ocurriendo.

## Futuro acordado (no implementar sin que lo pida)

Fase C (v4): siempre en segundo plano — ícono de bandeja (`pystray`), autoarranque con
el Programador de tareas de Windows, logging a archivo (la consola ya no existe en modo
`pythonw.exe`), y recuperación de fallos (sin internet / micrófono desconectado) sin que
el proceso muera. Detalle completo en `PLAN.md`, sección "Fase C". El diseño modular ya
lo contempla; audio/STT/TTS/LLM/herramientas no se tocan, solo se envuelven.
