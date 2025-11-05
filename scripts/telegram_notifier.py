import requests
import os
import time
from datetime import datetime
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Importamos las configuraciones que necesitamos
from scripts.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LIMITE_MB_TELEGRAM, MODEL_PATH, UMBRAL_CONFIANZA_OBJETO

def formatear_fecha_hora():
    """
    Retorna la fecha y hora formateada como:
    Día completo, fecha (DD-MM-YY) a las (hora HH:MM:SS)
    Ejemplo: "Lunes, 04-11-25 a las 22:21:16"
    """
    ahora = datetime.now()
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_semana = dias_semana[ahora.weekday()]
    fecha = ahora.strftime('%d-%m-%y')
    hora = ahora.strftime('%H:%M:%S')
    return f"{dia_semana}, {fecha} a las {hora}"

def enviar_alerta_telegram_con_video(ruta_video, ruta_thumbnail, callback_terminado=None):
    """Envía un mensaje con video a Telegram.
    
    Args:
        ruta_video: Ruta del archivo de video
        ruta_thumbnail: Ruta del archivo thumbnail
        callback_terminado: Función a llamar cuando el servicio termine de usar los archivos
    """
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error de envío: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados.")
        if callback_terminado:
            callback_terminado()
        return

    print(f"[{time.ctime()}] Hilo de envío: Preparando envío a Telegram...")
    
    try:
        video_size = os.path.getsize(ruta_video)
        
        if video_size > LIMITE_MB_TELEGRAM:
            print(f"Video muy grande ({video_size / (1024*1024):.2f}MB) supera el límite de Telegram (50MB).")
            print("Analizando video para encontrar el mejor frame con objeto detectado...")
            
            # Analizar el video para encontrar el mejor frame
            mejor_frame_path = encontrar_mejor_frame_objeto(ruta_video)
            
            if mejor_frame_path and os.path.exists(mejor_frame_path):
                # Enviar el mejor frame encontrado
                enviar_solo_imagen(
                    mejor_frame_path, 
                    f"Video grabado ({video_size / (1024*1024):.2f}MB, muy grande para Telegram). "
                    "Se envió el frame donde mejor se ve el objeto detectado."
                )
            else:
                # Fallback: usar el thumbnail original si no se encontró mejor frame
                print("No se pudo encontrar mejor frame, usando thumbnail original.")
                enviar_solo_imagen(
                    ruta_thumbnail, 
                    f"Video grabado ({video_size / (1024*1024):.2f}MB, muy grande para Telegram)"
                )
            
            # Notificar que terminamos de usar los archivos
            if callback_terminado:
                callback_terminado()
            return

        # Enviar video a Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        mensaje = f"🔴 AVISO\nMovimiento detectado el {formatear_fecha_hora()}."
        
        with open(ruta_video, 'rb') as video_file:
            files = {'video': (os.path.basename(ruta_video), video_file, 'video/mp4')}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': mensaje,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"[{time.ctime()}] Hilo de envío: Video enviado a Telegram correctamente.")
            else:
                print(f"Error al enviar video a Telegram: {result.get('description', 'Error desconocido')}")
        else:
            print(f"Error al enviar video a Telegram: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Excepción en el hilo de envío a Telegram: {e}")
    finally:
        # Notificar que terminamos de usar los archivos
        if callback_terminado:
            callback_terminado()

def encontrar_mejor_frame_objeto(ruta_video):
    """
    Analiza un video grabado para encontrar el frame donde mejor se vea el objeto detectado.
    Retorna la ruta del archivo de imagen guardado, o None si no se encuentra ningún objeto.
    """
    print(f"[{time.ctime()}] Analizando video para encontrar el mejor frame con objeto...")
    
    # Crear un detector en modo IMAGE para analizar frames individuales
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        score_threshold=UMBRAL_CONFIANZA_OBJETO
        # Sin category_allowlist para detectar todos los objetos
    )
    
    try:
        detector = vision.ObjectDetector.create_from_options(options)
    except Exception as e:
        print(f"Error al crear detector para análisis de video: {e}")
        return None
    
    cap = cv2.VideoCapture(ruta_video)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir el video {ruta_video}")
        return None
    
    mejor_frame = None
    mejor_score = 0
    mejor_frame_num = 0
    frame_num = 0
    
    try:
        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break
            
            # Convertir a RGB para MediaPipe
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            
            # Detectar objetos en este frame
            try:
                detection_result = detector.detect(mp_image)
                
                for detection in detection_result.detections:
                    # Buscar detecciones de objetos
                    for category in detection.categories:
                        # Calcular score de calidad:
                        # - Área del bounding box (objeto más grande = mejor)
                        # - Score de confianza
                        bbox = detection.bounding_box
                        area = bbox.width * bbox.height
                        confianza = category.score
                        
                        # Score combinado: área * confianza
                        # También consideramos si está cerca del centro (opcional)
                        altura_frame, ancho_frame = frame_bgr.shape[:2]
                        centro_x = bbox.origin_x + bbox.width / 2
                        centro_y = bbox.origin_y + bbox.height / 2
                        distancia_centro = abs(centro_x - ancho_frame/2) + abs(centro_y - altura_frame/2)
                        factor_centro = 1.0 / (1.0 + distancia_centro / 100.0)  # Penalizar si está lejos del centro
                        
                        score = area * confianza * factor_centro
                        
                        if score > mejor_score:
                            mejor_score = score
                            mejor_frame = frame_bgr.copy()
                            mejor_frame_num = frame_num
                        
                        break  # Solo consideramos el primer objeto detectado en este frame
            except Exception as e:
                print(f"Error al detectar en frame {frame_num}: {e}")
                continue
            
            frame_num += 1
        
        cap.release()
        
        if mejor_frame is not None:
            # Guardar el mejor frame como imagen
            timestamp_str = str(int(time.time()))
            ruta_imagen = f"mejor_frame_{timestamp_str}.jpg"
            cv2.imwrite(ruta_imagen, mejor_frame)
            print(f"Mejor frame encontrado en posición {mejor_frame_num} (score: {mejor_score:.2f})")
            return ruta_imagen
        else:
            print("No se encontró ningún objeto en el video.")
            return None
            
    except Exception as e:
        print(f"Error al analizar video: {e}")
        if cap.isOpened():
            cap.release()
        return None

def enviar_solo_imagen(ruta_imagen, descripcion):
    """Función de fallback si el video es muy grande."""
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error de envío: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados.")
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        
        mensaje = f"🔴 ¡Alerta! Objeto Detectado\n{descripcion}\n{formatear_fecha_hora()}"
        
        with open(ruta_imagen, 'rb') as photo_file:
            files = {'photo': (os.path.basename(ruta_imagen), photo_file)}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': mensaje,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print(f"[{time.ctime()}] Hilo de envío: Imagen enviada a Telegram correctamente.")
                else:
                    print(f"Error al enviar imagen a Telegram: {result.get('description', 'Error desconocido')}")
            else:
                print(f"Error al enviar imagen a Telegram: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"Excepción al enviar imagen a Telegram: {e}")
    finally:
        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)

