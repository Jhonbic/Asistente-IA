"""Capa 3 — El "cerebro": LLM vía NVIDIA NIM.

NIM expone una API compatible con la de OpenAI, así que usamos el SDK
oficial `openai` apuntando a la URL de NVIDIA. Este mismo código serviría
para OpenAI, Groq u Ollama local cambiando solo base_url y api_key.

La API key vive en el archivo .env (que .gitignore excluye de git):
    NVIDIA_API_KEY=nvapi-...
"""

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from herramientas import HERRAMIENTAS, ejecutar_herramienta

# Carga las variables del archivo .env de la raíz del proyecto.
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# Elegido tras benchmark real (2026-07-01): responde en ~1s con español
# excelente. El meta/llama-3.3-70b-instruct del plan original estaba
# saturado en el tier gratuito (timeouts de 45s+).
MODELO = "qwen/qwen3-next-80b-a3b-instruct"

# La "personalidad" del asistente. Clave: sus respuestas se van a LEER EN
# VOZ ALTA por el TTS, así que le pedimos brevedad y cero formato markdown
# (un asterisco o una lista con guiones sonarían fatal hablados).
PROMPT_SISTEMA = """Eres un asistente de voz personal que corre en la PC de tu usuario.
Hablas español de forma natural, comica y cercana.

Reglas importantes:
- Lo que te llega del usuario viene de un reconocedor de voz y puede traer errores
  fonéticos: palabras pegadas ("ponduki" = "pon Duki") o cambiadas por otras que suenan
  parecido ("ahora es Spotify" = "abre Spotify"). Interpretá la intención más probable
  en vez de tomarlo literal, sobre todo con nombres de artistas, canciones y apps.
- Tus respuestas se convierten a voz: sé breve (1-3 frases salvo que pidan detalle).
- Nada de markdown, listas, asteriscos ni emojis: solo texto plano hablable.
- Escribe los números como palabras cuando sea natural decirlos así.
- Si no sabes algo, dilo honestamente y en corto.
- Tenés herramientas para hacer cosas en la PC (abrir/cerrar apps, abrir webs, buscar
  información, dar el clima, controlar volumen y multimedia, ver batería/CPU/RAM, poner
  timers, apagar o suspender la PC). Cuando el pedido del usuario coincida con una, usala
  en vez de solo describir cómo hacerlo. Anunciá brevemente la acción que vas a hacer.
- NUNCA digas que estás haciendo una acción ("abro tal app") sin llamar a la herramienta
  en ese mismo mensaje: decirlo sin llamarla deja al usuario esperando algo que no pasa.
- Apagar o suspender la PC es una acción DESTRUCTIVA: primero preguntale al usuario si
  está seguro y llamá la herramienta con confirmar=false; solo volvé a llamarla con
  confirmar=true si el usuario confirmó explícitamente que sí en su siguiente mensaje."""

# Cuántos intercambios (usuario + asistente) recordar. Limita el costo en
# tokens y evita que el historial crezca sin fin.
MAX_INTERCAMBIOS = 10

# Tope de llamadas a herramientas encadenadas dentro de un mismo turno, para
# evitar que el modelo entre en un bucle infinito (herramienta -> herramienta -> ...).
MAX_LLAMADAS_HERRAMIENTAS = 3

# Schemas en el formato que espera la API `tools`: una lista con la entrada
# "schema" de cada herramienta registrada en herramientas.py.
TOOLS = [entrada["schema"] for entrada in HERRAMIENTAS.values()]

# Herramientas que "abren algo" (pestaña, app): si el modelo no queda
# conforme con el resultado (ej: un video mal elegido), a veces insiste
# llamando la misma herramienta de nuevo dentro del mismo turno, y cada
# llamada repite la acción real (segunda pestaña, segunda app abierta).
# Estas no deben ejecutarse dos veces en el mismo turno.
HERRAMIENTAS_NO_REPETIBLES_POR_TURNO = {
    "abrir_app",
    "cerrar_app",
    "abrir_web",
    "buscar_en_google",
    "reproducir_video_youtube",
    "abrir_canal_youtube",
}

# Qwen3 a veces, en vez de usar el campo estructurado tool_calls de la API,
# escribe el intento de llamada como texto plano dentro del content (un
# artefacto de su formato de entrenamiento). Si no lo detectamos, ese texto
# crudo terminaría hablado por el TTS. Este patrón lo reconoce y permite
# tratarlo como una llamada real.
PATRON_TOOL_CALL_EN_TEXTO = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)

# Tercer capricho de Qwen3 (descubierto 2026-07-03): a veces ANUNCIA la acción
# ("Abro WhatsApp.") como respuesta final pero no emite ningún tool_call — el
# usuario escucha que la va a hacer y no pasa nada. Peor: esa respuesta queda
# en el historial y los turnos siguientes la imitan, así que la sesión entera
# deja de usar herramientas. Este patrón detecta esos anuncios para reintentar
# la petición UNA vez forzando una herramienta (tool_choice="required").
PATRON_ANUNCIO_SIN_ACCION = re.compile(
    r"\b(abro|abriendo|voy a abrir|cierro|cerrando|voy a cerrar|"
    r"pongo|poniendo|voy a poner|reproduzco|reproduciendo|voy a reproducir|"
    r"busco|buscando|voy a buscar|silencio el|subo el|bajo el)\b",
    re.IGNORECASE,
)


def _parece_anuncio_sin_accion(texto: str) -> bool:
    """True si el texto anuncia una acción concreta (y no es una pregunta).

    Las preguntas se excluyen a propósito: si el modelo pregunta "¿Querés que
    abra X?" está pidiendo confirmación y NO hay que forzar ninguna acción.
    """
    if not texto or "?" in texto or "¿" in texto:
        return False
    return PATRON_ANUNCIO_SIN_ACCION.search(texto) is not None


def _extraer_tool_call_de_texto(texto: str):
    """Si el texto contiene un tool_call en formato de texto plano, lo parsea.

    Devuelve (nombre, argumentos_dict) o None si no hay nada que parsear.
    """
    if not texto:
        return None
    coincidencia = PATRON_TOOL_CALL_EN_TEXTO.search(texto)
    if not coincidencia:
        return None
    try:
        datos = json.loads(coincidencia.group(1))
        return datos["name"], datos.get("arguments", {})
    except (json.JSONDecodeError, KeyError):
        return None


class Cerebro:
    def __init__(self, modelo: str = MODELO):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta NVIDIA_API_KEY. Crea un archivo .env en la raíz del "
                "proyecto con la línea: NVIDIA_API_KEY=nvapi-..."
            )
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            timeout=45.0,     # sin esto, una petición atascada cuelga para siempre
            max_retries=1,
        )
        self.modelo = modelo
        # El historial es una lista de mensajes {role, content}. El LLM no
        # tiene memoria propia: "recuerda" porque le reenviamos todo esto
        # en cada petición.
        self.historial: list[dict] = []

    def responder(self, texto_usuario: str) -> str:
        """Envía el texto del usuario y devuelve la respuesta del modelo.

        Si el modelo decide usar una herramienta, la ejecuta, le devuelve el
        resultado y vuelve a preguntarle qué decir; repite esto hasta
        MAX_LLAMADAS_HERRAMIENTAS veces como máximo (evita bucles infinitos
        si el modelo insiste en llamar herramientas sin parar).
        """
        self.historial.append({"role": "user", "content": texto_usuario})
        self._recortar_historial()

        # Registra qué herramientas "de una sola vez" ya se ejecutaron en
        # este turno, para no repetirlas si el modelo insiste (ver
        # HERRAMIENTAS_NO_REPETIBLES_POR_TURNO más arriba).
        ejecutadas_este_turno: set[str] = set()
        # Para reintentar con tool_choice="required" a lo sumo UNA vez por
        # turno si el modelo anuncia una acción sin llamar la herramienta.
        ya_forzado_este_turno = False

        for _ in range(MAX_LLAMADAS_HERRAMIENTAS):
            mensajes = [{"role": "system", "content": PROMPT_SISTEMA}] + self.historial
            mensaje = self._pedir_completado(mensajes)

            tool_calls = mensaje.tool_calls
            if not tool_calls:
                # A veces el modelo escribe la llamada como texto plano en
                # vez de usar el campo estructurado de la API. La detectamos
                # y la tratamos igual que una llamada real, para que no
                # termine hablada literalmente por el TTS.
                extraida = _extraer_tool_call_de_texto(mensaje.content)
                if extraida is None:
                    texto = (mensaje.content or "").strip()
                    # Anuncio sin acción ("Abro WhatsApp." y ningún tool_call):
                    # reintentamos una vez FORZANDO que llame una herramienta.
                    # Solo si todavía no ejecutó ninguna en este turno: después
                    # de una herramienta real, un "Abriendo X." de cierre es la
                    # respuesta correcta, no un anuncio vacío.
                    if (
                        not ya_forzado_este_turno
                        and not ejecutadas_este_turno
                        and _parece_anuncio_sin_accion(texto)
                    ):
                        ya_forzado_este_turno = True
                        mensaje = self._pedir_completado(mensajes, forzar_herramienta=True)
                        tool_calls = mensaje.tool_calls
                    if not tool_calls:
                        # Sin reintento (o el reintento tampoco trajo llamadas):
                        # es una respuesta de texto normal, la devolvemos.
                        self.historial.append({"role": "assistant", "content": texto})
                        return texto
                    # El reintento forzado SÍ trajo tool_calls: seguimos abajo
                    # por el camino estructurado normal (sin guardar el anuncio
                    # vacío en el historial, para que no lo imite después).
                else:
                    nombre, argumentos = extraida
                    id_falso = f"texto-plano-{len(self.historial)}"
                    self.historial.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": id_falso,
                                    "type": "function",
                                    "function": {"name": nombre, "arguments": json.dumps(argumentos)},
                                }
                            ],
                        }
                    )
                    resultado = self._ejecutar_con_guarda(nombre, argumentos, ejecutadas_este_turno)
                    self.historial.append({"role": "tool", "tool_call_id": id_falso, "content": resultado})
                    continue

            # El modelo pidió usar una o más herramientas: las ejecutamos y le
            # devolvemos el resultado para que arme la respuesta final.
            self.historial.append(
                {
                    "role": "assistant",
                    "content": mensaje.content,
                    "tool_calls": [tc.model_dump() for tc in tool_calls],
                }
            )
            for llamada in tool_calls:
                argumentos = json.loads(llamada.function.arguments)
                resultado = self._ejecutar_con_guarda(
                    llamada.function.name, argumentos, ejecutadas_este_turno
                )
                self.historial.append(
                    {"role": "tool", "tool_call_id": llamada.id, "content": resultado}
                )

        # Se agotaron los intentos: pedimos una respuesta final sin permitir
        # más herramientas, para no dejar al usuario sin contestación.
        mensajes = [{"role": "system", "content": PROMPT_SISTEMA}] + self.historial
        mensaje = self._pedir_completado(mensajes, permitir_herramientas=False)
        texto = (mensaje.content or "").strip()
        self.historial.append({"role": "assistant", "content": texto})
        return texto

    def _ejecutar_con_guarda(self, nombre: str, argumentos: dict, ejecutadas_este_turno: set) -> str:
        """Ejecuta una herramienta, salvo que sea 'no repetible' y ya se haya usado este turno."""
        if nombre in HERRAMIENTAS_NO_REPETIBLES_POR_TURNO and nombre in ejecutadas_este_turno:
            return (
                "Esa acción ya se ejecutó en este turno, no la repitas: "
                "respondé directo con el resultado que ya tenés."
            )
        ejecutadas_este_turno.add(nombre)
        return ejecutar_herramienta(nombre, argumentos)

    def _pedir_completado(
        self,
        mensajes: list[dict],
        permitir_herramientas: bool = True,
        forzar_herramienta: bool = False,
    ):
        """Llama a la API con reintento ante rate limit; devuelve el mensaje de la respuesta.

        Con forzar_herramienta=True se manda tool_choice="required": el modelo
        está OBLIGADO a llamar alguna herramienta (se usa para el reintento
        cuando anunció una acción sin ejecutarla).
        """
        kwargs = dict(
            model=self.modelo,
            messages=mensajes,
            temperature=0.7,   # algo de variedad sin divagar
            max_tokens=300,    # tope de largo: es un asistente hablado
        )
        if permitir_herramientas:
            kwargs["tools"] = TOOLS
            kwargs["tool_choice"] = "required" if forzar_herramienta else "auto"

        try:
            respuesta = self.client.chat.completions.create(**kwargs)
        except RateLimitError:
            # Límite de ~40 req/min de NIM: esperamos un poco y reintentamos una vez.
            time.sleep(3)
            respuesta = self.client.chat.completions.create(**kwargs)

        return respuesta.choices[0].message

    def _recortar_historial(self) -> None:
        """Conserva solo los últimos MAX_INTERCAMBIOS pares de mensajes."""
        maximo = MAX_INTERCAMBIOS * 2
        if len(self.historial) > maximo:
            self.historial = self.historial[-maximo:]
