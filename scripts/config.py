import json
import os

# Obtener el directorio raíz del proyecto (donde está main.py)
# __file__ es scripts/config.py, así que subimos un nivel
_DIR_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Ruta de Credenciales ---
CREDENTIALS_PATH = os.path.join(_DIR_BASE, "credentials.json")

# --- Cargar Webhook de Discord ---
WEBHOOK_URL = None
try:
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as cred_file:
        _credentials = json.load(cred_file)
    WEBHOOK_URL = _credentials["discord"]["webhook_url"]
except (FileNotFoundError, KeyError) as err:
    print(
        f"ADVERTENCIA: No se pudo leer {CREDENTIALS_PATH}. "
        "La URL del Webhook está 'None'. El envío a Discord fallará."
    )

# --- Cargar Credenciales de Telegram ---
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None
try:
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as cred_file:
        _credentials = json.load(cred_file)
    TELEGRAM_BOT_TOKEN = _credentials.get("telegram", {}).get("bot_token")
    TELEGRAM_CHAT_ID = _credentials.get("telegram", {}).get("chat_id")
except (FileNotFoundError, KeyError) as err:
    print(
        f"ADVERTENCIA: No se pudieron leer las credenciales de Telegram en {CREDENTIALS_PATH}. "
        "El envío a Telegram fallará."
    )

# --- Configuración de Detección y Video ---
ANCHO_PROCESAMIENTO = 640
FPS_ESPERADO = 15  # FPS para la grabación de video

SEGUNDOS_PRE_ROLL = 1.0   # Segundos a guardar ANTES de la detección
SEGUNDOS_POST_ROLL = 9.0  # Segundos a grabar DESPUÉS de la detección

# Tamaño del búfer (cuántos fotogramas guardar en RAM)
TAMAÑO_BUFFER = int(FPS_ESPERADO * SEGUNDOS_PRE_ROLL)
# Cuántos fotogramas grabar después de la detección
FRAMES_A_GRABAR_POST = int(FPS_ESPERADO * SEGUNDOS_POST_ROLL)

# --- Configuración del Modelo de IA ---
MODEL_PATH = os.path.join(_DIR_BASE, 'efficientdet_lite0.tflite')
UMBRAL_CONFIANZA_OBJETO = 0.60 # Confianza mínima (60%)

# --- Configuración de Alertas ---
COOLDOWN_SEGUNDOS = 20 # Esperar 20s entre alertas
LIMITE_MB_DISCORD = 24 * 1024 * 1024 # Límite de 25MB para Discord
LIMITE_MB_TELEGRAM = 50 * 1024 * 1024 # Límite de 50MB para Telegram