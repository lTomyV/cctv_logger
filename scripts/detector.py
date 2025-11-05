import os
import requests
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Importamos las configuraciones que necesitamos
from scripts.config import MODEL_PATH, UMBRAL_CONFIANZA_OBJETO

def descargar_modelo_si_no_existe():
    """Descarga el modelo .tflite si no existe localmente."""
    if not os.path.exists(MODEL_PATH):
        print(f"Descargando modelo de IA ({MODEL_PATH})...")
        url = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite"
        try:
            r = requests.get(url, allow_redirects=True)
            r.raise_for_status() # Lanza un error si la descarga falla
            with open(MODEL_PATH, 'wb') as f:
                f.write(r.content)
            print("Modelo descargado exitosamente.")
        except Exception as e:
            print(f"ERROR: No se pudo descargar el modelo. {e}")
            raise

def crear_detector_objetos():
    """Configura y crea el detector de MediaPipe."""
    print("Cargando modelo de IA (MediaPipe)...")
    
    # Verifica si el modelo existe antes de cargarlo
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: No se encuentra el archivo del modelo: {MODEL_PATH}")
        print("Ejecuta la descarga primero o revisa config.py")
        return None

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        score_threshold=UMBRAL_CONFIANZA_OBJETO
        # Sin category_allowlist para detectar todos los objetos
    )
    
    try:
        detector = vision.ObjectDetector.create_from_options(options)
        print("Modelo cargado. Iniciando detección.")
        return detector
    except Exception as e:
        print(f"ERROR: No se pudo crear el detector de MediaPipe. {e}")
        return None