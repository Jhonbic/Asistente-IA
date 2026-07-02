Fase A — Manos libres (palabra de activación)

- Agregar un detector de palabra de activación (ej. "Hey Jarvis") que escucha en un hilo permanente usando poco CPU.
- Cuando oye la palabra, reproduce un sonido corto ("te escucho") y activa la grabación.
- Integrar VAD (detección de voz) para que la grabación corte sola cuando dejas de hablar — se acabó el segundo Enter.
- Adaptar asistente.py para que el loop sea: esperar palabra → grabar hasta silencio → transcribir → responder → volver a esperar la palabra.
- Mantener push-to-talk como respaldo por si el micro falla o hay mucho ruido.

Fase B — Que haga cosas (herramientas / function calling)

- Modificar llm.py para enviar al modelo una lista de herramientas que puede invocar (function calling de NIM).
- Crear un módulo nuevo herramientas.py donde cada capacidad es una función de Python independiente y probable por separado.
- Implementar un despachador: cuando el LLM pide una herramienta, se ejecuta la función real y se le devuelve el resultado para que responda por voz.
- Herramientas iniciales (según lo que priorices):
  - Abrir apps y webs — lanzar programas y páginas por voz.
  - Timers y recordatorios — con aviso hablado al vencer.
  - Control del sistema — volumen, multimedia, batería, suspender/apagar.
  - Búsqueda e info — hora, fecha, clima, cálculos, búsquedas web.
- Cada herramienta se prueba aislada (como las capas) antes de conectarla.

Fase C — Siempre en segundo plano

- Agregar un ícono en la bandeja del sistema que muestra el estado (escuchando / pensando) y permite salir con clic derecho.
Fase C — Siempre en segundo plano

- Agregar un ícono en la bandeja del sistema que muestra el estado (escuchando / pensando) y permite salir con clic derecho.
- Hacer que el asistente corra sin ventana de terminal visible.
- Configurar el autoarranque con Windows (al iniciar sesión) vía el Programador de tareas.
- Manejo robusto de errores para que, corriendo todo el día, un fallo puntual (sin internet, micro ocupado) no lo tumbe: se recupera solo y sigue escuchando.