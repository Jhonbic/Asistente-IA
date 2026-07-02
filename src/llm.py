"""Capa 3 — El "cerebro": LLM vía NVIDIA NIM.

NIM expone una API compatible con la de OpenAI, así que usamos el SDK
oficial `openai` apuntando a la URL de NVIDIA. Este mismo código serviría
para OpenAI, Groq u Ollama local cambiando solo base_url y api_key.

La API key vive en el archivo .env (que .gitignore excluye de git):
    NVIDIA_API_KEY=nvapi-...
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

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
- Tus respuestas se convierten a voz: sé breve (1-3 frases salvo que pidan detalle).
- Nada de markdown, listas, asteriscos ni emojis: solo texto plano hablable.
- Escribe los números como palabras cuando sea natural decirlos así.
- Si no sabes algo, dilo honestamente y en corto."""

# Cuántos intercambios (usuario + asistente) recordar. Limita el costo en
# tokens y evita que el historial crezca sin fin.
MAX_INTERCAMBIOS = 10


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
        """Envía el texto del usuario y devuelve la respuesta del modelo."""
        self.historial.append({"role": "user", "content": texto_usuario})
        self._recortar_historial()

        mensajes = [{"role": "system", "content": PROMPT_SISTEMA}] + self.historial

        try:
            respuesta = self.client.chat.completions.create(
                model=self.modelo,
                messages=mensajes,
                temperature=0.7,   # algo de variedad sin divagar
                max_tokens=300,    # tope de largo: es un asistente hablado
            )
        except RateLimitError:
            # Límite de ~40 req/min de NIM: esperamos un poco y reintentamos una vez.
            time.sleep(3)
            respuesta = self.client.chat.completions.create(
                model=self.modelo,
                messages=mensajes,
                temperature=0.7,
                max_tokens=300,
            )

        texto = respuesta.choices[0].message.content.strip()
        self.historial.append({"role": "assistant", "content": texto})
        return texto

    def _recortar_historial(self) -> None:
        """Conserva solo los últimos MAX_INTERCAMBIOS pares de mensajes."""
        maximo = MAX_INTERCAMBIOS * 2
        if len(self.historial) > maximo:
            self.historial = self.historial[-maximo:]
