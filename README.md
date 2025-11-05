# CCTV Logger - Sistema de Detección de Objetos con Alertas

Sistema de monitoreo de seguridad que detecta objetos en tiempo real mediante una cámara, graba videos de alertas y los envía automáticamente a Discord y/o Telegram.

## 🎯 Características

- **Detección de objetos en tiempo real** usando MediaPipe EfficientDet
- **Grabación automática de videos** cuando se detecta movimiento
  - Guarda 1.5 segundos antes de la detección
  - Graba 7 segundos después de la detección
- **Envío automático de alertas** a Discord y/o Telegram
- **Análisis inteligente** cuando el video es muy grande:
  - Si el video supera 25MB (Discord) o 50MB (Telegram), analiza todos los frames
  - Envía el frame donde mejor se ve el objeto detectado
- **Soporte para múltiples servicios** simultáneamente

## 📋 Requisitos

- Python 3.8 o superior
- Cámara conectada (webcam o cámara USB)
- Conexión a Internet (para descargar el modelo y enviar alertas)

## 🚀 Instalación

1. **Clonar el repositorio:**
```bash
git clone <url-del-repositorio>
cd cctv_logger
```

2. **Instalar dependencias:**
```bash
pip install opencv-python mediapipe requests
```

3. **Configurar credenciales** (ver sección de configuración abajo)

4. **Ejecutar el script:**
```bash
python main.py
```

## ⚙️ Configuración

### Credenciales

El sistema requiere un archivo `credentials.json` en la raíz del proyecto. Este archivo contiene las credenciales para Discord y Telegram.

#### Paso 1: Crear el archivo

Copia el archivo `credentials-template.json` y renómbralo a `credentials.json`:

```bash
cp credentials-template.json credentials.json
```

#### Paso 2: Configurar Discord (Opcional)

1. Ve a tu servidor de Discord
2. Configuración del servidor → Integraciones → Webhooks
3. Crea un nuevo webhook
4. Copia la URL del webhook
5. Pega la URL en `credentials.json` en el campo `discord.webhook_url`

**Ejemplo:**
```json
{
  "discord": {
    "webhook_url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
  }
}
```

#### Paso 3: Configurar Telegram (Opcional)

1. **Obtener el Bot Token:**
   - Abre Telegram y busca `@BotFather`
   - Envía `/newbot` y sigue las instrucciones
   - Copia el token que te proporciona (ejemplo: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Obtener el Chat ID:**
   
   **Opción A - Usando @userinfobot:**
   - Busca `@userinfobot` en Telegram
   - Inicia una conversación
   - El bot te mostrará tu Chat ID

   **Opción B - Usando la API:**
   - Envía un mensaje a tu bot (cualquier mensaje)
   - Visita en tu navegador: `https://api.telegram.org/bot<TU_BOT_TOKEN>/getUpdates`
   - Reemplaza `<TU_BOT_TOKEN>` con tu token real (sin los `< >`)
   - Busca `"chat":{"id":` en la respuesta JSON
   - El número que aparece es tu Chat ID

3. **Pegar en credentials.json:**
```json
{
  "telegram": {
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "123456789"
  }
}
```

#### Archivo completo de ejemplo:

```json
{
  "discord": {
    "webhook_url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
  },
  "telegram": {
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "123456789"
  }
}
```

**Nota:** Puedes configurar solo Discord, solo Telegram, o ambos. Si no configuras un servicio, simplemente no se enviarán alertas a ese servicio.

## 🔧 Configuración Avanzada

Puedes ajustar los parámetros en `scripts/config.py`:

- `ANCHO_PROCESAMIENTO`: Ancho de procesamiento de video (default: 640)
- `FPS_ESPERADO`: FPS para la grabación (default: 15)
- `SEGUNDOS_PRE_ROLL`: Segundos antes de la detección (default: 1.5)
- `SEGUNDOS_POST_ROLL`: Segundos después de la detección (default: 7)
- `UMBRAL_CONFIANZA_OBJETO`: Confianza mínima para detectar (default: 0.50 = 50%)
- `COOLDOWN_SEGUNDOS`: Tiempo entre alertas (default: 20 segundos)

## 📝 Formato de Alertas

Las alertas incluyen:
- **Fecha y hora formateada:** Día completo, fecha (DD-MM-YY) a las (HH:MM:SS)
- **Video embebido** (en Discord) o adjunto (en Telegram)
- **Mensaje descriptivo** con la información de la detección

## 🎥 Cómo Funciona

1. **Inicialización:** El script carga el modelo de IA (se descarga automáticamente la primera vez)
2. **Detección continua:** Analiza cada frame de la cámara en busca de objetos
3. **Grabación:** Cuando detecta un objeto:
   - Guarda los frames del buffer (pre-roll)
   - Continúa grabando durante el post-roll
   - Genera un video en formato MP4
4. **Envío:** Envía el video a los servicios configurados en segundo plano
5. **Limpieza:** Elimina los archivos temporales después del envío

## ⚠️ Notas Importantes

- El archivo `credentials.json` está en `.gitignore` por seguridad - no se subirá al repositorio
- El modelo de IA se descarga automáticamente la primera vez que ejecutas el script
- Los videos se eliminan automáticamente después de enviarse
- Si el video es muy grande, se envía solo el mejor frame encontrado
- Presiona 'q' en la ventana de video para salir del programa

## 🐛 Solución de Problemas

**Error: "No se pudo abrir la cámara"**
- Verifica que la cámara esté conectada
- En Linux, asegúrate de tener permisos de acceso a `/dev/video0`
- Prueba cambiar el índice en `main.py`: `cv2.VideoCapture(0)` → `cv2.VideoCapture(1)`

**Error: "WEBHOOK_URL no está configurado"**
- Verifica que `credentials.json` exista y tenga el formato correcto
- Asegúrate de que la URL del webhook sea válida

**El video no se envía a Discord/Telegram**
- Verifica las credenciales en `credentials.json`
- Revisa los logs para ver mensajes de error específicos
- Verifica tu conexión a Internet

## 📄 Licencia

[Especificar licencia si es necesario]

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request para cualquier mejora.

