import cv2
import time
import os
import threading
from collections import deque
import mediapipe as mp

# Añade 'scripts.' delante de cada import
from scripts import config
from scripts.detector import crear_detector_objetos, descargar_modelo_si_no_existe
from scripts.discord_notifier import enviar_alerta_discord_con_video
from scripts.telegram_notifier import enviar_alerta_telegram_con_video

def main():
    # 1. INICIALIZAR COMPONENTES
    buffer_preroll = deque(maxlen=config.TAMAÑO_BUFFER)
    
    print("Iniciando captura de video...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return

    ret, fotograma = cap.read()
    if not ret:
        print("Error al leer el primer fotograma.")
        cap.release()
        return
    
    # Calculamos dimensiones
    altura_orig, ancho_orig, _ = fotograma.shape
    altura_proc = int(config.ANCHO_PROCESAMIENTO * (altura_orig / ancho_orig))
    DIMENSIONES_VIDEO = (config.ANCHO_PROCESAMIENTO, altura_proc)
    
    # Creamos el detector
    detector = crear_detector_objetos()
    if detector is None:
        print("No se pudo crear el detector. Saliendo.")
        cap.release()
        return

    # Variables de estado
    ultima_alerta_tiempo = 0
    frame_timestamp_ms = 0
    cv2.namedWindow("Feed - Presiona 'q' para salir")

    estado_grabacion = "IDLE" 
    video_out = None          
    frames_grabados_post = 0  
    archivos_para_envio = None

    # 2. BUCLE PRINCIPAL DE DETECCIÓN
    print("Iniciando bucle principal...")
    try:
        while True:
            ret, fotograma_bgr = cap.read()
            if not ret:
                print("Fin del stream o error de cámara.")
                break
            
            # Redimensionamos
            fotograma_proc_bgr = cv2.resize(fotograma_bgr, DIMENSIONES_VIDEO, interpolation=cv2.INTER_AREA)

            # Llenamos búfer si estamos inactivos
            if estado_grabacion == "IDLE":
                buffer_preroll.append(fotograma_proc_bgr)

            # 3. DETECCIÓN CON MEDIAPIPE (optimizado para RPi4)
            # Procesar cada 2 frames para reducir carga (skip frame)
            if frame_timestamp_ms % 2 == 0:  # Procesar solo frames pares
                fotograma_proc_rgb = cv2.cvtColor(fotograma_proc_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=fotograma_proc_rgb)
                frame_timestamp_ms += 1 
                
                objeto_detectado = False
                try:
                    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)
                    for detection in detection_result.detections:
                        # Si hay alguna detección, consideramos que hay un objeto
                        objeto_detectado = True
                        bbox = detection.bounding_box
                        cv2.rectangle(
                            fotograma_proc_bgr,
                            (bbox.origin_x, bbox.origin_y),
                            (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height),
                            (0, 255, 0), 2
                        )
                except Exception as e:
                    print(f"Error en MediaPipe detect_for_video: {e}")
            else:
                objeto_detectado = False  # No detectar en frames impares

            # 4. LÓGICA DE GRABACIÓN
            tiempo_actual = time.time()

            # --- INICIAR GRABACIÓN ---
            if objeto_detectado and \
               estado_grabacion == "IDLE" and \
               (tiempo_actual - ultima_alerta_tiempo > config.COOLDOWN_SEGUNDOS):
                
                print(f"[{time.ctime()}] ¡OBJETO DETECTADO! Iniciando grabación...")
                estado_grabacion = "POSTROLL" 
                frames_grabados_post = 0
                ultima_alerta_tiempo = tiempo_actual
                
                timestamp_str = str(int(tiempo_actual))
                
                # Usamos códec para MP4 compatible con Telegram y Discord
                nombre_video = f"alerta_{timestamp_str}.mp4" 
                nombre_thumb = f"thumb_{timestamp_str}.jpg"
                archivos_para_envio = (nombre_video, nombre_thumb) 
                
                if buffer_preroll:
                    cv2.imwrite(nombre_thumb, buffer_preroll[0])
                else:
                    cv2.imwrite(nombre_thumb, fotograma_proc_bgr) # Fallback

                # Probar diferentes códecs en orden de preferencia para MP4
                codecs_para_probar = [
                    ('H264', 'MP4 con H.264 alternativo'),
                    ('avc1', 'MP4 con H.264'),
                    ('mp4v', 'MP4 con MPEG-4'),
                    ('XVID', 'AVI con XVID como fallback')
                ]
                
                video_out = None
                for codec_str, descripcion in codecs_para_probar:
                    fourcc = cv2.VideoWriter.fourcc(*codec_str)
                    nombre_archivo = nombre_video if codec_str != 'XVID' else f"alerta_{timestamp_str}.avi"
                    
                    video_out = cv2.VideoWriter(nombre_archivo, fourcc, config.FPS_ESPERADO, DIMENSIONES_VIDEO)
                    
                    if video_out.isOpened():
                        print(f"VideoWriter creado exitosamente con códec {codec_str} ({descripcion})")
                        if codec_str == 'XVID':
                            # Actualizar nombre del archivo si usamos AVI
                            archivos_para_envio = (nombre_archivo, nombre_thumb)
                        break
                    else:
                        video_out.release()
                        video_out = None
                
                if video_out is None:
                    print(f"ERROR: No se pudo crear el VideoWriter con ningún códec. Saltando grabación.")
                    estado_grabacion = "IDLE"
                    continue

                print(f"Volcando {len(buffer_preroll)} fotogramas de pre-roll...")
                for frame in buffer_preroll:
                    video_out.write(frame)
                
                buffer_preroll.clear()

            # --- CONTINUAR GRABACIÓN (POST-ROLL) ---
            if estado_grabacion == "POSTROLL" and video_out is not None:
                video_out.write(fotograma_proc_bgr)
                frames_grabados_post += 1
                
                if frames_grabados_post >= config.FRAMES_A_GRABAR_POST:
                    print(f"Grabación post-roll terminada. {frames_grabados_post} fotogramas escritos.")
                    
                    # Cerrar el video correctamente y asegurar que se escriba todo
                    if video_out is not None:
                        video_out.release()
                        video_out = None
                        # Pequeño delay para asegurar que el archivo se escriba completamente
                        time.sleep(0.1)
                    if archivos_para_envio is not None:
                        print(f"Video '{archivos_para_envio[0]}' guardado.")

                        # Preparar envío a servicios
                        print("Iniciando envío a servicios en segundo plano...")
                    
                    estado_grabacion = "IDLE"
                    
                    # Crear un handler compartido para la eliminación de archivos
                    # El contador se incrementa cuando cada servicio termina
                    archivos_originales = archivos_para_envio
                    
                    if archivos_originales is not None:
                        # Contador compartido con lock para thread-safety
                        contador_lock = threading.Lock()
                        contador_servicios = {"count": 0}
                        servicios_esperados = 0
                        
                        if config.WEBHOOK_URL:
                            servicios_esperados += 1
                        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                            servicios_esperados += 1
                        
                        def notificar_servicio_terminado():
                            """Callback que se ejecuta cuando un servicio termina de usar los archivos."""
                            with contador_lock:
                                contador_servicios["count"] += 1
                                if contador_servicios["count"] >= servicios_esperados:
                                    # Ambos servicios han terminado, eliminar archivos
                                    try:
                                        if archivos_originales is not None:
                                            if os.path.exists(archivos_originales[0]):
                                                os.remove(archivos_originales[0])
                                            if os.path.exists(archivos_originales[1]):
                                                os.remove(archivos_originales[1])
                                            print(f"Archivos originales eliminados después de que {contador_servicios['count']} servicio(s) terminaron.")
                                    except Exception as e:
                                        print(f"Error al eliminar archivos originales: {e}")
                        
                        # Pasar el callback a cada servicio
                        if config.WEBHOOK_URL:
                            send_thread_discord = threading.Thread(
                                target=enviar_alerta_discord_con_video, 
                                args=(archivos_originales[0], archivos_originales[1], notificar_servicio_terminado)
                            )
                            send_thread_discord.start()
                        
                        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                            send_thread_telegram = threading.Thread(
                                target=enviar_alerta_telegram_con_video, 
                                args=(archivos_originales[0], archivos_originales[1], notificar_servicio_terminado)
                            )
                            send_thread_telegram.start()
                    
                    archivos_para_envio = None

            # 5. DEBUG VISUAL Y SALIDA
            cv2.imshow("Feed - Presiona 'q' para salir", fotograma_proc_bgr)
            if cv2.waitKey(50) & 0xFF == ord('q'):  # Aumentado de 1ms a 50ms para reducir CPU
                print("Saliendo por petición del usuario...")
                break

    except Exception as e:
        print(f"\nError inesperado en el bucle principal: {e}")
    finally:
        if video_out is not None:
            video_out.release()
            print("Grabación de video interrumpida y cerrada.")
        cap.release()
        cv2.destroyAllWindows()
        print("Recursos liberados. Script terminado.")

if __name__ == "__main__":
    # 1. Asegurarse que el modelo exista
    descargar_modelo_si_no_existe()
    
    # 2. Correr la aplicación principal
    main()